"""Keep input nesting limits consistent across Python versions and platforms."""

MAX_JSON_DEPTH = 64


def validate_json_depth(value):
    # Iterators keep auxiliary memory proportional to depth, not document size.
    stack = [iter((value,))]
    while stack:
        try:
            item = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if isinstance(item, (dict, list, tuple)):
            if len(stack) > MAX_JSON_DEPTH:
                raise ValueError("JSON 嵌套过深，请使用规定的导入结构")
            stack.append(iter(item.values() if isinstance(item, dict) else item))
    return value
