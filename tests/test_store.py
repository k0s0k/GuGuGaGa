"""Persistence, import recovery, race conditions and local HTTP access checks."""
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timedelta, timezone
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from server.scheduler import parse_time
from server.store import DEFAULT_STATE, Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="coderecall-store-test-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "progress.db"
        self.store = Store(self.path, range(1, 101))
        self.now = datetime(2026, 10, 4, 12, 0).astimezone()
        self.day = self.now.date().isoformat()
        self.clock = patch("server.store.utc_now", return_value=self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def rate(self, pid=1, event="first", rating="good", **extra):
        return self.store.action({"type": "rate", "problemId": pid, "eventId": event,
                                  "rating": rating, "day": self.day, "seconds": 60, **extra})

    def test_default_goal_can_be_completed_from_new_daily_plan(self):
        state = self.store.read()
        self.assertEqual(state["settings"]["theme"], "dark")
        self.assertEqual(state["settings"]["newPerDay"], 3)
        self.assertEqual(state["settings"]["dailyGoal"], 3)
        state["settings"]["dailyGoal"] = 30
        self.assertEqual(self.store.read()["settings"]["dailyGoal"], 3)

    def test_first_feedback_and_relearning_persist_with_utc_due(self):
        first = self.rate(rating="again")
        self.assertEqual(first["events"][0]["kind"], "new")
        self.assertEqual(parse_time(first["cards"]["1"]["due"]) - self.now, timedelta(minutes=10))
        self.assertTrue(first["cards"]["1"]["due"].endswith("+00:00"))
        second = self.rate(event="second", rating="good")
        self.assertEqual(second["events"][1]["kind"], "review")
        self.assertEqual(second["cards"]["1"]["reviews"], 2)
        self.assertEqual(second["cards"]["1"]["lapses"], 1)
        self.assertEqual(Store(self.path, range(1, 101)).read(), second)

    def test_retry_is_idempotent_even_after_date_changes(self):
        first = self.rate()
        with patch("server.store.utc_now", return_value=self.now + timedelta(days=5)):
            retried = self.rate(seconds=120)
        self.assertEqual(first, retried)
        with self.assertRaises(ValueError):
            self.rate(pid=2)
        with self.assertRaises(ValueError):
            self.rate(rating="easy")
        self.assertEqual(self.store.read(), first)

    def test_reaching_goal_never_automatically_checks_in(self):
        self.rate()
        self.rate(event="repeat")
        self.rate(pid=2, event="two")
        self.assertEqual(self.store.read()["checkins"], [])
        state = self.rate(pid=3, event="three", rating="again")
        self.assertEqual(state["checkins"], [])
        self.assertEqual(len(state["events"]), 4)

    def test_changing_goal_never_checks_in_or_removes_existing_checkin(self):
        self.rate()
        self.rate(pid=2, event="two")
        state = self.store.action({"type": "settings", "settings": {"dailyGoal": 2}})
        self.assertEqual(state["checkins"], [])
        checked = self.store.action({"type": "checkin"})
        self.assertEqual(checked["checkins"], [self.day])
        raised = self.store.action({"type": "settings", "settings": {"dailyGoal": 5}})
        self.assertEqual(raised["checkins"], [self.day])

    def test_manual_checkin_is_idempotent_without_creating_learning_events(self):
        before = self.store.read()
        first = self.store.action({"type": "checkin"})
        expected = copy.deepcopy(before)
        expected["checkins"] = [self.day]
        self.assertEqual(first, expected)
        self.assertEqual(self.store.action({"type": "checkin"}), expected)
        self.assertEqual(Store(self.path, range(1, 101)).read(), expected)
        with patch("server.store.utc_now", return_value=self.now + timedelta(days=1)):
            tomorrow = self.store.action({"type": "checkin"})
        self.assertEqual(tomorrow["checkins"], [self.day, (self.now.date() + timedelta(days=1)).isoformat()])
        self.assertEqual(tomorrow["events"], [])
        self.assertEqual(tomorrow["knowledgeEvents"], [])

    def test_manual_checkin_rejects_any_client_date_atomically(self):
        before = self.store.read()
        for requested in (self.day, "2020-01-01", "2099-01-01", None, 0, [], "2026-02-30"):
            with self.subTest(day=requested), self.assertRaisesRegex(ValueError, "请勿指定日期"):
                self.store.action({"type": "checkin", "day": requested})
            self.assertEqual(self.store.read(), before)

    def test_manual_checkin_uses_machine_local_date_at_utc_day_boundary(self):
        class BoundaryClock(datetime):
            def astimezone(self, tz=None):
                return datetime(2026, 10, 5, 0, 30, tzinfo=timezone(timedelta(hours=8)))
        utc_instant = BoundaryClock(2026, 10, 4, 16, 30, tzinfo=timezone.utc)
        with patch("server.store.utc_now", return_value=utc_instant):
            state = self.store.action({"type": "checkin"})
        self.assertEqual(state["checkins"], ["2026-10-05"])

    def test_parallel_manual_checkins_create_only_one_day(self):
        stores = [Store(self.path, range(1, 101)) for _ in range(4)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: stores[i % 4].action({"type": "checkin"}), range(24)))
        state = self.store.read()
        self.assertEqual(state["checkins"], [self.day])
        self.assertEqual(state["events"], [])
        self.assertEqual(state["knowledgeEvents"], [])

    def test_backup_restores_manual_checkins_without_learning_records(self):
        incoming = copy.deepcopy(DEFAULT_STATE)
        incoming["checkins"] = ["2026-10-03", "2026-10-01", "2026-10-03"]
        restored = self.store.action({"type": "import", "state": incoming})
        self.assertEqual(restored["checkins"], ["2026-10-01", "2026-10-03"])
        self.assertEqual(restored["events"], [])
        self.assertEqual(restored["knowledgeEvents"], [])
        self.assertEqual(self.store.action({"type": "import", "state": restored}), restored)
        self.assertEqual(Store(self.path, range(1, 101)).read(), restored)

    def test_existing_dark_default_migration_runs_once_and_preserves_data_and_later_preferences(self):
        original = self.rate()
        original = self.store.action({"type": "settings", "settings": {"theme": "light", "workspaceName": "旧的空间"}})
        original["checkins"] = ["2026-10-01"]
        original["notes"]["1"] = "旧笔记"
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
            db.execute("DROP TABLE app_migrations")
        upgraded = Store(self.path, range(1, 101))
        expected = copy.deepcopy(original)
        expected["settings"]["theme"] = "dark"
        self.assertEqual(upgraded.read(), expected)
        selected = upgraded.action({"type": "settings", "settings": {"theme": "light"}})
        self.assertEqual(Store(self.path, range(1, 101)).read(), selected)
        upgraded.action({"type": "settings", "settings": {"theme": "dark"}})
        imported = upgraded.action({"type": "import", "state": original})
        self.assertEqual(Store(self.path, range(1, 101)).read(), imported)
        self.assertEqual(imported["settings"]["theme"], "light")
        with upgraded.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM app_migrations WHERE name='default-dark-v2.3'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_v1_upgrade_keeps_historical_checkins_and_original_backup(self):
        original = copy.deepcopy(DEFAULT_STATE)
        original["version"] = 1
        original["settings"]["theme"] = "light"
        original["checkins"] = ["2026-10-01"]
        original["notes"]["1"] = "第一版笔记"
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
            db.execute("DROP TABLE app_migrations")
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertEqual(upgraded["version"], 2)
        self.assertEqual(upgraded["settings"]["theme"], "dark")
        self.assertEqual(upgraded["checkins"], original["checkins"])
        self.assertEqual(upgraded["notes"], original["notes"])
        backups = list(self.path.parent.glob("before-v2-upgrade-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), original)

    def test_local_day_is_authoritative_with_one_day_clock_tolerance(self):
        for offset in (-1, 1):
            requested = (self.now.date() + timedelta(days=offset)).isoformat()
            state = self.rate(event=f"offset-{offset}", day=requested)
            self.assertEqual(state["events"][-1]["day"], self.day)
        state = self.rate(event="missing-day", day=None)
        self.assertEqual(state["events"][-1]["day"], self.day)
        before = self.store.read()
        for day in ("2026-02-30", "2026-1-04", "1999-01-01", 42):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.rate(event=f"bad-{day}", day=day)
        self.assertEqual(self.store.read(), before)

    def test_import_backup_preserves_original_and_restores_replacement(self):
        self.rate()
        original = self.store.action({"type": "note", "problemId": 1, "text": "原来的笔记"})
        incoming = copy.deepcopy(DEFAULT_STATE)
        incoming["notes"]["2"] = "备份中的笔记"
        result = self.store.action({"type": "import", "state": incoming})
        self.assertEqual(result, incoming)
        backups = list(self.path.parent.glob("before-import-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), original)
        self.assertFalse(list(self.path.parent.glob("*.tmp")))
        restored = self.store.action({"type": "import", "state": original})
        self.assertEqual(restored, original)

    def test_invalid_import_does_not_touch_data_or_create_backup(self):
        good = self.rate()
        variants = []
        bad = copy.deepcopy(good); bad["version"] = True; variants.append(bad)
        bad = copy.deepcopy(good); bad["cards"]["1"].pop("due"); variants.append(bad)
        bad = copy.deepcopy(good); bad["cards"]["1"]["due"] = "2026-10-05T00:00:00"; variants.append(bad)
        bad = copy.deepcopy(good); bad["cards"]["1"]["stability"] = float("nan"); variants.append(bad)
        bad = copy.deepcopy(good); bad["cards"]["1"]["lapses"] = 9; variants.append(bad)
        bad = copy.deepcopy(good); bad["events"].append(copy.deepcopy(bad["events"][0])); variants.append(bad)
        bad = copy.deepcopy(good); bad["events"][0]["eventId"] = ""; variants.append(bad)
        bad = copy.deepcopy(good); bad["events"][0]["seconds"] = -1; variants.append(bad)
        bad = copy.deepcopy(good); bad["notes"]["999"] = "不存在"; variants.append(bad)
        bad = copy.deepcopy(good); bad["drafts"]["1:java:leetcode"] = "bad"; variants.append(bad)
        bad = copy.deepcopy(good); bad["checkins"] = ["2026-02-30"]; variants.append(bad)
        bad = copy.deepcopy(good); bad["settings"]["retention"] = float("inf"); variants.append(bad)
        for incoming in variants:
            with self.subTest(incoming=incoming), self.assertRaises(ValueError):
                self.store.action({"type": "import", "state": incoming})
            self.assertEqual(self.store.read(), good)
        self.assertEqual(list(self.path.parent.glob("before-import-*")), [])

    def test_backup_failure_keeps_original_database(self):
        original = self.rate()
        with patch.object(self.store, "_backup", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.action({"type": "import", "state": copy.deepcopy(DEFAULT_STATE)})
        self.assertEqual(self.store.read(), original)

    def test_multiple_instances_do_not_lose_updates(self):
        stores = [Store(self.path, range(1, 101)) for _ in range(4)]
        def save(i):
            return stores[i % len(stores)].action({"type": "rate", "problemId": 1,
                "eventId": f"parallel-{i}", "rating": "good", "day": self.day, "seconds": 1})
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(save, range(32)))
        state = self.store.read()
        self.assertEqual(len(state["events"]), 32)
        self.assertEqual(state["cards"]["1"]["reviews"], 32)
        self.assertEqual(state["checkins"], [])
        payload = {"type": "rate", "problemId": 2, "eventId": "same-event", "rating": "good", "day": self.day}
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: stores[i % 4].action(payload), range(16)))
        final = self.store.read()
        self.assertEqual(final["cards"]["2"]["reviews"], 1)
        self.assertEqual(len(final["events"]), 33)

    def test_drafts_keep_languages_and_modes_separate(self):
        for language in ("python", "cpp"):
            for mode in ("leetcode", "acm"):
                self.store.action({"type": "draft", "problemId": 1, "language": language,
                                   "mode": mode, "code": f"{language}/{mode}"})
        self.assertEqual(len(self.store.read()["drafts"]), 4)

    def test_invalid_actions_roll_back(self):
        original = self.store.read()
        bad_actions = [None, {"type": "settings", "settings": []},
                       {"type": "note", "problemId": 1, "text": 5},
                       {"type": "favorite", "problemId": 999}, {"type": "unknown"}]
        for action in bad_actions:
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.store.action(action)
        for seconds in (-1, 14401, True, 1.5, "30"):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.rate(seconds=seconds)
        self.assertEqual(self.store.read(), original)


class LocalHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server.app import make_handler, TOKEN
        cls.token = TOKEN
        cls.temporary = tempfile.TemporaryDirectory(prefix="coderecall-http-test-")
        cls.store = Store(Path(cls.temporary.name) / "progress.db", range(1, 101))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.store, 8766))
        cls.port = cls.server.server_port
        cls.server.RequestHandlerClass = make_handler(cls.store, cls.port)
        cls.server.RequestHandlerClass.log_message = lambda *args: None
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temporary.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            data = response.read()
            return response.status, json.loads(data) if data else None
        finally:
            connection.close()

    def json_request(self, payload, **headers):
        return self.request("POST", "/api/action", json.dumps(payload),
                            {"Content-Type": "application/json", "X-CodeRecall-Token": self.token, **headers})

    def test_bootstrap_and_valid_development_origin(self):
        status, result = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertEqual(result["token"], self.token)
        self.assertEqual(len(result["problems"]), 100)
        status, _ = self.json_request({"type": "settings", "settings": {"dailyGoal": 3}},
                                     Host="127.0.0.1:5173", Origin="http://127.0.0.1:5173")
        self.assertEqual(status, 200)

    def test_rejects_foreign_or_malformed_hosts(self):
        for host in ("evil.example", "localhost.evil.example:8766", "127.0.0.1:9999", "localhost:bad", "localhost:8766@evil.example"):
            with self.subTest(host=host):
                status, _ = self.request("GET", "/api/bootstrap", headers={"Host": host})
                self.assertEqual(status, 403)

    def test_rejects_missing_token_and_untrusted_origins(self):
        status, _ = self.request("POST", "/api/action", "{}", {"Content-Type": "application/json"})
        self.assertEqual(status, 403)
        for origin in ("https://evil.example", "null", "http://localhost:9999", f"https://localhost:{self.port}"):
            with self.subTest(origin=origin):
                status, _ = self.json_request({"type": "settings", "settings": {}}, Origin=origin)
                self.assertEqual(status, 403)
        status, _ = self.json_request({}, **{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(status, 403)

    def test_bad_json_and_content_type_return_specific_errors(self):
        valid_headers = {"Content-Type": "application/json", "X-CodeRecall-Token": self.token}
        for body in ("{", "[]", '{"type":"settings","settings":{"retention":NaN}}'):
            status, result = self.request("POST", "/api/action", body, valid_headers)
            self.assertEqual(status, 400)
            self.assertIn("error", result)
        status, _ = self.request("POST", "/api/action", "{}", {**valid_headers, "Content-Type": "text/plain"})
        self.assertEqual(status, 415)
        status, _ = self.request("POST", "/api/action", "", {**valid_headers, "Content-Length": "0"})
        self.assertEqual(status, 413)


if __name__ == "__main__":
    unittest.main()
