"""A transparent, feedback-driven spaced repetition scheduler.

Stability is the number of days until estimated retention reaches 90%.
This is an original heuristic, not MaiMemo's proprietary production algorithm.
"""
from datetime import datetime, timedelta, timezone
import math

RATINGS = {"again", "hard", "good", "easy"}


def utc_now():
    return datetime.now(timezone.utc)


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("时间必须为包含时区的 ISO 日期字符串")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("时间格式错误，请使用包含时区的 ISO 日期字符串") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("时间缺少时区")
    return result


def aware_now(now=None):
    now = now or utc_now()
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("调度时间必须包含时区")
    return now.astimezone(timezone.utc)


def retention(card, now=None):
    if not card or not card.get("lastReview"):
        return None
    now = aware_now(now)
    elapsed = max(0, (now - parse_time(card["lastReview"])).total_seconds() / 86400)
    return round(0.9 ** (elapsed / max(0.1, card.get("stability", 1))), 4)


def schedule(previous, rating, target=0.9, now=None):
    if not isinstance(rating, str) or rating not in RATINGS:
        raise ValueError("请选择有效的记忆反馈")
    if type(target) not in (int, float) or not math.isfinite(target) or not 0.8 <= target <= 0.95:
        raise ValueError("目标记忆保留率范围为 80%–95%")
    now = aware_now(now)
    old = previous or {}
    strength = old.get("stability", 1)
    recall = retention(old, now)
    # First exposure starts conservatively; forgetting triggers same-day relearning.
    if rating == "again":
        strength = max(0.25, strength * 0.4)
        due = now + timedelta(minutes=10)
    else:
        if not old.get("lastReview"):
            strength = {"hard": 0.5, "good": 1, "easy": 4}[rating]
        else:
            gain = {"hard": 1.2, "good": 2.2, "easy": 3.2}[rating]
            strength *= gain + (1 - (recall or 0)) * (1 if rating == "hard" else 3)
        strength = min(365, max(0.25, strength))
        interval = max(1, round(strength * math.log(target) / math.log(0.9)))
        due = now + timedelta(days=min(365, interval))
    return {
        "stability": round(strength, 3),
        "due": due.isoformat(),
        "lastReview": now.isoformat(),
        "reviews": old.get("reviews", 0) + 1,
        "lapses": old.get("lapses", 0) + (rating == "again"),
        "rating": rating,
        "status": "learning" if rating == "again" else "review",
    }
