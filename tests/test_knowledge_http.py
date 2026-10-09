"""Round-trip the v2 user workflows through the real local HTTP handler."""
import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from server.app import LocalHTTPServer, make_handler
from server.catalog import BY_ID
from server.store import DEFAULT_STATE, Store


class KnowledgeHttpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="coderecall-knowledge-http-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = Store(self.root / "progress.db", BY_ID)
        self.server = LocalHTTPServer(("127.0.0.1", 0), make_handler(self.store, 0))
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.store, self.port)
        self.server.RequestHandlerClass.log_message = lambda *_: None
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        status, bootstrap = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.token = bootstrap["token"]
        self.assertEqual(bootstrap["state"]["version"], 2)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def post(self, path, payload, **headers):
        return self.request("POST", path, json.dumps(payload, ensure_ascii=False).encode("utf-8"), {
            "Content-Type": "application/json",
            "X-CodeRecall-Token": self.token,
            "Origin": f"http://127.0.0.1:{self.port}",
            **headers,
        })

    def action(self, payload):
        status, result = self.post("/api/action", payload)
        self.assertEqual(status, 200, result)
        return result

    @staticmethod
    def document():
        return {
            "format": "coderecall.knowledge", "version": 1,
            "deck": {"id": "http-deck", "title": "学习测试", "description": "本地 HTTP 测试"},
            "items": [{"id": "http-card", "kind": "qa", "title": "主动回忆",
                       "prompt": "为什么先回忆再看答案？", "answer": "检查自己是否能独立提取知识。",
                       "tags": ["学习方法"], "source": "测试笔记"}],
        }

    @staticmethod
    def legacy_backup():
        fields = ("settings", "cards", "notes", "favorites", "drafts", "events", "checkins")
        return {"version": 1, **{field: copy.deepcopy(DEFAULT_STATE[field]) for field in fields}}

    def test_new_routes_require_session_and_same_origin_before_processing(self):
        before = self.store.read()
        payload = {"mode": "ai", "endpoint": "https://example.invalid/v1", "model": "test",
                   "text": "学习笔记", "deckTitle": "测试", "apiKey": "never-send-this"}
        with patch("server.app.split_document") as split:
            for path in ("/api/knowledge/split", "/api/knowledge/validate", "/api/action"):
                with self.subTest(path=path, authorization="missing token"):
                    status, _ = self.request("POST", path, b"{}", {"Content-Type": "application/json"})
                    self.assertEqual(status, 403)
                for headers in ({"Origin": "https://untrusted.example"},
                                {"Host": "127.0.0.1.evil.example"},
                                {"Sec-Fetch-Site": "cross-site"}):
                    with self.subTest(path=path, headers=headers):
                        status, _ = self.post(path, payload, **headers)
                        self.assertEqual(status, 403)
            split.assert_not_called()
        self.assertEqual(self.store.read(), before)

    def test_local_split_validate_then_import_is_explicit_and_repeatable(self):
        original = self.store.read()
        status, preview = self.post("/api/knowledge/split", {
            "mode": "local", "deckTitle": "Python 笔记",
            "text": "# 作用域\n变量的可见范围。\n\n# 示例\n```python\n# 这是注释\nvalue = 1\n```\n",
        })
        self.assertEqual(status, 200, preview)
        self.assertEqual([item["title"] for item in preview["items"]], ["作用域", "示例"])
        self.assertIn("# 这是注释", preview["items"][1]["answer"])
        self.assertEqual(self.store.read(), original, "Preview must not write learning content")
        status, validated = self.post("/api/knowledge/validate", preview)
        self.assertEqual(status, 200, validated)
        self.assertEqual(self.store.read(), original)
        imported = self.action({"type": "knowledge-import", "document": validated})
        self.assertEqual(len(imported["knowledge"]), 2)
        self.assertEqual(len(imported["decks"]), 1)
        self.assertEqual(imported["knowledgeEvents"], [])
        repeated = self.action({"type": "knowledge-import", "document": validated})
        self.assertEqual(repeated, imported)
        status, fetched = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, imported)

    def test_ai_preview_uses_stubbed_provider_and_never_persists_credentials(self):
        proposed = self.document()
        provider_reply = {"choices": [{"message": {"content": json.dumps(proposed)}, "finish_reason": "stop"}]}
        before = self.store.read()
        with patch("server.ai_import._request_completion", return_value=provider_reply) as completion:
            status, preview = self.post("/api/knowledge/split", {
                "mode": "ai", "endpoint": "https://example.invalid/v1", "model": "test-model",
                "text": "仅在测试进程中使用的笔记", "deckTitle": "用户指定的知识库",
                "apiKey": "test-secret-never-persist",
            })
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview["deck"]["title"], "用户指定的知识库")
        completion.assert_called_once()
        self.assertEqual(self.store.read(), before)
        self.assertNotIn("test-secret", json.dumps(preview))
        with patch("server.ai_import._request_completion") as completion:
            status, failure = self.post("/api/knowledge/split", {
                "mode": "ai", "endpoint": "http://example.invalid/v1", "model": "test-model",
                "text": "笔记", "deckTitle": "测试", "apiKey": "test-secret-never-persist",
            })
            completion.assert_not_called()
        self.assertEqual(status, 400, failure)
        self.assertNotIn("test-secret", json.dumps(failure))

    def test_invalid_knowledge_batch_rolls_back_and_keeps_existing_content(self):
        existing = self.action({"type": "knowledge-import", "document": self.document()})
        invalid = self.document()
        invalid["deck"]["id"] = "another-deck"
        invalid["items"][0]["id"] = "new-valid-first-card"
        invalid["items"].append({"id": "broken-second-card", "kind": "cloze", "title": "坏的填空",
                                 "prompt": "没有填空标记", "answer": "答案"})
        for path, payload in (("/api/knowledge/validate", invalid),
                              ("/api/action", {"type": "knowledge-import", "document": invalid})):
            with self.subTest(path=path):
                status, failure = self.post(path, payload)
                self.assertEqual(status, 400, failure)
                self.assertIn("error", failure)
                self.assertEqual(self.store.read(), existing)

    def test_personal_solutions_are_separate_and_reset_preserves_other_variants(self):
        status, builtin = self.request("GET", "/api/problems/1")
        self.assertEqual(status, 200)
        for language in ("python", "cpp"):
            for mode in ("leetcode", "acm"):
                solution = {"brief": f"{language}/{mode} concise", "annotated": "# 我的注释",
                            "explanation": "## 思路\n自己的解释。"}
                state = self.action({"type": "solution", "problemId": 1,
                                     "language": language, "mode": mode, "solution": solution})
                actual = state["solutions"][f"1:{language}:{mode}"]
                for field, value in solution.items():
                    self.assertEqual(actual[field], value)
                self.assertIn("updatedAt", actual)
        self.assertEqual(len(state["solutions"]), 4)
        status, unchanged_builtin = self.request("GET", "/api/problems/1")
        self.assertEqual(status, 200)
        self.assertEqual(builtin, unchanged_builtin)
        reset = self.action({"type": "solution-reset", "problemId": 1, "language": "python", "mode": "leetcode"})
        self.assertNotIn("1:python:leetcode", reset["solutions"])
        self.assertEqual(len(reset["solutions"]), 3)
        status, failure = self.post("/api/action", {"type": "solution", "problemId": 1,
                                                    "language": "java", "mode": "leetcode", "solution": {}})
        self.assertEqual(status, 400, failure)
        self.assertEqual(self.store.read(), reset)

    def test_knowledge_and_algorithm_reviews_require_explicit_daily_checkin(self):
        self.action({"type": "settings", "settings": {"dailyGoal": 2}})
        self.action({"type": "knowledge-import", "document": self.document()})
        first = self.action({"type": "knowledge-rate", "itemId": "http-card", "rating": "good",
                             "eventId": "knowledge-feedback", "seconds": 30})
        self.assertEqual(first["checkins"], [])
        complete = self.action({"type": "rate", "problemId": 1, "rating": "good",
                                "eventId": "algorithm-feedback", "seconds": 60})
        self.assertEqual(len(complete["knowledgeCards"]), 1)
        self.assertEqual(len(complete["cards"]), 1)
        self.assertEqual(complete["checkins"], [])
        checked = self.action({"type": "checkin"})
        self.assertEqual(checked["checkins"], [complete["knowledgeEvents"][0]["day"]])
        self.assertEqual(self.action({"type": "checkin"}), checked)
        self.assertEqual(checked["knowledgeEvents"], complete["knowledgeEvents"])
        self.assertEqual(checked["events"], complete["events"])

    def test_checkin_without_learning_is_saved_and_client_dates_are_rejected(self):
        state = self.action({"type": "checkin"})
        self.assertEqual(len(state["checkins"]), 1)
        self.assertEqual(state["events"], [])
        self.assertEqual(state["knowledgeEvents"], [])
        for day in (state["checkins"][0], "2020-01-01", None):
            status, failure = self.post("/api/action", {"type": "checkin", "day": day})
            self.assertEqual(status, 400, failure)
            self.assertIn("error", failure)
            self.assertEqual(self.store.read(), state)

    def test_v1_backup_import_upgrades_copy_and_backs_up_current_v2_state(self):
        old_state = self.action({"type": "knowledge-import", "document": self.document()})
        legacy = self.legacy_backup()
        legacy["notes"]["1"] = "## 旧版笔记\n保留我的复习内容。"
        result = self.action({"type": "import", "state": legacy})
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["notes"], legacy["notes"])
        self.assertEqual(result["knowledge"], {})
        self.assertEqual(result["solutions"], {})
        backups = list(self.root.glob("before-import-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), old_state)
        self.assertEqual(Store(self.root / "progress.db", BY_ID).read(), result)

    def test_complete_backup_larger_than_8_mib_can_be_restored(self):
        legacy = self.legacy_backup()
        legacy["notes"] = {str(pid): "记" * 29000 for pid in BY_ID}
        payload = {"type": "import", "state": legacy}
        self.assertGreater(len(json.dumps(payload, ensure_ascii=False).encode("utf-8")), 8 * 1024 * 1024)
        result = self.action(payload)
        self.assertEqual(result["notes"], legacy["notes"])
        self.assertEqual(result["version"], 2)

    def test_malformed_json_and_unknown_api_do_not_mutate_state(self):
        before = self.store.read()
        headers = {"Content-Type": "application/json", "X-CodeRecall-Token": self.token}
        for body in (b"{", b"[]", b'{"version":NaN}'):
            status, failure = self.request("POST", "/api/knowledge/validate", body, headers)
            self.assertEqual(status, 400, failure)
        status, failure = self.post("/api/knowledge/missing", {})
        self.assertEqual(status, 404, failure)
        self.assertEqual(self.store.read(), before)


if __name__ == "__main__":
    unittest.main()
