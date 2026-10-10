"""Exercise executable programs and regressions in the local judge contract."""
import ast
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import sys
import tempfile
import tokenize
import unittest
from unittest.mock import Mock, patch

from server.adapters import brief, enrich, format_input, program
from server.catalog import BY_ID, PROBLEMS
from server.runner import OUTPUT_LIMIT, compiler, execute, matches, run, same_value, stop_process


class SolutionContractTests(unittest.TestCase):
    def test_every_python_reference_variant_runs_all_examples(self):
        self.assertEqual(len(PROBLEMS), 100)
        self.assertEqual(len({problem["id"] for problem in PROBLEMS}), 100)
        jobs = []
        for problem in PROBLEMS:
            for field in ("summary", "constraints", "examples", "approach", "steps", "correctness", "pitfalls", "time", "space"):
                self.assertTrue(problem[field], (problem["id"], field))
            self.assertGreaterEqual(len(problem["examples"]), 2)
            detail = enrich(problem)
            for mode in ("leetcode", "acm"):
                for style in ("brief", "annotated"):
                    jobs.append((problem, mode, style, detail["solutions"]["python"][mode][style]))

        def check(job):
            problem, mode, style, source = job
            result = run(problem, {"language": "python", "mode": mode, "code": source})
            return problem["id"], mode, style, result

        # The public runner permits two jobs at once; exercise that real boundary.
        with ThreadPoolExecutor(max_workers=2) as pool:
            for problem_id, mode, style, result in pool.map(check, jobs):
                with self.subTest(problem=problem_id, mode=mode, style=style):
                    self.assertEqual(result["status"], "passed", result)

    def test_simple_acm_program_is_standalone_without_unrelated_nodes(self):
        source = program(BY_ID[1], "python", BY_ID[1]["python"])
        self.assertLess(len(source.splitlines()), 45)
        for unused in ("class TreeNode", "class ListNode", "class Node", "def read_argument", "import heapq"):
            self.assertNotIn(unused, source)
        # Future imports are legal in user code and must remain at the top.
        result = run(BY_ID[1], {"code": "from __future__ import annotations\n" + BY_ID[1]["python"]})
        self.assertEqual(result["status"], "passed", result)

    def test_templates_are_executable_scaffolds_in_both_languages(self):
        for problem in PROBLEMS:
            detail = enrich(problem)
            ast.parse(detail["templates"]["python"]["acm"])
            self.assertIn("int main()", detail["templates"]["cpp"]["acm"])
            self.assertIn("#include <stdexcept>", detail["templates"]["cpp"]["acm"])

    def test_invalid_node_identity_and_shallow_copy_are_rejected(self):
        cases = [
            (138, "class Solution:\n    def copyRandomList(self, head):\n        return head\n"),
            (160, "class Solution:\n    def getIntersectionNode(self, headA, headB):\n        return ListNode(8)\n"),
            (142, "class Solution:\n    def detectCycle(self, head):\n        return ListNode(0)\n"),
            (236, "class Solution:\n    def lowestCommonAncestor(self, root, p, q):\n        return TreeNode(3)\n"),
        ]
        for problem_id, source in cases:
            with self.subTest(problem=problem_id):
                result = run(BY_ID[problem_id], {"code": source})
                self.assertEqual(result["status"], "failed")
                self.assertTrue(result["cases"][0]["error"])

    def test_returning_a_cycle_cannot_pass_by_truncated_values(self):
        problem = dict(BY_ID[206], examples=[{"input": [[1]], "output": [1]}])
        source = "class Solution:\n    def reverseList(self, head):\n        head.next = head\n        return head\n"
        result = run(problem, {"code": source})
        self.assertEqual(result["status"], "failed")
        self.assertIn("环", result["cases"][0]["stderr"])

    def test_no_intersection_and_empty_structures(self):
        for problem_id, arguments, expected in ((160, [[], [], -1, -1], None),
                                                (142, [[], -1], -1), (138, [[]], [])):
            problem = dict(BY_ID[problem_id], examples=[{"input": arguments, "output": expected}])
            result = run(problem, {"code": problem["python"]})
            self.assertEqual(result["status"], "passed", result)

    def test_custom_input_executes_without_claiming_correctness(self):
        result = run(BY_ID[1], {"code": "print([999])", "mode": "acm", "stdin": ""})
        self.assertEqual(result["status"], "executed")
        self.assertIsNone(result["cases"][0]["passed"])
        self.assertEqual(result["cases"][0]["actual"], [999])

    def test_runtime_syntax_and_debug_output_errors_are_visible(self):
        for source, detail in (("raise ValueError('specific failure')", "specific failure"),
                               ("def broken(:\n    pass", "SyntaxError")):
            result = run(BY_ID[1], {"code": source, "mode": "acm", "stdin": ""})
            self.assertEqual(result["status"], "failed")
            self.assertIn(detail, result["cases"][0]["stderr"])
        result = run(BY_ID[1], {"code": "print('debug'); print([0, 1])", "mode": "acm", "stdin": ""})
        self.assertEqual(result["status"], "failed")
        self.assertIn("JSON", result["cases"][0]["error"])

    def test_python_unicode_output_and_diagnostics_remain_readable(self):
        result = run(BY_ID[1], {"code": "print('\\\"中文结果\\\"')", "mode": "acm", "stdin": ""})
        self.assertEqual(result["cases"][0]["actual"], "中文结果")
        result = run(BY_ID[1], {"code": "raise ValueError('请检查输入')", "mode": "acm", "stdin": ""})
        self.assertIn("请检查输入", result["cases"][0]["stderr"])

    @unittest.skipUnless(compiler(), "C++ compiler is unavailable")
    def test_cpp_and_python_share_json_string_escaping(self):
        problem = dict(BY_ID[3], method="echo", returns="string", examples=[
            {"input": [value], "output": value}
            for value in ('n\n\t\r\b\f\0', 'a"b\\c', '中文🙂', '')])
        sources = {
            "python": "class Solution:\n    def echo(self, s):\n        return s\n",
            "cpp": "class Solution { public: string echo(string s) { return s; } };",
        }
        for language, source in sources.items():
            with self.subTest(language=language):
                result = run(problem, {"language": language, "code": source})
                self.assertEqual(result["status"], "passed", result)
                escaped = json.dumps("中文🙂", ensure_ascii=True) + "\n"
                result = run(problem, {"language": language, "code": source, "stdin": escaped})
                self.assertEqual(result["cases"][0].get("actual"), "中文🙂", result)
        problem = dict(BY_ID[3], examples=[{"input": ['n\n'], "output": 2}])
        result = run(problem, {"language": "cpp", "code": problem["cpp"]})
        self.assertEqual(result["status"], "passed", result)

    def test_invalid_user_code_and_missing_compiler_have_clear_responses(self):
        for payload in ({"code": ""}, {"code": "pass", "language": "javascript"}, {"code": "pass", "stdin": 5}):
            with self.assertRaises(ValueError):
                run(BY_ID[1], payload)
        with patch("server.runner.compiler", return_value=None):
            result = run(BY_ID[1], {"code": "class Solution {};", "language": "cpp"})
        self.assertEqual(result["status"], "unavailable")


