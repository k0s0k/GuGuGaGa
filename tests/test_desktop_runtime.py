"""Desktop workers must use the portable runtimes, never restart the GUI exe."""
from contextlib import ExitStack
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from server import runtime
from server.adapters import enrich
from server.catalog import BY_ID
from server.runner import capabilities, run


def frozen_paths(stack, root, platform="win32"):
    stack.enter_context(patch.object(sys, "platform", platform))
    stack.enter_context(patch.object(sys, "frozen", True, create=True))
    stack.enter_context(patch.object(sys, "_MEIPASS", str(root / "_internal"), create=True))
    stack.enter_context(patch.object(sys, "executable", str(root / "CodeRecall.exe")))


class PortableRuntimeTests(unittest.TestCase):
    def tearDown(self):
        runtime._probe_python.cache_clear()
        runtime._macos_compiler.cache_clear()

    def test_frozen_app_and_resources_have_distinct_roots(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            frozen_paths(stack, root)
            self.assertEqual(runtime.app_dir(), root)
            self.assertEqual(runtime.resource_root(), root / "_internal")
            self.assertEqual(runtime.python_command(), [str(root / "_internal/runtime/python/python.exe"), "-I", "-X", "utf8"])
            self.assertNotEqual(runtime.python_command()[0], sys.executable)

    def test_missing_bundled_python_does_not_fall_back_to_gui(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            frozen_paths(stack, Path(directory))
            launch = stack.enter_context(patch("server.runtime.spawn_process"))
            self.assertEqual(capabilities()["python"], {"available": False, "version": None})
            result = run(BY_ID[1], {"code": "print([])", "mode": "acm"})
            self.assertEqual(result["status"], "unavailable")
            self.assertIn("_internal", result["message"])
            launch.assert_not_called()

    def test_frozen_macos_uses_independent_python_and_clears_gui_library_paths(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            frozen_paths(stack, root, platform="darwin")
            stack.enter_context(patch("server.runtime.compiler", return_value=None))
            stack.enter_context(patch.dict(os.environ, {
                "DYLD_LIBRARY_PATH": "frozen-libraries", "DYLD_FRAMEWORK_PATH": "frozen-frameworks",
                "DYLD_FALLBACK_LIBRARY_PATH": "frozen-fallback", "PYTHONPATH": "app-python",
            }))
            self.assertEqual(runtime.python_command(), [str(root / "_internal/runtime/python/bin/python3"), "-I", "-X", "utf8"])
            self.assertNotEqual(runtime.python_command()[0], sys.executable)
            environment = runtime.child_environment()
            for key in ("DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "PYTHONPATH"):
                self.assertNotIn(key, environment)
                self.assertIn(key, os.environ)

    def test_macos_missing_command_line_tools_never_invokes_compiler_stub(self):
        with patch.object(sys, "platform", "darwin"), patch.dict(os.environ, {"CODERECALL_CXX": ""}), \
                patch("server.runtime.subprocess.run", return_value=subprocess.CompletedProcess([], 2, "")) as probe:
            self.assertIsNone(runtime.compiler())
            self.assertIsNone(runtime.compiler())
            probe.assert_called_once()
            self.assertEqual(probe.call_args.args[0], ["/usr/bin/xcode-select", "-p"])
            result = run(BY_ID[1], {"language": "cpp", "code": "int main() {}", "mode": "acm"})
            self.assertEqual(result["status"], "unavailable")
            self.assertIn("xcode-select --install", result["message"])
            self.assertIn("xcode-select --install", capabilities()["cpp"]["setupHelp"])

    def test_macos_resolves_installed_clang_without_system_path(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            developer = root / "CommandLineTools"
            executable = developer / "usr/bin/clang++"
            executable.parent.mkdir(parents=True)
            executable.touch()
            stack.enter_context(patch.object(sys, "platform", "darwin"))
            stack.enter_context(patch.dict(os.environ, {"PATH": "", "CODERECALL_CXX": ""}))
            probe = stack.enter_context(patch("server.runtime.subprocess.run", side_effect=[
                subprocess.CompletedProcess([], 0, str(developer) + "\n"),
                subprocess.CompletedProcess([], 0, str(executable) + "\n"),
            ]))
            self.assertEqual(runtime.compiler(), str(executable))
            self.assertEqual(runtime.compiler(), str(executable))
            self.assertEqual(probe.call_count, 2)
            self.assertEqual(probe.call_args.args[0], ["/usr/bin/xcrun", "--find", "clang++"])

    def test_macos_python_error_describes_app_bundle(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            frozen_paths(stack, Path(directory), platform="darwin")
            stack.enter_context(patch("server.runtime.spawn_process"))
            result = run(BY_ID[1], {"language": "python", "code": "print([])", "mode": "acm"})
            self.assertEqual(result["status"], "unavailable")
            self.assertIn("GuGuGaGa.app", result["message"])
            self.assertNotIn(".exe", result["message"])

    def test_bundled_compiler_precedes_path_and_custom_precedes_bundle(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            frozen_paths(stack, root)
            bundled = root / "_internal/runtime/toolchains/w64devkit/bin/g++.exe"
            bundled.parent.mkdir(parents=True)
            bundled.touch()
            custom = root / "custom-g++.exe"
            custom.touch()
            stack.enter_context(patch.dict(os.environ, {"CODERECALL_CXX": ""}))
            stack.enter_context(patch("server.runtime.shutil.which", return_value="system-g++.exe"))
            self.assertEqual(runtime.compiler(), str(bundled))
            with patch.dict(os.environ, {"CODERECALL_CXX": str(custom)}):
                self.assertEqual(runtime.compiler(), str(custom))
            bundled.unlink()
            self.assertEqual(runtime.compiler(), "system-g++.exe")

    def test_child_environment_excludes_gui_libraries_and_includes_gcc_dlls(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            frozen_paths(stack, root)
            gcc = root / "_internal/runtime/toolchains/w64devkit/bin/g++.exe"
            stack.enter_context(patch("server.runtime.compiler", return_value=str(gcc)))
            system_path = str(root / "system-bin")
            stack.enter_context(patch.dict(os.environ, {
                "PATH": os.pathsep.join([str(root / "_internal"), str(root / "_internal/pythonnet"), system_path]),
                "PYTHONHOME": str(root / "_internal"), "PYTHONPATH": str(root / "_internal"),
                "LD_LIBRARY_PATH": "frozen-libs", "LD_LIBRARY_PATH_ORIG": "system-libs",
            }))
            environment = runtime.child_environment()
            self.assertEqual(environment["PATH"].split(os.pathsep), [str(gcc.parent), system_path])
            self.assertEqual(environment["LD_LIBRARY_PATH"], "system-libs")
            self.assertNotIn("PYTHONHOME", environment)
            self.assertNotIn("PYTHONPATH", environment)
            self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
            self.assertIn("PYTHONHOME", os.environ)  # Parent environment is unchanged.

    def test_python_version_is_probed_once_from_worker(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            frozen_paths(stack, root)
            executable = root / "_internal/runtime/python/python.exe"
            executable.parent.mkdir(parents=True)
            executable.touch()
            launch = stack.enter_context(patch("server.runtime.spawn_process"))
            launch.return_value.communicate.return_value = ("3.12.10\n", "")
            launch.return_value.returncode = 0
            expected = {"available": True, "version": "3.12.10"}
            self.assertEqual(runtime.python_capabilities(), expected)
            self.assertEqual(runtime.python_capabilities(), expected)
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0][:4], [str(executable), "-I", "-X", "utf8"])

    @unittest.skipUnless(os.name == "nt", "Windows DLL lookup behavior")
    def test_spawn_restores_parent_dll_directory_when_executable_is_missing(self):
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetDllDirectoryW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
        kernel32.GetDllDirectoryW.restype = ctypes.c_uint32
        kernel32.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel32.SetDllDirectoryW.restype = ctypes.c_int

        def get_directory():
            buffer = ctypes.create_unicode_buffer(32768)
            kernel32.GetDllDirectoryW(len(buffer), buffer)
            return buffer.value

        original = get_directory()
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            frozen_paths(stack, root)
            kernel32.SetDllDirectoryW(str(root))
            try:
                with self.assertRaises(OSError):
                    runtime.spawn_process([str(root / "does-not-exist.exe")])
                self.assertEqual(get_directory(), str(root))
            finally:
                kernel32.SetDllDirectoryW(original or None)

    def test_development_worker_runs_python_without_changing_modes(self):
        self.assertEqual(runtime.python_command()[0], sys.executable)
        problem = BY_ID[1]
        detail = enrich(problem)
        for mode in ("leetcode", "acm"):
            with self.subTest(mode=mode):
                result = run(problem, {"language": "python", "mode": mode, "code": detail["solutions"]["python"][mode]["brief"]})
                self.assertEqual(result["status"], "passed", result)


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_EMBEDDED_PYTHON = _PROJECT_ROOT / ".local/desktop-python"
_BUNDLED_GCC = _PROJECT_ROOT / ".local/toolchains/w64devkit/bin/g++.exe"


@unittest.skipUnless((_EMBEDDED_PYTHON / "python.exe").is_file() and _BUNDLED_GCC.is_file(), "Portable build dependencies have not been downloaded")
class EmbeddedWorkerTests(unittest.TestCase):
    def test_frozen_workers_execute_both_languages_and_modes_without_system_path(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            shutil.copytree(_EMBEDDED_PYTHON, root / "_internal/runtime/python")
            frozen_paths(stack, root)
            # No Python or compiler is discoverable from PATH in this test.
            stack.enter_context(patch.dict(os.environ, {"PATH": "", "CODERECALL_CXX": str(_BUNDLED_GCC)}))
            python = runtime.python_capabilities()
            self.assertTrue(python["available"], python)
            self.assertNotEqual(runtime.python_command()[0], sys.executable)
            problem = BY_ID[1]
            detail = enrich(problem)
            for language in ("python", "cpp"):
                for mode in ("leetcode", "acm"):
                    with self.subTest(language=language, mode=mode):
                        result = run(problem, {"language": language, "mode": mode, "code": detail["solutions"][language][mode]["brief"]})
                        self.assertEqual(result["status"], "passed", result)
            result = run(problem, {"language": "python", "mode": "acm", "code": "print('\\\"中文桌面版\\\"')", "stdin": ""})
            self.assertEqual(result["cases"][0]["actual"], "中文桌面版")
        runtime._probe_python.cache_clear()


if __name__ == "__main__":
    unittest.main()
