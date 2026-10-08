"""Knowledge migrations, transactional imports and shared review/check-in behavior."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server.knowledge import validate_document
from server.store import DEFAULT_STATE, MAX_STATE_BYTES, Store


def document():
    return {"format": "coderecall.knowledge", "version": 1,
            "deck": {"id": "cpp", "title": "C++", "description": "语言知识"},
            "items": [{"id": "raii", "title": "RAII", "kind": "qa", "prompt": "什么是 RAII？",
                       "answer": "资源获取即初始化。", "tags": ["内存管理"], "source": "学习笔记"}]}


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="knowledge-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "progress.db"
        self.store = Store(self.path, range(1, 101))
        self.now = datetime(2026, 10, 9, 8, tzinfo=timezone.utc)
        clock = patch("server.store.utc_now", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def import_one(self):
        return self.store.action({"type": "knowledge-import", "document": document()})

    def rate(self, event="knowledge-event", **overrides):
        return self.store.action({"type": "knowledge-rate", "itemId": "raii", "rating": "good", "eventId": event,
                                  "day": self.now.astimezone().date().isoformat(), "seconds": 12, **overrides})

    def test_v1_database_backup_and_upgrade_are_once_only_and_preserve_old_fields(self):
        original = copy.deepcopy(DEFAULT_STATE)
        for key in ("solutions", "decks", "knowledge", "knowledgeCards", "knowledgeNotes", "knowledgeFavorites", "knowledgeEvents"):
            original.pop(key)
        original["version"] = 1
        original["settings"].pop("includeHot100")
        original["notes"]["1"] = "# 旧笔记"
        original["drafts"]["1:python:leetcode"] = "print('old')"
        original["favorites"] = [1]
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertEqual(upgraded["version"], 2)
        for key in original:
            if key == "settings":
                self.assertEqual(upgraded[key], {**original[key], "includeHot100": True})
            elif key != "version":
                self.assertEqual(upgraded[key], original[key])
        backups = list(self.path.parent.glob("before-v2-upgrade-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), original)
        Store(self.path, range(1, 101))
        self.assertEqual(len(list(self.path.parent.glob("before-v2-upgrade-*.json"))), 1)

    def test_failed_upgrade_backup_never_changes_original_database(self):
        original = copy.deepcopy(DEFAULT_STATE)
        original["version"] = 1
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        with patch.object(Store, "_backup", side_effect=OSError("disk full")), self.assertRaises(OSError):
            Store(self.path, range(1, 101))
        self.assertEqual(self.store.read(), original)

    def test_hot100_recommendations_default_enabled_and_can_be_disabled_without_data_loss(self):
        self.assertIs(self.store.read()["settings"]["includeHot100"], True)
        self.store.action({"type": "rate", "problemId": 1, "rating": "good", "eventId": "old-lc"})
        self.store.action({"type": "note", "problemId": 1, "text": "keep notes"})
        self.import_one()
        before = self.store.read()
        disabled = self.store.action({"type": "settings", "settings": {"includeHot100": False}})
        self.assertIs(disabled["settings"]["includeHot100"], False)
        for key in before:
            if key != "settings":
                self.assertEqual(disabled[key], before[key])
        self.assertIs(Store(self.path, range(1, 101)).read()["settings"]["includeHot100"], False)
        self.assertEqual(self.store.validate_import(disabled), disabled)
        for value in (0, 1, None, "false", [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.action({"type": "settings", "settings": {"includeHot100": value}})
        self.assertEqual(self.store.read(), disabled)

    def test_existing_v2_database_and_import_default_missing_hot100_preference_to_true(self):
        existing = self.import_one()
        existing["settings"].pop("includeHot100")
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(existing),))
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertIs(upgraded["settings"]["includeHot100"], True)
        self.assertEqual(upgraded["knowledge"], existing["knowledge"])
        self.assertIs(self.store.validate_import(existing)["settings"]["includeHot100"], True)

    def test_excessive_backup_nesting_fails_without_modifying_state(self):
        original = self.import_one()
        nested = []
        cursor = nested
        for _ in range(2000):
            child = []
            cursor.append(child)
            cursor = child
        incoming = {**original, "unknown": nested}
        with self.assertRaises(ValueError):
            self.store.action({"type": "import", "state": incoming})
        self.assertEqual(self.store.read(), original)
        self.assertFalse(list(self.path.parent.glob("before-import-*.json")))

    def test_import_retry_is_idempotent_and_conflicts_roll_back_entire_batch(self):
        original = self.import_one()
        self.assertEqual(self.import_one(), original)
        bad = document()
        bad["items"].insert(0, {**bad["items"][0], "id": "new-card"})
        bad["items"][1]["answer"] = "覆盖旧答案"
        with self.assertRaisesRegex(ValueError, "已存在"):
            self.store.action({"type": "knowledge-import", "document": bad})
        self.assertEqual(self.store.read(), original)

    def test_generated_ids_are_repeatable_without_losing_progress(self):
        incoming = document()
        incoming["deck"].pop("id")
        incoming["items"][0].pop("id")
        first = self.store.action({"type": "knowledge-import", "document": incoming})
        item_id = next(iter(first["knowledge"]))
        self.store.action({"type": "knowledge-note", "itemId": item_id, "text": "保留我"})
        after = self.store.action({"type": "knowledge-import", "document": incoming})
        self.assertEqual(len(after["knowledge"]), 1)
        self.assertEqual(after["knowledgeNotes"][item_id], "保留我")

    def test_custom_solutions_are_separate_by_language_mode_and_reset_only_one(self):
        for language in ("python", "cpp"):
            for mode in ("leetcode", "acm"):
                self.store.action({"type": "solution", "problemId": 1, "language": language, "mode": mode,
                                   "solution": {"brief": f"{language}-{mode}", "annotated": "", "explanation": "# 自己的思路"}})
        self.assertEqual(len(self.store.read()["solutions"]), 4)
        after = self.store.action({"type": "solution-reset", "problemId": 1, "language": "python", "mode": "leetcode"})
        self.assertEqual(len(after["solutions"]), 3)
        self.assertNotIn("1:python:leetcode", after["solutions"])
        before = copy.deepcopy(after)
        with self.assertRaises(ValueError):
            self.store.action({"type": "solution", "problemId": 1, "language": "python", "mode": "leetcode", "solution": {"brief": "x"}})
        self.assertEqual(self.store.read(), before)

    def test_shared_checkin_counts_distinct_knowledge_and_leetcode_items(self):
        self.import_one()
        self.rate()
        self.rate(event="repeat")
        self.store.action({"type": "rate", "problemId": 1, "rating": "again", "eventId": "lc1"})
        self.assertEqual(self.store.read()["checkins"], [])
        after = self.store.action({"type": "rate", "problemId": 2, "rating": "good", "eventId": "lc2"})
        self.assertEqual(after["checkins"], [self.now.astimezone().date().isoformat()])
        self.assertEqual(after["knowledgeCards"]["raii"]["reviews"], 2)
        self.assertEqual(after["knowledgeEvents"][0]["kind"], "new")
        self.assertEqual(after["knowledgeEvents"][1]["kind"], "review")

    def test_rating_retry_is_idempotent_and_event_ids_cannot_cross_domains(self):
        self.import_one()
        original = self.rate()
        with patch("server.store.utc_now", return_value=self.now + timedelta(days=8)):
            self.assertEqual(self.rate(seconds=32), original)
        with self.assertRaises(ValueError):
            self.store.action({"type": "rate", "problemId": 1, "rating": "good", "eventId": "knowledge-event"})
        self.store.action({"type": "rate", "problemId": 1, "rating": "good", "eventId": "lc"})
        with self.assertRaises(ValueError):
            self.rate(event="lc")

    def test_edit_and_archive_retain_notes_favorites_and_review_history(self):
        self.import_one()
        self.rate()
        self.store.action({"type": "knowledge-note", "itemId": "raii", "text": "**自己的笔记**"})
        self.store.action({"type": "knowledge-favorite", "itemId": "raii"})
        item = self.store.read()["knowledge"]["raii"]
        self.store.action({"type": "knowledge-save", "item": {**item, "answer": "修改后的答案"}})
        archived = self.store.action({"type": "knowledge-archive", "itemId": "raii", "archived": True})
        self.assertTrue(archived["knowledge"]["raii"]["archived"])
        self.assertEqual(archived["knowledgeNotes"]["raii"], "**自己的笔记**")
        self.assertEqual(archived["knowledgeFavorites"], ["raii"])
        self.assertEqual(archived["knowledgeCards"]["raii"]["reviews"], 1)
        with self.assertRaises(ValueError):
            self.rate(event="archived")
        self.store.action({"type": "knowledge-archive", "itemId": "raii", "archived": False})
        self.assertEqual(self.rate(event="restored")["knowledgeCards"]["raii"]["reviews"], 2)

    def test_full_v2_backup_roundtrip_and_dangling_references_rejected(self):
        self.import_one()
        original = self.rate()
        self.assertEqual(self.store.action({"type": "import", "state": original}), original)
        variants = []
        bad = copy.deepcopy(original); bad["decks"] = {}; variants.append(bad)
        bad = copy.deepcopy(original); bad["knowledge"]["raii"]["id"] = "other"; variants.append(bad)
        bad = copy.deepcopy(original); bad["knowledgeFavorites"] = ["missing"]; variants.append(bad)
        bad = copy.deepcopy(original); bad["knowledgeCards"]["raii"]["stability"] = float("nan"); variants.append(bad)
        bad = copy.deepcopy(original); bad["knowledgeEvents"].append(bad["knowledgeEvents"][0]); variants.append(bad)
        bad = copy.deepcopy(original); bad["knowledge"]["raii"]["archived"] = 1; variants.append(bad)
        for incoming in variants:
            with self.subTest(incoming=incoming), self.assertRaises(ValueError):
                self.store.action({"type": "import", "state": incoming})
            self.assertEqual(self.store.read(), original)

    def test_library_above_eight_megabytes_is_restorable_but_size_limit_is_atomic(self):
        self.assertEqual(MAX_STATE_BYTES, 64 * 1024 * 1024)
        original = self.import_one()
        incoming = copy.deepcopy(original)
        template = incoming["knowledge"]["raii"]
        for index in range(100):
            item_id = f"big-item-{index}"
            incoming["knowledge"][item_id] = {**template, "id": item_id, "answer": "x" * 90000}
        self.assertGreater(len(json.dumps(incoming)), 8 * 1024 * 1024)
        restored = self.store.action({"type": "import", "state": incoming})
        self.assertEqual(len(restored["knowledge"]), 101)
        with patch("server.store.MAX_STATE_BYTES", 1024):
            with self.assertRaises(ValueError):
                self.store.action({"type": "knowledge-note", "itemId": "raii", "text": "do not persist"})
            with self.assertRaises(ValueError):
                self.store.validate_import(incoming)
        self.assertEqual(self.store.read(), restored)

    def test_concurrent_knowledge_updates_do_not_lose_progress(self):
        self.import_one()
        stores = [Store(self.path, range(1, 101)) for _ in range(3)]
        def rate(index):
            return stores[index % 3].action({"type": "knowledge-rate", "itemId": "raii", "rating": "good", "eventId": f"concurrent-{index}"})
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(rate, range(15)))
        self.assertEqual(self.store.read()["knowledgeCards"]["raii"]["reviews"], 15)

    def test_document_validation_rejects_invalid_schema_and_cloze(self):
        variants = []
        bad = document(); bad["version"] = True; variants.append(bad)
        bad = document(); bad["items"] = []; variants.append(bad)
        bad = document(); bad["items"][0]["id"] = "../escape"; variants.append(bad)
        bad = document(); bad["deck"]["id"] = None; variants.append(bad)
        bad = document(); bad["items"][0]["tags"] = "tag"; variants.append(bad)
        bad = document(); bad["items"][0]["answer"] = " "; variants.append(bad)
        bad = document(); bad["items"].append(bad["items"][0]); variants.append(bad)
        bad = document(); bad["apiKey"] = "should-not-import"; variants.append(bad)
        bad = document(); bad["items"][0]["kind"] = "cloze"; variants.append(bad)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_document(value)
        good = document()
        good["items"][0].update(kind="cloze", prompt="RAII 使用{{c1::对象生命周期}}管理资源。")
        self.assertEqual(validate_document(good)["items"][0]["kind"], "cloze")

    def test_import_preserves_markdown_indentation(self):
        incoming = document()
        incoming["items"][0]["answer"] = "    print('indented code block')\n"
        after = self.store.action({"type": "knowledge-import", "document": incoming})
        self.assertEqual(after["knowledge"]["raii"]["answer"], incoming["items"][0]["answer"])


if __name__ == "__main__":
    unittest.main()
