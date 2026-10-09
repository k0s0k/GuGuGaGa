"""Selected knowledge decks are explicit preferences with legacy compatibility."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from server.store import Store


def document(deck_id, item_id="card"):
    return {"format": "coderecall.knowledge", "version": 1,
            "deck": {"id": deck_id, "title": deck_id, "description": ""},
            "items": [{"id": f"{deck_id}-{item_id}", "title": item_id, "kind": "qa", "prompt": "问题", "answer": "答案"}]}


class StudyDeckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gugugaga-study-decks-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "progress.db"
        self.store = Store(self.path, range(1, 101))

    def import_deck(self, deck_id, item_id="card"):
        return self.store.action({"type": "knowledge-import", "document": document(deck_id, item_id)})

    def select(self, ids, **settings):
        return self.store.action({"type": "settings", "settings": {"studyDeckIds": ids, **settings}})

    def test_new_user_creating_or_importing_decks_does_not_automatically_select_them(self):
        self.assertEqual(self.store.read()["settings"]["studyDeckIds"], [])
        created = self.store.action({"type": "deck-save", "deck": {"id": "manual", "title": "手动创建"}})
        self.assertEqual(created["settings"]["studyDeckIds"], [])
        imported = self.import_deck("cpp")
        self.assertEqual(imported["settings"]["studyDeckIds"], [])
        self.assertEqual(set(imported["decks"]), {"manual", "cpp"})

    def test_missing_legacy_database_preference_selects_all_existing_decks_once(self):
        self.import_deck("cpp")
        self.import_deck("english")
        self.store.action({"type": "knowledge-note", "itemId": "cpp-card", "text": "保留笔记"})
        original = self.store.action({"type": "settings", "settings": {"theme": "light", "includeHot100": False}})
        original["settings"].pop("studyDeckIds")
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        expected = copy.deepcopy(original)
        expected["settings"]["studyDeckIds"] = ["cpp", "english"]
        upgraded = Store(self.path, range(1, 101))
        self.assertEqual(upgraded.read(), expected)
        self.assertEqual(Store(self.path, range(1, 101)).read(), expected)
        cleared = upgraded.action({"type": "settings", "settings": {"studyDeckIds": []}})
        self.assertEqual(Store(self.path, range(1, 101)).read(), cleared)

    def test_legacy_backups_default_to_all_validated_decks_or_empty_for_v1(self):
        self.import_deck("cpp")
        legacy = self.import_deck("english")
        legacy["settings"].pop("studyDeckIds")
        restored = self.store.action({"type": "import", "state": legacy})
        self.assertEqual(restored["settings"]["studyDeckIds"], ["cpp", "english"])
        self.assertEqual(restored["knowledge"], legacy["knowledge"])
        legacy["version"] = 1
        for key in ("decks", "knowledge", "knowledgeCards", "knowledgeEvents", "knowledgeFavorites", "knowledgeNotes"):
            legacy.pop(key)
        v1 = self.store.action({"type": "import", "state": legacy})
        self.assertEqual(v1["settings"]["studyDeckIds"], [])

    def test_explicit_empty_is_retained_even_when_another_old_preference_needs_migration(self):
        existing = self.import_deck("cpp")
        existing["settings"].pop("avatar")
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(existing),))
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertEqual(upgraded["settings"]["studyDeckIds"], [])
        self.select(["cpp"])
        restored = self.store.action({"type": "import", "state": upgraded})
        self.assertEqual(restored["settings"]["studyDeckIds"], [])

    def test_selection_deduplicates_preserves_order_and_survives_unrelated_settings_and_backup(self):
        self.import_deck("cpp")
        self.import_deck("english")
        selected = self.select(["english", "cpp", "english"], includeHot100=False)
        self.assertEqual(selected["settings"]["studyDeckIds"], ["english", "cpp"])
        self.assertFalse(selected["settings"]["includeHot100"])
        changed = self.store.action({"type": "settings", "settings": {"workspaceName": "我的计划", "dailyGoal": 5}})
        self.assertEqual(changed["settings"]["studyDeckIds"], ["english", "cpp"])
        self.assertEqual(Store(self.path, range(1, 101)).read(), changed)
        self.select([])
        restored = self.store.action({"type": "import", "state": changed})
        self.assertEqual(restored, changed)
        self.assertEqual(Store(self.path, range(1, 101)).read(), changed)

    def test_new_items_in_a_selected_deck_keep_selection_and_existing_review_history(self):
        self.import_deck("cpp", "old")
        self.select(["cpp"])
        studied = self.store.action({"type": "knowledge-rate", "itemId": "cpp-old", "rating": "good", "eventId": "old-review"})
        extended = self.import_deck("cpp", "new")
        self.assertEqual(extended["settings"]["studyDeckIds"], ["cpp"])
        self.assertEqual(set(extended["knowledge"]), {"cpp-old", "cpp-new"})
        self.assertEqual(extended["knowledgeCards"], studied["knowledgeCards"])
        self.assertEqual(extended["knowledgeEvents"], studied["knowledgeEvents"])
        self.assertEqual(extended["stones"], studied["stones"])
        added = self.import_deck("english")
        self.assertEqual(added["settings"]["studyDeckIds"], ["cpp"])

    def test_invalid_selections_are_rejected_without_partial_settings_writes(self):
        self.import_deck("cpp")
        original = self.select(["cpp"])
        invalid = (None, True, "cpp", {}, [1], [True], [{}], [""], ["bad/id"], ["x" * 101], ["missing"], ["cpp", "missing"], ["cpp"] * 501)
        for ids in invalid:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.select(ids, includeHot100=False, dailyGoal=9)
            self.assertEqual(self.store.read(), original)

    def test_invalid_import_selection_is_atomic_and_never_creates_backup(self):
        self.import_deck("cpp")
        original = self.select(["cpp"])
        for ids in (["missing"], None, {"cpp": True}, ["../cpp"]):
            incoming = copy.deepcopy(original)
            incoming["settings"]["studyDeckIds"] = ids
            incoming["settings"]["workspaceName"] = "不可写入"
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.store.action({"type": "import", "state": incoming})
            self.assertEqual(self.store.read(), original)
        self.assertEqual(list(self.path.parent.glob("before-import-*.json")), [])

    def test_import_references_are_checked_against_incoming_decks_not_current_library(self):
        self.import_deck("cpp")
        source = Store(Path(self.temp.name) / "other.db", range(1, 101))
        source.action({"type": "knowledge-import", "document": document("english")})
        incoming = source.action({"type": "settings", "settings": {"studyDeckIds": ["english"]}})
        restored = self.store.action({"type": "import", "state": incoming})
        self.assertEqual(restored["settings"]["studyDeckIds"], ["english"])
        self.assertEqual(set(restored["decks"]), {"english"})
        invalid = copy.deepcopy(incoming)
        invalid["settings"]["studyDeckIds"] = ["cpp"]
        with self.assertRaisesRegex(ValueError, "不存在的知识库"):
            self.store.action({"type": "import", "state": invalid})
        self.assertEqual(self.store.read(), restored)


if __name__ == "__main__":
    unittest.main()
