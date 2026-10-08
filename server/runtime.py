"""Locate the portable desktop payload and launch its independent code workers."""
from contextlib import contextmanager
import ctypes
from functools import lru_cache
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading


_SPAWN_LOCK = threading.Lock()


def resource_root():
    """Directory containing packaged assets (separate from writable app data)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return resource_root()


def python_command():
    # In a frozen app sys.executable is CodeRecall.exe, NOT a Python interpreter.
    executable = resource_root() / "runtime/python/python.exe" if getattr(sys, "frozen", False) else Path(sys.executable)
    # Isolated mode ignores PYTHONIOENCODING, so also select UTF-8 explicitly.
    return [str(executable), "-I", "-X", "utf8"]


def compiler():
    custom = os.environ.get("CODERECALL_CXX")
    if custom and Path(custom).is_file():
        return str(Path(custom).resolve())
    candidates = [resource_root() / "runtime/toolchains/w64devkit/bin/g++.exe",
                  app_dir() / ".local/toolchains/w64devkit/bin/g++.exe"]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("g++") or shutil.which("clang++")


def child_environment():
    environment = dict(os.environ)
    if getattr(sys, "frozen", False):
        # PyInstaller changes the library search path for its own extension DLLs.
        # Workers have their own Python/GCC DLLs and must not load the app's copies.
        root = resource_root().resolve()
        environment["PATH"] = os.pathsep.join(
            entry for entry in environment.get("PATH", "").split(os.pathsep)
            if entry and not Path(entry).resolve().is_relative_to(root)
        )
        if "LD_LIBRARY_PATH_ORIG" in environment:
            environment["LD_LIBRARY_PATH"] = environment["LD_LIBRARY_PATH_ORIG"]
        else:
            environment.pop("LD_LIBRARY_PATH", None)
        environment.pop("PYTHONHOME", None)
        environment.pop("PYTHONPATH", None)
    # Compiled student programs also need the compiler's libstdc++/libgcc DLLs.
    cxx = compiler()
    if cxx:
        environment["PATH"] = str(Path(cxx).parent) + os.pathsep + environment.get("PATH", "")
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


@contextmanager
def external_dll_search_path():
    """Only clear PyInstaller's process-wide DLL directory while spawning.

    PyInstaller documents this Windows requirement under 'Launching External
    Programs'. A lock protects simultaneous launches from the two judge workers.
    The parent's original DLL directory is restored even when Popen fails.
    """
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    with _SPAWN_LOCK:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetDllDirectoryW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
        kernel32.GetDllDirectoryW.restype = ctypes.c_uint32
        kernel32.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel32.SetDllDirectoryW.restype = ctypes.c_int
        size = kernel32.GetDllDirectoryW(0, None)
        buffer = ctypes.create_unicode_buffer(size + 1)
        kernel32.GetDllDirectoryW(len(buffer), buffer)
        previous = buffer.value
        if not kernel32.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            if not kernel32.SetDllDirectoryW(previous or None):
                raise ctypes.WinError(ctypes.get_last_error())


def spawn_process(command, **kwargs):
    kwargs.setdefault("env", child_environment())
    if os.name == "nt":
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    else:
        kwargs.setdefault("start_new_session", True)
    with external_dll_search_path():
        return subprocess.Popen(command, **kwargs)


@lru_cache(maxsize=4)
def _probe_python(executable, modified):
    del modified  # Cache is invalidated when the interpreter is replaced.
    process = None
    try:
        process = spawn_process([executable, "-I", "-X", "utf8", "-c", "import platform; print(platform.python_version())"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8")
        stdout, _ = process.communicate(timeout=5)
        version = stdout.strip()
        if process.returncode == 0 and len(version.split(".")) == 3 and all(part.isdigit() for part in version.split(".")):
            return True, version
    except (OSError, subprocess.SubprocessError, UnicodeError):
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
    return False, None


def python_capabilities():
    executable = python_command()[0]
    try:
        modified = Path(executable).stat().st_mtime_ns
    except OSError:
        return {"available": False, "version": None}
    available, version = _probe_python(executable, modified)
    return {"available": available, "version": version}
