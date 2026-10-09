"""History-derived rewards, transactional spending and portable wallet backups."""
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server.stones import STONE_RULES, calculate_stones
from server.store import DEFAULT_STATE, Store


class StoneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gugugaga-stones-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "progress.db"
        self.now = datetime(2026, 10, 20, 12).astimezone().astimezone(timezone.utc)
        self.clock = patch("server.store.utc_now", return_value=self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.store = Store(self.path, range(1, 101))
        self.today = self.now.astimezone().date()

    def day(self, offset=0):
        return (self.today + timedelta(days=offset)).isoformat()

    def at(self, offset):
        return patch("server.store.utc_now", return_value=self.now + timedelta(days=offset))

    def rate(self, problem=1, event="new", **overrides):
        return self.store.action({"type": "rate", "problemId": problem, "eventId": event, "rating": "good", **overrides})

    def funded(self, days_ago=2, count=4):
        with self.at(-days_ago):
            for problem in range(1, count + 1):
                self.rate(problem, f"history-{problem}")
        return self.store.read()

    def makeup(self, offset=-1, **extra):
        return self.store.action({"type": "checkin-makeup", "day": self.day(offset), **extra})

    def test_new_wallet_has_no_reward_and_rule_values_are_server_authoritative(self):
        wallet = self.store.read()["stones"]
        self.assertEqual(wallet, {"balance": 0, "totalEarned": 0, "totalSpent": 0,
                                  "rules": STONE_RULES, "startedOn": self.day(), "makeups": []})
        self.assertEqual(Store(self.path, range(1, 101)).read()["stones"], wallet)

    def test_each_item_earns_once_per_day_and_next_day_review_earns_five(self):
        first = self.rate()
        self.assertEqual(first["stones"]["balance"], 10)
        repeated = self.rate(event="a-repeat", rating="again")
        self.assertEqual(repeated["stones"]["balance"], 10)
        self.assertEqual(self.rate(event="a-repeat", rating="again"), repeated)
        with self.at(1):
            reviewed = self.rate(event="next-day")
            self.assertEqual(reviewed["stones"]["balance"], 15)
            self.assertEqual(self.rate(event="next-day-again")["stones"]["balance"], 15)

    def test_knowledge_and_algorithm_domains_reward_separately(self):
        self.store.action({"type": "knowledge-import", "document": {
            "format": "coderecall.knowledge", "version": 1, "deck": {"id": "deck", "title": "知识"},
            "items": [{"id": "1", "title": "知识点", "kind": "qa", "prompt": "问题", "answer": "答案"}]}})
        self.rate()
        payload = {"type": "knowledge-rate", "itemId": "1", "eventId": "knowledge-first", "rating": "good"}
        first = self.store.action(payload)
        self.assertEqual(first["stones"]["balance"], 20)
        self.assertEqual(self.store.action({**payload, "eventId": "knowledge-repeat"})["stones"]["balance"], 20)
        with self.at(1):
            self.assertEqual(self.store.action({**payload, "eventId": "knowledge-next-day"})["stones"]["balance"], 25)

    def test_manual_checkin_rewards_two_once_without_learning(self):
        first = self.store.action({"type": "checkin"})
        self.assertEqual(first["stones"]["balance"], 2)
        self.assertEqual(first["events"], [])
        self.assertEqual(first["knowledgeEvents"], [])
        self.assertEqual(self.store.action({"type": "checkin"}), first)
        with self.at(1):
            self.assertEqual(self.store.action({"type": "checkin"})["stones"]["balance"], 4)

    def test_makeup_spends_balance_but_never_lifetime_earnings_or_rewards_itself(self):
        before = self.funded()
        after = self.makeup()
        self.assertEqual(after["checkins"], [self.day(-1)])
        self.assertEqual(after["stones"]["balance"], 20)
        self.assertEqual(after["stones"]["totalEarned"], 40)
        self.assertEqual(after["stones"]["totalSpent"], 20)
        self.assertEqual(after["stones"]["makeups"], [{"day": self.day(-1), "cost": 20, "spentAt": self.now.isoformat()}])
        self.assertEqual(after["events"], before["events"])
        self.assertEqual(after["knowledgeEvents"], before["knowledgeEvents"])
        self.assertEqual(self.makeup(), after)
        with self.at(35):
            self.assertEqual(self.makeup(), after, "A retry stays idempotent after the original eligibility window.")

    def test_existing_manual_checkin_is_not_charged_or_converted_to_makeup(self):
        with self.at(-1):
            self.store.action({"type": "checkin"})
        before = self.store.read()
        self.assertEqual(self.makeup(), before)
        self.assertEqual(before["stones"]["balance"], 2)
        self.assertEqual(before["stones"]["makeups"], [])

    def test_insufficient_balance_leaves_all_state_unchanged(self):
        self.funded(count=1)
        before = self.store.read()
        with self.assertRaisesRegex(ValueError, "石头不足"):
            self.makeup()
        self.assertEqual(self.store.read(), before)

    def test_makeup_date_and_server_fixed_cost_rejections_are_atomic(self):
        self.funded(days_ago=40)
        before = self.store.read()
        for payload in ({"day": self.day()}, {"day": self.day(1)}, {"day": self.day(-31)},
                        {"day": "2026-02-30"}, {"day": None}, {"day": 7}, {"day": self.day(-1), "cost": 0}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.store.action({"type": "checkin-makeup", **payload})
            self.assertEqual(self.store.read(), before)
        boundary = self.makeup(-30)
        self.assertIn(self.day(-30), boundary["checkins"])
        self.assertEqual(boundary["stones"]["balance"], 20)

    def test_makeup_cannot_precede_first_use_even_when_balance_is_sufficient(self):
        self.funded(days_ago=2)
        before = self.store.read()
        with self.assertRaisesRegex(ValueError, "开始使用以来"):
            self.makeup(-3)
        self.assertEqual(self.store.read(), before)
        self.assertEqual(self.makeup(-2)["stones"]["balance"], 20)

    def test_parallel_spending_and_retries_cannot_overspend(self):
        self.funded(days_ago=4, count=2)
        stores = [Store(self.path, range(1, 101)) for _ in range(4)]
        def attempt(index):
            try:
                stores[index % 4].action({"type": "checkin-makeup", "day": self.day(-1 if index % 2 else -2)})
                return True
            except ValueError as error:
                self.assertIn("石头不足", str(error))
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(24)))
        self.assertTrue(any(results))
        result = self.store.read()
        self.assertEqual(result["stones"]["balance"], 0)
        self.assertEqual(result["stones"]["totalSpent"], 20)
        self.assertEqual(len(result["stones"]["makeups"]), 1)
        self.assertEqual(len(result["checkins"]), 1)

    def test_parallel_daily_reviews_credit_only_one_reward(self):
        stores = [Store(self.path, range(1, 101)) for _ in range(4)]
        def rate(index):
            return stores[index % 4].action({"type": "rate", "problemId": 1, "eventId": f"parallel-{index}", "rating": "good"})
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(rate, range(24)))
        result = self.store.read()
        self.assertEqual(result["stones"]["balance"], 10)
        self.assertEqual(len(result["events"]), 24)

    def test_old_database_history_is_credited_deterministically_once(self):
        self.funded()
        self.store.action({"type": "checkin"})
        original = self.store.read()
        original.pop("stones")
        original["settings"]["theme"] = "light"
        original["settings"]["workspaceName"] = "我的名字"
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        upgraded = Store(self.path, range(1, 101)).read()
        self.assertEqual(upgraded["stones"]["balance"], 42)
        self.assertEqual(upgraded["stones"]["startedOn"], self.day(-2))
        self.assertEqual(upgraded["settings"], original["settings"])
        self.assertEqual(upgraded["events"], original["events"])
        self.assertEqual(Store(self.path, range(1, 101)).read(), upgraded)

    def test_legacy_v1_v2_backups_derive_rewards_without_client_balances(self):
        self.funded()
        legacy = self.store.read()
        legacy.pop("stones")
        for version in (1, 2):
            legacy["version"] = version
            restored = self.store.action({"type": "import", "state": legacy})
            self.assertEqual(restored["stones"]["balance"], 40)
            self.assertEqual(restored["stones"]["startedOn"], self.day(-2))
        empty = self.store.action({"type": "import", "state": copy.deepcopy(DEFAULT_STATE)})
        self.assertEqual(empty["stones"]["balance"], 0)
        self.assertEqual(empty["stones"]["startedOn"], self.day())

    def test_wallet_roundtrip_restores_spending_and_recomputes_fake_totals_and_rules(self):
        self.funded()
        original = self.makeup()
        fake = copy.deepcopy(original)
        fake["stones"].update(balance=999999, totalEarned=999999, totalSpent=0, rules={"makeup": 0})
        restored = self.store.action({"type": "import", "state": fake})
        self.assertEqual(restored, original)
        self.assertEqual(Store(self.path, range(1, 101)).read(), original)

    def test_invalid_spending_records_never_overwrite_or_create_import_backups(self):
        self.funded()
        original = self.makeup()
        variants = []
        bad = copy.deepcopy(original); bad["stones"] = None; variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["makeups"] = {}; variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["makeups"].append(bad["stones"]["makeups"][0]); variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["makeups"][0]["cost"] = 0; variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["makeups"][0]["cost"] = True; variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["makeups"][0]["spentAt"] = "2026-10-20T12:00:00"; variants.append(bad)
        bad = copy.deepcopy(original); bad["checkins"] = []; variants.append(bad)
        bad = copy.deepcopy(original); bad["events"] = []; variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["startedOn"] = "2026-02-30"; variants.append(bad)
        bad = copy.deepcopy(original); bad["stones"]["makeups"][0]["day"] = self.day(-3); bad["checkins"] = [self.day(-3)]; variants.append(bad)
        for incoming in variants:
            with self.subTest(incoming=incoming), self.assertRaises(ValueError):
                self.store.action({"type": "import", "state": incoming})
            self.assertEqual(self.store.read(), original)
        self.assertEqual(list(self.path.parent.glob("before-import-*.json")), [])

    def test_event_time_selects_first_daily_feedback_after_unordered_legacy_import(self):
        self.rate()
        self.rate(event="repeat")
        incoming = self.store.read()
        incoming["events"][1]["time"] = (self.now + timedelta(minutes=1)).isoformat()
        incoming["events"].reverse()
        restored = self.store.action({"type": "import", "state": incoming})
        self.assertEqual(restored["stones"]["balance"], 10)

    def test_local_calendar_boundary_uses_server_local_day_for_rewards_and_makeup(self):
        self.funded(days_ago=2)
        boundary = datetime(self.today.year, self.today.month, self.today.day, 0, 30).astimezone().astimezone(timezone.utc)
        with patch("server.store.utc_now", return_value=boundary):
            signed = self.store.action({"type": "checkin"})
            paid = self.makeup()
        self.assertIn(boundary.astimezone().date().isoformat(), signed["checkins"])
        self.assertEqual(signed["stones"]["balance"], 42)
        wallet = calculate_stones(signed, boundary)
        self.assertEqual(wallet["balance"], 42)
        self.assertEqual(paid["stones"]["balance"], 22)
        self.assertEqual(paid["stones"]["makeups"][0]["spentAt"], boundary.isoformat())

    def test_legacy_empty_database_gains_zero_balance_and_keeps_first_open_day(self):
        original = copy.deepcopy(DEFAULT_STATE)
        with self.store.connect() as db:
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(original),))
        migrated = Store(self.path, range(1, 101)).read()
        self.assertEqual(migrated["stones"]["balance"], 0)
        self.assertEqual(migrated["stones"]["startedOn"], self.day())
        with self.at(4):
            self.assertEqual(Store(self.path, range(1, 101)).read()["stones"]["startedOn"], self.day())

    def test_makeup_backups_remain_valid_across_timezones_at_utc_midnight_boundary(self):
        self.funded()
        original = self.makeup()
        # In UTC+8 this was a valid previous-day makeup at 00:30, even
        # though its UTC timestamp has the same date as the made-up day.
        original["stones"]["makeups"][0]["spentAt"] = self.day(-1) + "T16:30:00+00:00"
        from server.scheduler import parse_time
        class TravelerDateTime(datetime):
            def astimezone(self, tz=None):
                return super().astimezone(tz or timezone(timedelta(hours=-7)))
        def traveler_time(value):
            parsed = parse_time(value)
            return TravelerDateTime.fromisoformat(parsed.isoformat())
        with patch("server.stones.parse_time", side_effect=traveler_time):
            restored = self.store.action({"type": "import", "state": original})
        self.assertEqual(restored["stones"]["balance"], 20)
        self.assertEqual(restored["stones"]["totalEarned"], 40)


if __name__ == "__main__":
    unittest.main()
