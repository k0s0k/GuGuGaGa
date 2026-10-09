"""Derive stone rewards from study history; persist only makeup spending facts."""
from datetime import date, timedelta, timezone

from .scheduler import parse_time


STONE_RULES = {"learn": 10, "review": 5, "checkin": 2, "makeup": 20, "makeupWindowDays": 30}
_MISSING = object()


def calendar_day(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("石头记录中的日期格式错误")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("石头记录中的日期格式错误") from exc
    if parsed.isoformat() != value:
        raise ValueError("石头记录中的日期格式错误")
    return parsed


def calculate_stones(state, now):
    """Ignore imported balances/rules and reconstruct rewards and spending."""
    today = now.astimezone().date()
    previous = state.get("stones", _MISSING)
    if previous is _MISSING:
        previous = {}
    if not isinstance(previous, dict):
        raise ValueError("石头账户格式错误")
    records = previous.get("makeups", [])
    if not isinstance(records, list):
        raise ValueError("补签记录格式错误")
    activity_days = [calendar_day(event["day"]) for event in state["events"] + state["knowledgeEvents"]]
    candidate_paid_days = {record.get("day") for record in records if isinstance(record, dict) and isinstance(record.get("day"), str)}
    activity_days.extend(calendar_day(day) for day in state["checkins"] if day not in candidate_paid_days)
    started_on = min([today, *activity_days])
    if "startedOn" in previous:
        started_on = min(started_on, calendar_day(previous["startedOn"]))
    checkins = set(state["checkins"])
    paid_days = set()
    makeups = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("补签记录格式错误")
        day = record.get("day")
        parsed_day = calendar_day(day)
        if day in paid_days:
            raise ValueError("补签日期不能重复")
        if day not in checkins:
            raise ValueError("补签记录缺少对应签到日期")
        cost = record.get("cost")
        if type(cost) is not int or cost != STONE_RULES["makeup"]:
            raise ValueError("补签石头数量无效")
        spent_at = parse_time(record.get("spentAt")).astimezone(timezone.utc)
        # Backups may be restored in another timezone. A local calendar day
        # can differ from the saved UTC day by one; live actions enforce the
        # exact local 30-day window, while historical validation allows that
        # timezone shift without invalidating an otherwise valid backup.
        utc_spent_day = spent_at.date()
        earliest = max(started_on, utc_spent_day - timedelta(days=STONE_RULES["makeupWindowDays"] + 1))
        if not earliest <= parsed_day <= utc_spent_day:
            raise ValueError("补签日期不在该次补签的有效范围内")
        paid_days.add(day)
        makeups.append({"day": day, "spentAt": spent_at.isoformat(), "cost": cost})
    makeups.sort(key=lambda record: (record["spentAt"], record["day"]))

    first_events = {}
    for domain, events, item_key in (("problem", state["events"], "problemId"),
                                     ("knowledge", state["knowledgeEvents"], "itemId")):
        for event in events:
            key = (domain, str(event[item_key]), event["day"])
            order = parse_time(event["time"])
            previous_event = first_events.get(key)
            if previous_event is None or order < previous_event[0]:
                first_events[key] = (order, event)
    learning = sum(STONE_RULES["learn"] if event["kind"] == "new" else STONE_RULES["review"]
                   for _, event in first_events.values())
    total_earned = learning + len(checkins - paid_days) * STONE_RULES["checkin"]
    total_spent = sum(record["cost"] for record in makeups)
    if total_spent > total_earned:
        raise ValueError("补签记录的支出超过已获得的石头")
    return {"balance": total_earned - total_spent, "totalEarned": total_earned,
            "totalSpent": total_spent, "rules": dict(STONE_RULES),
            "startedOn": started_on.isoformat(), "makeups": makeups}


def make_up_checkin(state, payload, now):
    if set(payload) != {"type", "day"}:
        raise ValueError("补签只需提供日期，费用由系统确定")
    day = payload.get("day")
    requested = calendar_day(day)
    today = now.astimezone().date()
    wallet = calculate_stones(state, now)
    oldest = max(calendar_day(wallet["startedOn"]), today - timedelta(days=STONE_RULES["makeupWindowDays"]))
    if requested >= today:
        raise ValueError("只能补签开始使用以来、最近 30 天内的过去日期")
    # A retry, or a day already checked in manually, never spends again.
    if day in state["checkins"]:
        return
    if requested < oldest:
        raise ValueError("只能补签开始使用以来、最近 30 天内的过去日期")
    if wallet["balance"] < STONE_RULES["makeup"]:
        raise ValueError(f"石头不足，补签需要 {STONE_RULES['makeup']} 颗")
    wallet["makeups"].append({"day": day, "spentAt": now.astimezone(timezone.utc).isoformat(), "cost": STONE_RULES["makeup"]})
    state["stones"] = wallet
    state["checkins"].append(day)
    state["checkins"].sort()
