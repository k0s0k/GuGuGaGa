import copy
from contextlib import contextmanager
from datetime import date
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4
from .scheduler import RATINGS, schedule, utc_now, parse_time

DEFAULT_STATE = {
    "version": 1,
    "settings": {"dailyGoal": 3, "newPerDay": 3, "language": "python", "mode": "leetcode", "retention": 0.9, "theme": "light"},
    "cards": {}, "notes": {}, "favorites": [], "drafts": {}, "events": [], "checkins": [],
}


class Store:
    def __init__(self, path, problem_ids):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.problem_ids = {str(i) for i in problem_ids}
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO state VALUES (1, ?)", (json.dumps(DEFAULT_STATE),))

    @contextmanager
    def connect(self):
        # sqlite 的事务上下文不会关闭连接，因此显式释放文件句柄。
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def read(self):
        with self.lock, self.connect() as db:
            return json.loads(db.execute("SELECT data FROM state WHERE id=1").fetchone()[0])

    def _id(self, value):
        value = str(value)
        if value not in self.problem_ids:
            raise ValueError("题目不存在")
        return value

    @staticmethod
    def _day(value):
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError("日期格式错误")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("日期格式错误，请使用 YYYY-MM-DD") from exc
        if parsed.isoformat() != value:
            raise ValueError("日期格式错误，请使用 YYYY-MM-DD")
        return value

    @classmethod
    def local_day(cls, requested, now):
        today = now.astimezone().date()
        if requested is not None:
            requested_day = date.fromisoformat(cls._day(requested))
            # 浏览器与本机可能在跨日瞬间或时区设置上相差一天。
            if abs((requested_day - today).days) > 1:
                raise ValueError("学习日期与本机日期相差过大，请检查系统时间并刷新页面")
        return today.isoformat()

    @staticmethod
    def settings(value):
        if not isinstance(value, dict):
            raise ValueError("设置格式错误")
        result = copy.deepcopy(DEFAULT_STATE["settings"])
        for key in result:
            if key in value:
                result[key] = value[key]
        if type(result["dailyGoal"]) is not int or not 1 <= result["dailyGoal"] <= 30:
            raise ValueError("每日目标范围为 1–30 题")
        if type(result["newPerDay"]) is not int or not 1 <= result["newPerDay"] <= 10:
            raise ValueError("每日新题范围为 1–10 题")
        if result["language"] not in ("python", "cpp") or result["mode"] not in ("leetcode", "acm"):
            raise ValueError("语言或答题模式无效")
        if result["theme"] not in ("light", "dark"):
            raise ValueError("主题无效")
        if type(result["retention"]) not in (int, float) or not math.isfinite(result["retention"]) or not 0.8 <= result["retention"] <= 0.95:
            raise ValueError("目标记忆保留率范围为 80%–95%")
        return result

    def validate_import(self, value):
        if not isinstance(value, dict) or type(value.get("version")) is not int or value.get("version") != 1:
            raise ValueError("不支持的备份格式或版本")
        state = copy.deepcopy(DEFAULT_STATE)
        state["settings"] = self.settings(value.get("settings", {}))
        for key in ("cards", "notes", "drafts"):
            if not isinstance(value.get(key, {}), dict):
                raise ValueError("备份结构错误")
        for key in ("favorites", "events", "checkins"):
            if not isinstance(value.get(key, []), list):
                raise ValueError("备份结构错误")
        for pid, card in value.get("cards", {}).items():
            self._id(pid)
            if not isinstance(card, dict) or card.get("rating") not in ("again", "hard", "good", "easy"):
                raise ValueError("复习记录错误")
            for field in ("due", "lastReview"):
                parse_time(card.get(field))
            if parse_time(card["due"]) < parse_time(card["lastReview"]):
                raise ValueError("下次复习时间不能早于最近学习时间")
            if type(card.get("stability")) not in (int, float) or not math.isfinite(card["stability"]) or not 0.1 <= card["stability"] <= 365:
                raise ValueError("记忆强度无效")
            for field in ("reviews", "lapses"):
                if type(card.get(field)) is not int or not 0 <= card[field] <= 100000:
                    raise ValueError("复习次数无效")
            if card["reviews"] < 1 or card["lapses"] > card["reviews"]:
                raise ValueError("复习次数与遗忘次数不一致")
            state["cards"][pid] = {k: card[k] for k in ("due", "lastReview", "rating", "stability", "reviews", "lapses")}
            state["cards"][pid]["status"] = "learning" if card["rating"] == "again" else "review"
        for pid, note in value.get("notes", {}).items():
            self._id(pid)
            if not isinstance(note, str) or len(note) > 30000:
                raise ValueError("笔记内容无效")
            state["notes"][pid] = note
        for key, code in value.get("drafts", {}).items():
            if not isinstance(key, str):
                raise ValueError("草稿标识无效")
            parts = key.split(":")
            if len(parts) != 3 or parts[0] not in self.problem_ids or parts[1] not in ("python", "cpp") or parts[2] not in ("leetcode", "acm") or not isinstance(code, str) or len(code) > 100000:
                raise ValueError("草稿格式无效")
            state["drafts"][key] = code
        state["favorites"] = list(dict.fromkeys(int(self._id(i)) for i in value.get("favorites", [])))
        seen = set()
        for event in value.get("events", []):
            if not isinstance(event, dict) or not isinstance(event.get("eventId"), str) or not 1 <= len(event["eventId"]) <= 100 or event["eventId"] in seen:
                raise ValueError("学习记录标识无效")
            seen.add(event["eventId"])
            self._id(event.get("problemId"))
            self._day(event.get("day"))
            if event.get("rating") not in ("again", "hard", "good", "easy") or event.get("kind") not in ("new", "review"):
                raise ValueError("学习记录无效")
            if type(event.get("seconds")) is not int or not 0 <= event["seconds"] <= 14400:
                raise ValueError("学习时长无效")
            parse_time(event.get("time"))
            state["events"].append({k: event[k] for k in ("eventId", "problemId", "day", "rating", "kind", "seconds", "time")})
            state["events"][-1]["problemId"] = int(self._id(event["problemId"]))
        state["checkins"] = sorted(set(self._day(day) for day in value.get("checkins", [])))
        event_days = {event["day"] for event in state["events"]}
        if any(day not in event_days for day in state["checkins"]):
            raise ValueError("打卡日期缺少对应学习记录")
        return state

    @staticmethod
    def _checkin(state, day):
        completed = len({event["problemId"] for event in state["events"] if event["day"] == day})
        if completed >= state["settings"]["dailyGoal"] and day not in state["checkins"]:
            state["checkins"].append(day)
            state["checkins"].sort()

    def _backup(self, state):
        stem = "before-import-" + utc_now().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex[:8]
        backup = self.path.parent / (stem + ".json")
        temporary = self.path.parent / (stem + ".tmp")
        # 备份落盘完成后才覆盖数据库；同目录重命名避免半写入文件。
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(backup)

    def action(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("请求格式错误")
        kind = payload.get("type")
        with self.lock, self.connect() as db:
            # 在读取前取得写事务锁，多个 Store 实例/线程也不会丢失更新。
            db.execute("BEGIN IMMEDIATE")
            state = json.loads(db.execute("SELECT data FROM state WHERE id=1").fetchone()[0])
            if kind in ("rate", "favorite", "note", "draft"):
                pid = self._id(payload.get("problemId"))
            if kind == "rate":
                event_id = payload.get("eventId")
                if not isinstance(event_id, str) or not 1 <= len(event_id) <= 100:
                    raise ValueError("学习记录标识无效")
                rating = payload.get("rating")
                if not isinstance(rating, str) or rating not in RATINGS:
                    raise ValueError("请选择有效的记忆反馈")
                existing = next((event for event in state["events"] if event["eventId"] == event_id), None)
                if existing:
                    if existing["problemId"] != int(pid) or existing["rating"] != rating:
                        raise ValueError("学习记录标识已被其他操作使用，请刷新后重试")
                    return state  # 即使次日重试，已有事件也不会再次增加复习次数。
                old = state["cards"].get(pid)
                now = utc_now()
                day = self.local_day(payload.get("day"), now)
                seconds = payload.get("seconds", 0)
                if type(seconds) is not int or not 0 <= seconds <= 14400:
                    raise ValueError("学习时长必须为 0–14400 的整数秒")
                state["cards"][pid] = schedule(old, rating, state["settings"]["retention"], now)
                state["events"].append({"eventId": event_id, "problemId": int(pid), "day": day, "rating": rating, "kind": "review" if old else "new", "time": now.isoformat(), "seconds": seconds})
                self._checkin(state, day)
            elif kind == "favorite":
                number = int(pid)
                if number in state["favorites"]:
                    state["favorites"].remove(number)
                else:
                    state["favorites"].append(number)
            elif kind == "note":
                note = payload.get("text")
                if not isinstance(note, str) or len(note) > 30000:
                    raise ValueError("笔记最多 30000 字")
                state["notes"][pid] = note
            elif kind == "draft":
                language, mode, code = payload.get("language"), payload.get("mode"), payload.get("code")
                if language not in ("python", "cpp") or mode not in ("leetcode", "acm") or not isinstance(code, str) or len(code) > 100000:
                    raise ValueError("代码草稿无效")
                state["drafts"][f"{pid}:{language}:{mode}"] = code
            elif kind == "settings":
                updates = payload.get("settings")
                if not isinstance(updates, dict):
                    raise ValueError("设置格式错误")
                state["settings"] = self.settings({**state["settings"], **updates})
                self._checkin(state, self.local_day(None, utc_now()))
            elif kind == "import":
                replacement = self.validate_import(payload.get("state"))
                self._backup(state)
                state = replacement
            else:
                raise ValueError("不支持的操作")
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state, ensure_ascii=False, allow_nan=False),))
            return state
