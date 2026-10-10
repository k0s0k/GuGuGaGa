import base64
import binascii
import copy
from contextlib import contextmanager
from datetime import date
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import unicodedata
from uuid import uuid4
from .scheduler import RATINGS, schedule, utc_now, parse_time
from .knowledge import deck_fields, item_fields, identifier, import_into, text
from .stones import calculate_stones, make_up_checkin
from .json_support import validate_json_depth

MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_AVATAR_BYTES = 256 * 1024


def workspace_name(value):
    if not isinstance(value, str):
        raise ValueError("工作空间名称须为 1–40 个字符")
    if any(unicodedata.category(char) in ("Cc", "Cs", "Zl", "Zp") for char in value):
        raise ValueError("工作空间名称不能包含换行或控制字符")
    value = value.strip()
    if not 1 <= len(value) <= 40:
        raise ValueError("工作空间名称须为 1–40 个字符")
    return value


def avatar_data_url(value):
    """Accept bounded, canonical raster data URLs; never persist remote URLs or SVG."""
    if not isinstance(value, str):
        raise ValueError("头像格式无效")
    if value == "":
        return value
    if len(value) > ((MAX_AVATAR_BYTES + 2) // 3) * 4 + 24:
        raise ValueError("头像压缩后最多 256 KB")
    prefix, separator, encoded = value.partition(",")
    if not separator or prefix not in ("data:image/png;base64", "data:image/jpeg;base64", "data:image/webp;base64"):
        raise ValueError("头像仅支持 PNG、JPEG 或 WebP 图片")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("头像图片编码无效") from exc
    if len(data) > MAX_AVATAR_BYTES:
        raise ValueError("头像压缩后最多 256 KB")
    if not data or base64.b64encode(data).decode("ascii") != encoded:
        raise ValueError("头像图片编码无效")
    if prefix == "data:image/png;base64":
        valid = (len(data) >= 45 and data.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
                 and data.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"))
    elif prefix == "data:image/jpeg;base64":
        valid = len(data) >= 4 and data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")
    else:
        valid = (len(data) >= 20 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
                 and data[12:16] in (b"VP8 ", b"VP8L", b"VP8X")
                 and int.from_bytes(data[4:8], "little") == len(data) - 8)
    if not valid:
        raise ValueError("头像图片内容与格式不匹配")
    return value

DEFAULT_STATE = {
    "version": 2,
    "settings": {"dailyGoal": 3, "newPerDay": 3, "language": "python", "mode": "leetcode", "retention": 0.9, "theme": "dark", "includeHot100": True, "studyDeckIds": [], "avatar": "", "workspaceName": "我的工作空间"},
    "cards": {}, "notes": {}, "favorites": [], "drafts": {}, "events": [], "checkins": [],
    "solutions": {}, "decks": {}, "knowledge": {}, "knowledgeCards": {},
    "knowledgeNotes": {}, "knowledgeFavorites": [], "knowledgeEvents": [],
}


class Store:
    def __init__(self, path, problem_ids):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.problem_ids = {str(i) for i in problem_ids}
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO state VALUES (1, ?)", (json.dumps(DEFAULT_STATE),))
            state = json.loads(db.execute("SELECT data FROM state WHERE id=1").fetchone()[0])
            if type(state.get("version")) is not int or state["version"] not in (1, 2):
                raise ValueError("此数据库版本无法打开，请使用相应版本的软件")
            if state["version"] == 1:
                upgraded = self.validate_import(state)
                self._backup(state, "before-v2-upgrade")
                db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(upgraded, ensure_ascii=False, allow_nan=False),))
                state = upgraded
            elif any(key not in state.get("settings", {}) for key in ("includeHot100", "studyDeckIds", "avatar", "workspaceName")):
                # Additive v2 preference: retain all existing study data unchanged.
                preferences = state.get("settings", {})
                if "studyDeckIds" not in preferences:
                    preferences = {**preferences, "studyDeckIds": list(state.get("decks", {}))}
                state["settings"] = self.settings(preferences)
                self._validate_study_decks(state)
                db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state, ensure_ascii=False, allow_nan=False),))
            # Apply the new default once; later explicit choices and imported
            # preferences remain untouched, including on subsequent launches.
            db.execute("CREATE TABLE IF NOT EXISTS app_migrations (name TEXT PRIMARY KEY)")
            migration = "default-dark-v2.3"
            if not db.execute("SELECT 1 FROM app_migrations WHERE name=?", (migration,)).fetchone():
                state["settings"]["theme"] = "dark"
                db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state, ensure_ascii=False, allow_nan=False),))
                db.execute("INSERT INTO app_migrations (name) VALUES (?)", (migration,))
            wallet = calculate_stones(state, utc_now())
            if state.get("stones") != wallet:
                state["stones"] = wallet
                db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state, ensure_ascii=False, allow_nan=False),))

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
        if type(result["includeHot100"]) is not bool:
            raise ValueError("Hot 100 推荐开关必须为布尔值")
        selected_decks = result["studyDeckIds"]
        if not isinstance(selected_decks, list) or len(selected_decks) > 500:
            raise ValueError("学习计划知识库必须为数组，最多 500 项")
        result["studyDeckIds"] = list(dict.fromkeys(identifier(deck_id, "学习计划知识库 ID") for deck_id in selected_decks))
        result["avatar"] = avatar_data_url(result["avatar"])
        result["workspaceName"] = workspace_name(result["workspaceName"])
        if type(result["retention"]) not in (int, float) or not math.isfinite(result["retention"]) or not 0.8 <= result["retention"] <= 0.95:
            raise ValueError("目标记忆保留率范围为 80%–95%")
        return result

    @staticmethod
    def _validate_study_decks(state):
        if any(deck_id not in state["decks"] for deck_id in state["settings"]["studyDeckIds"]):
            raise ValueError("学习计划包含不存在的知识库，请重新选择")

    def validate_import(self, value):
        if not isinstance(value, dict) or type(value.get("version")) is not int or value.get("version") not in (1, 2):
            raise ValueError("不支持的备份格式或版本")
        validate_json_depth(value)
        try:
            if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_STATE_BYTES:
                raise ValueError("备份最多 64 MB")
        except (TypeError, OverflowError, RecursionError) as exc:
            raise ValueError("备份内容无效") from exc
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
        if value["version"] == 2:
            self._validate_knowledge_state(value, state)
        # Missing means a pre-selection backup; explicit [] means no decks.
        if "studyDeckIds" not in value.get("settings", {}):
            state["settings"]["studyDeckIds"] = list(state["decks"])
        self._validate_study_decks(state)
        if "stones" in value:
            state["stones"] = value["stones"]
        state["stones"] = calculate_stones(state, utc_now())
        return state

    def _solution_key(self, key):
        if not isinstance(key, str):
            raise ValueError("题解标识无效")
        parts = key.split(":")
        if len(parts) != 3 or parts[0] not in self.problem_ids or parts[1] not in ("python", "cpp") or parts[2] not in ("leetcode", "acm"):
            raise ValueError("题解语言或答题模式无效")
        return key

    @staticmethod
    def _solution(value, updated_at=None):
        if not isinstance(value, dict):
            raise ValueError("题解格式错误")
        result = {key: text(value.get(key), label, limit) for key, label, limit in
                  (("brief", "简洁题解", 100000), ("annotated", "注释题解", 100000), ("explanation", "题解解析", 30000))}
        result["updatedAt"] = updated_at if updated_at is not None else value.get("updatedAt")
        parse_time(result["updatedAt"])
        return result

    @staticmethod
    def _validate_card(card):
        if not isinstance(card, dict) or card.get("rating") not in ("again", "hard", "good", "easy"):
            raise ValueError("复习记录错误")
        if parse_time(card.get("due")) < parse_time(card.get("lastReview")):
            raise ValueError("下次复习时间不能早于最近学习时间")
        strength = card.get("stability")
        if type(strength) not in (int, float) or not math.isfinite(strength) or not 0.1 <= strength <= 365:
            raise ValueError("记忆强度无效")
        if any(type(card.get(field)) is not int or not 0 <= card[field] <= 100000 for field in ("reviews", "lapses")):
            raise ValueError("复习次数无效")
        if card["reviews"] < 1 or card["lapses"] > card["reviews"]:
            raise ValueError("复习次数与遗忘次数不一致")
        result = {key: card[key] for key in ("due", "lastReview", "rating", "stability", "reviews", "lapses")}
        result["status"] = "learning" if card["rating"] == "again" else "review"
        return result

    def _validate_knowledge_state(self, value, state):
        for key, maximum in (("solutions", 400), ("decks", 500), ("knowledge", 10000), ("knowledgeCards", 10000), ("knowledgeNotes", 10000)):
            if not isinstance(value.get(key, {}), dict) or len(value.get(key, {})) > maximum:
                raise ValueError(f"备份 {key} 格式错误或数量过多")
        for key, maximum in (("knowledgeFavorites", 10000), ("knowledgeEvents", 100000)):
            if not isinstance(value.get(key, []), list) or len(value.get(key, [])) > maximum:
                raise ValueError(f"备份 {key} 格式错误或数量过多")
        for key, solution in value.get("solutions", {}).items():
            state["solutions"][self._solution_key(key)] = self._solution(solution)
        for key, deck in value.get("decks", {}).items():
            identifier(key, "知识库 ID")
            fields = deck_fields(deck)
            if fields.get("id") != key:
                raise ValueError("知识库 ID 与索引不一致")
            for field in ("createdAt", "updatedAt"):
                parse_time(deck.get(field))
            state["decks"][key] = {**fields, "createdAt": deck["createdAt"], "updatedAt": deck["updatedAt"]}
        for key, item in value.get("knowledge", {}).items():
            identifier(key, "知识点 ID")
            fields = item_fields(item)
            if fields.get("id") != key or not isinstance(item.get("deckId"), str) or item["deckId"] not in state["decks"]:
                raise ValueError("知识点 ID 或所属知识库无效")
            if type(item.get("archived")) is not bool:
                raise ValueError("知识点归档状态必须为布尔值")
            for field in ("createdAt", "updatedAt"):
                parse_time(item.get(field))
            state["knowledge"][key] = {**fields, **{field: item[field] for field in ("deckId", "archived", "createdAt", "updatedAt")}}
        for key, card in value.get("knowledgeCards", {}).items():
            self._knowledge_id(state, key)
            state["knowledgeCards"][key] = self._validate_card(card)
        for key, note in value.get("knowledgeNotes", {}).items():
            self._knowledge_id(state, key)
            state["knowledgeNotes"][key] = text(note, "知识点笔记", 30000)
        state["knowledgeFavorites"] = list(dict.fromkeys(self._knowledge_id(state, key) for key in value.get("knowledgeFavorites", [])))
        seen = {event["eventId"] for event in state["events"]}
        for event in value.get("knowledgeEvents", []):
            if not isinstance(event, dict) or not isinstance(event.get("eventId"), str) or not 1 <= len(event["eventId"]) <= 100 or event["eventId"] in seen:
                raise ValueError("学习记录标识无效或重复")
            seen.add(event["eventId"])
            self._knowledge_id(state, event.get("itemId"))
            self._day(event.get("day"))
            if event.get("rating") not in ("again", "hard", "good", "easy") or event.get("kind") not in ("new", "review"):
                raise ValueError("学习记录无效")
            if type(event.get("seconds")) is not int or not 0 <= event["seconds"] <= 14400:
                raise ValueError("学习时长无效")
            parse_time(event.get("time"))
            state["knowledgeEvents"].append({field: event[field] for field in ("eventId", "itemId", "day", "rating", "kind", "seconds", "time")})

    @staticmethod
    def _knowledge_id(state, item_id):
        if not isinstance(item_id, str) or item_id not in state["knowledge"]:
            raise ValueError("知识点不存在")
        return item_id

    def _knowledge_action(self, state, payload):
        kind = payload["type"]
        now = utc_now()
        timestamp = now.isoformat()
        if kind == "knowledge-import":
            import_into(state, payload.get("document"), timestamp)
        elif kind == "deck-save":
            fields = deck_fields(payload.get("deck"))
            deck_id = fields.get("id") or "deck-" + uuid4().hex
            old = state["decks"].get(deck_id)
            if not old and len(state["decks"]) >= 500:
                raise ValueError("知识库数量已达 500 个上限")
            state["decks"][deck_id] = {**fields, "id": deck_id, "createdAt": old["createdAt"] if old else timestamp, "updatedAt": timestamp}
        elif kind == "knowledge-save":
            item = payload.get("item")
            fields = item_fields(item)
            deck_id = item.get("deckId")
            if not isinstance(deck_id, str) or deck_id not in state["decks"]:
                raise ValueError("请选择已存在的知识库")
            item_id = fields.get("id") or "item-" + uuid4().hex
            old = state["knowledge"].get(item_id)
            if not old and len(state["knowledge"]) >= 10000:
                raise ValueError("知识点数量已达 10000 个上限")
            state["knowledge"][item_id] = {**fields, "id": item_id, "deckId": deck_id, "archived": old["archived"] if old else False,
                                          "createdAt": old["createdAt"] if old else timestamp, "updatedAt": timestamp}
        elif kind in ("knowledge-archive", "knowledge-note", "knowledge-favorite", "knowledge-rate"):
            item_id = self._knowledge_id(state, payload.get("itemId"))
            if kind == "knowledge-archive":
                if type(payload.get("archived")) is not bool:
                    raise ValueError("归档状态必须为布尔值")
                state["knowledge"][item_id]["archived"] = payload["archived"]
                state["knowledge"][item_id]["updatedAt"] = timestamp
            elif kind == "knowledge-note":
                state["knowledgeNotes"][item_id] = text(payload.get("text"), "笔记", 30000)
            elif kind == "knowledge-favorite":
                favorites = state["knowledgeFavorites"]
                favorites.remove(item_id) if item_id in favorites else favorites.append(item_id)
            else:
                event_id, rating = payload.get("eventId"), payload.get("rating")
                if not isinstance(event_id, str) or not 1 <= len(event_id) <= 100:
                    raise ValueError("学习记录标识无效")
                if not isinstance(rating, str) or rating not in RATINGS:
                    raise ValueError("请选择有效的记忆反馈")
                existing = next((event for event in state["knowledgeEvents"] + state["events"] if event["eventId"] == event_id), None)
                if existing:
                    if existing.get("itemId") != item_id or existing["rating"] != rating:
                        raise ValueError("学习记录标识已被其他操作使用，请刷新后重试")
                    return
                if state["knowledge"][item_id]["archived"]:
                    raise ValueError("请先恢复此知识点，再提交复习反馈")
                seconds = payload.get("seconds", 0)
                if type(seconds) is not int or not 0 <= seconds <= 14400:
                    raise ValueError("学习时长必须为 0–14400 的整数秒")
                day = self.local_day(payload.get("day"), now)
                old = state["knowledgeCards"].get(item_id)
                state["knowledgeCards"][item_id] = schedule(old, rating, state["settings"]["retention"], now)
                state["knowledgeEvents"].append({"eventId": event_id, "itemId": item_id, "day": day, "rating": rating,
                                                 "kind": "review" if old else "new", "time": timestamp, "seconds": seconds})
        else:
            raise ValueError("不支持的知识库操作")

    def _backup(self, state, prefix="before-import"):
        stem = prefix + "-" + utc_now().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex[:8]
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
            if kind in ("rate", "favorite", "note", "draft", "solution", "solution-reset"):
                pid = self._id(payload.get("problemId"))
            if kind == "rate":
                event_id = payload.get("eventId")
                if not isinstance(event_id, str) or not 1 <= len(event_id) <= 100:
                    raise ValueError("学习记录标识无效")
                rating = payload.get("rating")
                if not isinstance(rating, str) or rating not in RATINGS:
                    raise ValueError("请选择有效的记忆反馈")
                existing = next((event for event in state["events"] + state["knowledgeEvents"] if event["eventId"] == event_id), None)
                if existing:
                    if existing.get("problemId") != int(pid) or existing["rating"] != rating:
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
            elif kind == "checkin":
                if "day" in payload:
                    raise ValueError("签到只记录本机今日日期，请勿指定日期")
                day = self.local_day(None, utc_now())
                if day not in state["checkins"]:
                    state["checkins"].append(day)
                    state["checkins"].sort()
            elif kind == "checkin-makeup":
                make_up_checkin(state, payload, utc_now())
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
            elif kind in ("solution", "solution-reset"):
                key = self._solution_key(f"{pid}:{payload.get('language')}:{payload.get('mode')}")
                if kind == "solution-reset":
                    state["solutions"].pop(key, None)
                else:
                    state["solutions"][key] = self._solution(payload.get("solution"), utc_now().isoformat())
            elif isinstance(kind, str) and (kind.startswith("knowledge-") or kind == "deck-save"):
                self._knowledge_action(state, payload)
            elif kind == "settings":
                updates = payload.get("settings")
                if not isinstance(updates, dict):
                    raise ValueError("设置格式错误")
                state["settings"] = self.settings({**state["settings"], **updates})
                self._validate_study_decks(state)
            elif kind == "import":
                replacement = self.validate_import(payload.get("state"))
                self._backup(state)
                state = replacement
            else:
                raise ValueError("不支持的操作")
            state["stones"] = calculate_stones(state, utc_now())
            serialized = json.dumps(state, ensure_ascii=False, allow_nan=False)
            if len(serialized.encode("utf-8")) > MAX_STATE_BYTES:
                raise ValueError("学习资料已达 64 MB 上限，请精简较长的笔记或题解后再保存")
            db.execute("UPDATE state SET data=? WHERE id=1", (serialized,))
            return state