class ComparisonTests(unittest.TestCase):
    def test_recursive_numbers_keep_integer_answers_exact(self):
        self.assertTrue(same_value([None, 2, -1], [None, 2.0, -1.0]))
        self.assertTrue(same_value({"value": [0.30000000001]}, {"value": [0.3]}))
        self.assertFalse(same_value(1000000001, 1000000000))
        self.assertFalse(same_value([True], [1]))
        self.assertFalse(same_value([1, 2], [1]))

    def test_unordered_comparison_respects_inner_order_and_multiplicity(self):
        self.assertTrue(matches(BY_ID[46], [[2, 1], [1, 2]], [[1, 2], [2, 1]], [[1, 2]]))
        self.assertFalse(matches(BY_ID[46], [[1, 2], [1, 2]], [[1, 2], [2, 1]], [[1, 2]]))
        self.assertTrue(matches(BY_ID[49], [["tea", "eat"], ["bat"]], [["bat"], ["eat", "tea"]], []))
        self.assertFalse(matches(BY_ID[49], [["eat", "tea", "tea"], ["bat"]], [["bat"], ["eat", "tea"]], []))

    def test_two_sum_rejects_same_index_and_accepts_either_index_order(self):
        self.assertTrue(matches(BY_ID[1], [1, 0], [0, 1], [[3, 3], 6]))
        self.assertFalse(matches(BY_ID[1], [0, 0], [0, 1], [[3, 3], 6]))
        self.assertFalse(matches(BY_ID[1], [False, 1], [0, 1], [[3, 3], 6]))

    def test_bst_judge_accepts_distinct_shapes_but_rejects_unreachable_nodes(self):
        problem = BY_ID[108]
        self.assertTrue(matches(problem, [2, 1, 3], None, [[1, 2, 3]]))
        self.assertTrue(matches(problem, [2, 1], None, [[1, 2]]))
        self.assertTrue(matches(problem, [1, None, 2], None, [[1, 2]]))
        self.assertFalse(matches(problem, [1, None, None, 99], None, [[1]]))
        self.assertFalse(matches(problem, [1, None, 2, None, 3], None, [[1, 2, 3]]))
        self.assertFalse(matches(problem, [True], None, [[1]]))


