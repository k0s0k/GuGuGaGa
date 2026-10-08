"""Verify observable scheduling behavior, including clock and rating boundaries."""
from datetime import datetime, timedelta, timezone
import unittest

from server.scheduler import parse_time, retention, schedule


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 4, 15, 58, tzinfo=timezone.utc)

    def test_first_exposure_intervals_and_counters(self):
        for rating, days in (("hard", 1), ("good", 1), ("easy", 4)):
            with self.subTest(rating=rating):
                card = schedule(None, rating, now=self.now)
                self.assertEqual(parse_time(card["due"]) - self.now, timedelta(days=days))
                self.assertEqual(card["reviews"], 1)
                self.assertEqual(card["lapses"], 0)
                self.assertEqual(card["status"], "review")

    def test_forgetting_returns_in_ten_minutes(self):
        card = schedule(None, "again", now=self.now)
        self.assertEqual(parse_time(card["due"]) - self.now, timedelta(minutes=10))
        self.assertEqual(card["status"], "learning")
        self.assertEqual(card["lapses"], 1)
        next_card = schedule(card, "good", now=self.now + timedelta(minutes=10))
        self.assertEqual(next_card["reviews"], 2)
        self.assertEqual(next_card["lapses"], 1)
        self.assertEqual(next_card["status"], "review")

    def test_retention_definition_and_backward_clock(self):
        card = schedule(None, "easy", now=self.now)
        self.assertIsNone(retention(None, self.now))
        self.assertEqual(retention(card, self.now), 1)
        self.assertEqual(retention(card, self.now + timedelta(days=4)), 0.9)
        self.assertLess(retention(card, self.now + timedelta(days=8)), 0.9)
        self.assertEqual(retention(card, self.now - timedelta(days=1)), 1)

    def test_timezone_offsets_represent_the_same_instant(self):
        china = self.now.astimezone(timezone(timedelta(hours=8)))
        utc_card = schedule(None, "again", now=self.now)
        china_card = schedule(None, "again", now=china)
        self.assertEqual(utc_card, china_card)
        self.assertEqual(parse_time("2026-10-04T23:58:00+08:00"), self.now)
        self.assertEqual(parse_time("2026-10-04T15:58:00Z"), self.now)

    def test_higher_retention_means_shorter_interval(self):
        relaxed = schedule(None, "easy", target=0.8, now=self.now)
        frequent = schedule(None, "easy", target=0.95, now=self.now)
        self.assertLess(parse_time(frequent["due"]), parse_time(relaxed["due"]))

    def test_stability_caps_and_long_term_intervals(self):
        card = schedule(None, "easy", now=self.now)
        now = self.now
        for _ in range(20):
            now = parse_time(card["due"])
            card = schedule(card, "easy", target=0.8, now=now)
        self.assertEqual(card["stability"], 365)
        self.assertLessEqual(parse_time(card["due"]) - now, timedelta(days=365))
        self.assertEqual(card["reviews"], 21)

    def test_invalid_public_inputs_are_rejected(self):
        for value in (None, "bad", "2026-10-04T12:00:00", 42):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_time(value)
        for rating in (None, "unknown", [], 3):
            with self.subTest(rating=rating), self.assertRaises(ValueError):
                schedule(None, rating, now=self.now)
        for target in (0, 1, True, float("nan"), float("inf"), "0.9"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                schedule(None, "good", target=target, now=self.now)
        with self.assertRaises(ValueError):
            schedule(None, "good", now=datetime(2026, 10, 4))


if __name__ == "__main__":
    unittest.main()
