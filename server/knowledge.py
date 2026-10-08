"""Validated, portable knowledge documents shared by manual and AI imports."""
import hashlib
import json
import re

FORMAT = "coderecall.knowledge"
KINDS = ("qa", "cloze", "procedure")
MAX_ITEMS = 1000
MAX_TEXT = 100000
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}\Z")


def text(value, label, limit, required=False, preserve_whitespace=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError(f"{label}必须为{'非空' if required else ''}文本，最多 {limit} 字")
    if "\x00" in value:
        raise ValueError(f"{label}不能包含空字符")
    return value.strip() if required and not preserve_whitespace else value


def identifier(value, label="标识"):
    if not isinstance(value, str) or ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label}需为 1–100 位字母、数字、下划线、点、冒号或短横线，以字母或数字开头")
    return value


def deck_fields(value):
    if not isinstance(value, dict):
        raise ValueError("知识库格式错误")
    result = {"title": text(value.get("title"), "知识库名称", 200, True),
              "description": text(value.get("description", ""), "知识库描述", 5000)}
    if "id" in value:
        result["id"] = identifier(value["id"], "知识库 ID")
    return result


def item_fields(value):
    if not isinstance(value, dict):
        raise ValueError("知识点格式错误")
    if value.get("kind") not in KINDS:
        raise ValueError("知识点类型必须为 qa、cloze 或 procedure")
    tags = value.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 30:
        raise ValueError("标签必须为数组，最多 30 个")
    result = {
        "title": text(value.get("title"), "知识点标题", 300, True),
        "kind": value["kind"],
        "prompt": text(value.get("prompt"), "知识点问题", MAX_TEXT, True, True),
        "answer": text(value.get("answer"), "知识点答案", MAX_TEXT, True, True),
        "tags": list(dict.fromkeys(text(tag, "标签", 60, True) for tag in tags)),
        "source": text(value.get("source", ""), "来源", 2000),
    }
    if result["kind"] == "cloze" and re.search(r"\{\{c[1-9]\d*::[^{}\n]+\}\}", result["prompt"]) is None:
        raise ValueError("填空题的问题中至少需要一个 {{c1::答案}} 标记")
    if "id" in value:
        result["id"] = identifier(value["id"], "知识点 ID")
    return result


def validate_document(value):
    if not isinstance(value, dict) or value.get("format") != FORMAT or type(value.get("version")) is not int or value["version"] != 1:
        raise ValueError("知识库文件需使用 coderecall.knowledge 格式，version 为 1")
    if set(value) - {"format", "version", "deck", "items"}:
        raise ValueError("知识库文件包含不支持的顶层字段")
    deck = deck_fields(value.get("deck"))
    if set(value["deck"]) - {"id", "title", "description"}:
        raise ValueError("知识库包含不支持的字段")
    items = value.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise ValueError(f"每次导入必须包含 1–{MAX_ITEMS} 个知识点")
    clean_items = []
    seen = set()
    for item in items:
        clean = item_fields(item)
        if set(item) - {"id", "title", "kind", "prompt", "answer", "tags", "source"}:
            raise ValueError("知识点包含不支持的字段")
        if "id" in clean:
            if clean["id"] in seen:
                raise ValueError("导入文件含重复知识点 ID")
            seen.add(clean["id"])
        clean_items.append(clean)
    result = {"format": FORMAT, "version": 1, "deck": deck, "items": clean_items}
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 8 * 1024 * 1024:
        raise ValueError("知识库文件最多 8 MB，请分批导入")
    return result


def stable_id(prefix, value):
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return prefix + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def import_into(state, document, now):
    """Mutate a transaction-local state only; all conflicts fail the whole batch."""
    document = validate_document(document)
    fields = document["deck"]
    deck_id = fields.get("id") or stable_id("deck-", {"title": fields["title"], "description": fields["description"]})
    existing = state["decks"].get(deck_id)
    if existing and any(existing[field] != fields[field] for field in ("title", "description")):
        raise ValueError(f"知识库 ID {deck_id} 已存在且内容不同，请先编辑知识库或使用新的 ID")
    if not existing:
        if len(state["decks"]) >= 500:
            raise ValueError("知识库数量已达 500 个上限")
        state["decks"][deck_id] = {**fields, "id": deck_id, "createdAt": now, "updatedAt": now}
    for fields in document["items"]:
        item_id = fields.get("id") or stable_id("item-", {"deckId": deck_id, **fields})
        proposed = {**fields, "id": item_id, "deckId": deck_id}
        existing = state["knowledge"].get(item_id)
        if existing:
            if any(existing.get(field) != proposed[field] for field in proposed):
                raise ValueError(f"知识点 ID {item_id} 已存在且内容不同，请使用编辑功能或新的 ID")
            continue
        if len(state["knowledge"]) >= 10000:
            raise ValueError("知识点数量已达 10000 个上限")
        state["knowledge"][item_id] = {**proposed, "archived": False, "createdAt": now, "updatedAt": now}
    return deck_id
