import unittest

from server.json_support import MAX_JSON_DEPTH, validate_json_depth


class JsonDepthTests(unittest.TestCase):
    def test_depth_boundary_and_wide_documents(self):
        value = "笔记 [不是 JSON 结构]"
        for _ in range(MAX_JSON_DEPTH):
            value = [value]
        self.assertIs(validate_json_depth(value), value)
        with self.assertRaises(ValueError):
            validate_json_depth({"one_more_level": value})
        wide = [{"title": "卡片", "tags": ["学习"]} for _ in range(10000)]
        self.assertIs(validate_json_depth(wide), wide)

    def test_cycles_are_rejected_without_recursion(self):
        cycle = []
        cycle.append(cycle)
        with self.assertRaises(ValueError):
            validate_json_depth(cycle)
