"""Execute user-authored code locally, with time and output limits.

This is a local development runner, not a security sandbox for untrusted code.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from .adapters import program, format_input
from .runtime import compiler, compiler_flags, compiler_help, python_capabilities, python_command, python_runtime_help, spawn_process

RUN_LOCK = threading.Semaphore(2)
OUTPUT_LIMIT = 128 * 1024


def capabilities():
    cxx = compiler()
    return {"python": python_capabilities(), "cpp": {"available": bool(cxx), "compiler": Path(cxx).name if cxx else None,
            "setupHelp": None if cxx else compiler_help()}, "localExecution": True}


def stop_process(process):
    if os.name == "nt":
        killer = spawn_process(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        killer.wait(timeout=5)
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # A fast-exiting child may disappear between the output check and
            # group signalling. Ignore the error only after confirming exit.
            if process.poll() is None:
                raise
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def execute(command, stdin, directory, timeout):
    started = time.perf_counter()
    with tempfile.TemporaryFile() as input_file, tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        input_file.write(stdin.encode("utf-8"))
        input_file.seek(0)
        try:
            process = spawn_process(command, cwd=directory, stdin=input_file, stdout=output, stderr=errors)
        except OSError as exc:
            return {"stdout": "", "stderr": str(exc), "exitCode": -1,
                    "elapsedMs": round((time.perf_counter() - started) * 1000),
                    "error": "无法启动程序，请检查本地解释器或编译器配置。"}
        failure = None
        while process.poll() is None:
            if time.perf_counter() - started > timeout:
                failure = f"运行超过 {timeout} 秒，已停止进程。"
                stop_process(process)
                break
            if os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > OUTPUT_LIMIT:
                failure = "输出超过 128 KB，已停止进程。"
                stop_process(process)
                break
            time.sleep(0.025)
        # A short-lived process can exceed the limit and exit between two polls.
        if not failure and os.fstat(output.fileno()).st_size + os.fstat(errors.fileno()).st_size > OUTPUT_LIMIT:
            failure = "输出超过 128 KB，结果已截断。"
        output.seek(0)
        errors.seek(0)
        stdout = output.read(OUTPUT_LIMIT)
        stderr = errors.read(max(0, OUTPUT_LIMIT - len(stdout)))
        return {"stdout": stdout.decode("utf-8", errors="replace").strip(), "stderr": stderr.decode("utf-8", errors="replace").strip(), "exitCode": process.returncode, "elapsedMs": round((time.perf_counter() - started) * 1000), "error": failure}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def same_value(actual, expected):
    """Compare JSON recursively; only expected floating results use tolerance."""
    if type(expected) is int:
        return type(actual) in (int, float) and actual == expected
    if type(expected) is float:
        return type(actual) in (int, float) and math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-7)
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(same_value(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(same_value(actual[key], expected[key]) for key in expected)
    return type(actual) is type(expected) and actual == expected


def matches(problem, actual, expected, args):
    if problem["id"] == 1:
        return isinstance(actual, list) and len(actual) == 2 and all(type(i) is int and 0 <= i < len(args[0]) for i in actual) and actual[0] != actual[1] and args[0][actual[0]] + args[0][actual[1]] == args[1]
    compare = problem.get("compare")
    if compare == "unordered":
        return isinstance(actual, list) and sorted(map(canonical, actual)) == sorted(map(canonical, expected))
    if compare == "groups":
        def groups(values):
            return sorted(canonical(sorted(group, key=canonical)) for group in values)
        return isinstance(actual, list) and all(isinstance(row, list) for row in actual) and groups(actual) == groups(expected)
    if compare == "palindrome":
        return isinstance(actual, str) and actual == actual[::-1] and actual in args[0] and len(actual) == len(expected)
    if compare == "bst":
        if not isinstance(actual, list) or any(value is not None and type(value) is not int for value in actual):
            return False
        if not actual or actual[0] is None:
            return not args[0] and not any(value is not None for value in actual)
        nodes = [[actual[0], None, None]]
        cursor = 1
        for node in nodes:
            for side in (1, 2):
                if cursor < len(actual):
                    if actual[cursor] is not None:
                        node[side] = len(nodes)
                        nodes.append([actual[cursor], None, None])
                    cursor += 1
        if any(value is not None for value in actual[cursor:]):
            return False  # Values after an exhausted parent queue have no valid position.
        heights = [0] * len(nodes)
        for index in range(len(nodes) - 1, -1, -1):
            _, left, right = nodes[index]
            lh = heights[left] if left is not None else 0
            rh = heights[right] if right is not None else 0
            if abs(lh - rh) > 1:
                return False
            heights[index] = max(lh, rh) + 1
        values, stack, index = [], [], 0
        while index is not None or stack:
            while index is not None:
                stack.append(index)
                index = nodes[index][1]
            index = stack.pop()
            values.append(nodes[index][0])
            index = nodes[index][2]
        return values == args[0]
    return same_value(actual, expected)


def run(problem, payload):
    language = payload.get("language", "python")
    mode = payload.get("mode", "leetcode")
    code = payload.get("code")
    if language not in ("python", "cpp") or mode not in ("leetcode", "acm"):
        raise ValueError("语言或模式不支持")
    if not isinstance(code, str) or not code.strip() or len(code) > 100000:
        raise ValueError("请填写代码（最多 100 KB）")
    if language == "cpp" and not compiler():
        return {"status": "unavailable", "message": compiler_help(), "cases": []}
    if language == "python" and not python_capabilities()["available"]:
        return {"status": "unavailable", "message": python_runtime_help(), "cases": []}
    custom = payload.get("stdin")
    if custom is not None and (not isinstance(custom, str) or len(custom) > 20000):
        raise ValueError("自定义输入最多 20 KB")
    if not RUN_LOCK.acquire(blocking=False):
        return {"status": "busy", "message": "已有两个程序正在运行，请稍后重试。", "cases": []}
    try:
        with tempfile.TemporaryDirectory(prefix="coderecall-") as directory:
            path = Path(directory)
            source = program(problem, language, code) if mode == "leetcode" else code
            if language == "python":
                filename = path / "main.py"
                filename.write_text(source, encoding="utf-8")
                command = [*python_command(), str(filename)]
            else:
                filename = path / "main.cpp"
                filename.write_text(source, encoding="utf-8")
                binary = path / ("main.exe" if os.name == "nt" else "main")
                cxx = compiler()
                compiled = execute([cxx, *compiler_flags(cxx), "-std=c++17", "-O2", str(filename), "-o", str(binary)], "", directory, 30)
                if compiled["exitCode"] != 0 or compiled["error"]:
                    return {"status": "compile_error", "message": compiled["error"] or compiled["stderr"], "cases": []}
                command = [str(binary)]
            cases = [{"stdin": custom}] if custom is not None else [{**example, "stdin": format_input(problem, example["input"])} for example in problem["examples"]]
            results = []
            for example in cases:
                result = execute(command, example["stdin"], directory, 4)
                result["input"] = example["stdin"]
                result["expected"] = example.get("output")
                result["passed"] = None
                if result["exitCode"] == 0 and not result["error"]:
                    try:
                        actual = json.loads(result["stdout"])
                        result["actual"] = actual
                        if custom is None:
                            result["passed"] = matches(problem, actual, example["output"], example["input"])
                    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
                        result["error"] = "输出格式无效：请只输出一行 JSON 结果，移除调试打印。"
                elif not result["error"]:
                    result["error"] = "程序运行出错"
                results.append(result)
            success = all(not r["error"] and r["exitCode"] == 0 and r["passed"] is not False for r in results)
            return {"status": ("executed" if custom is not None else "passed") if success else "failed", "message": ("自定义输入运行完成（未判定正确性）" if custom is not None else f"通过 {sum(r['passed'] is True for r in results)} / {len(results)} 个本地样例") if success else "请检查输出、错误信息和边界条件", "cases": results}
    finally:
        RUN_LOCK.release()