class CommentTests(unittest.TestCase):
    def test_python_comments_are_removed_without_touching_strings(self):
        source = '''# leading comment
value = "# keep this"  # trailing comment
url = "https://example.test/#fragment"
text = """A docstring-like value # keep"""
'''
        concise = brief(source, "python")
        self.assertNotIn("trailing comment", concise)
        self.assertIn('"# keep this"', concise)
        self.assertIn("#fragment", concise)
        self.assertFalse(any(token.type == tokenize.COMMENT for token in tokenize.generate_tokens(io.StringIO(concise).readline)))
        original, simplified = {}, {}
        exec(source, original)
        exec(concise, simplified)
        for name in ("value", "url", "text"):
            self.assertEqual(original[name], simplified[name])

    def test_cpp_strings_characters_raw_literals_and_numeric_separators(self):
        source = '''#include <string>
const char* url = "https://example.test/*keep*/"; // remove A
const char* raw = R"tag(/* keep raw */ // still raw)tag"; /* remove B */
char quote = '\\''; // remove C
auto letter = L'a'; // remove wide comment
int count = 1'000; // remove D
int/**/value = 2;
// continued comment \\
this is also a comment
'''
        concise = brief(source, "cpp")
        self.assertIn("https://example.test/*keep*/", concise)
        self.assertIn('R"tag(/* keep raw */ // still raw)tag"', concise)
        self.assertIn("1'000", concise)
        self.assertIn("L'a'", concise)
        self.assertIn("int value", concise)
        self.assertIn("#include <string>", concise)
        self.assertNotIn("remove", concise)
        self.assertNotIn("this is also", concise)


class ProcessLimitTests(unittest.TestCase):
    def test_group_permission_error_is_ignored_only_after_child_exit(self):
        process = Mock(pid=12345)
        with patch("server.runner.os.name", "posix"), \
                patch("signal.SIGKILL", 9, create=True), \
                patch("server.runner.os.killpg", side_effect=PermissionError(), create=True):
            process.poll.return_value = 0
            stop_process(process)
            process.wait.assert_called_once_with(timeout=2)
            process.reset_mock()
            process.poll.return_value = None
            with self.assertRaises(PermissionError):
                stop_process(process)
            process.wait.assert_not_called()

    def execute_python(self, source, timeout=2):
        with tempfile.TemporaryDirectory() as directory:
            return execute([sys.executable, "-I", "-X", "utf8", "-c", source], "", directory, timeout)

    def test_timeout_terminates_a_non_finishing_program(self):
        result = self.execute_python("while True: pass", timeout=0.15)
        self.assertIn("超过", result["error"])
        self.assertNotEqual(result["exitCode"], 0)
        self.assertLess(result["elapsedMs"], 2500)

    def test_output_limit_catches_fast_exit_and_bounds_both_streams(self):
        source = f"import sys; sys.stdout.write('x' * {OUTPUT_LIMIT}); sys.stderr.write('y' * {OUTPUT_LIMIT})"
        result = self.execute_python(source)
        self.assertIn("输出超过", result["error"])
        self.assertLessEqual(len(result["stdout"].encode()) + len(result["stderr"].encode()), OUTPUT_LIMIT)

    def test_exit_code_and_stderr_survive(self):
        result = self.execute_python("import sys; print('out'); print('diagnostic', file=sys.stderr); sys.exit(7)")
        self.assertEqual(result["exitCode"], 7)
        self.assertEqual(result["stdout"], "out")
        self.assertEqual(result["stderr"], "diagnostic")

    def test_missing_executable_returns_a_readable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = execute([str(Path(directory) / "missing-executable")], "", directory, 1)
        self.assertEqual(result["exitCode"], -1)
        self.assertIn("无法启动", result["error"])


if __name__ == "__main__":
    unittest.main()
