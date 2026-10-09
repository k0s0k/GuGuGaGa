"""GuGuGaGa Windows desktop entry point.

Run from source: python desktop.py
Frozen builds include an independent Python interpreter for submitted programs.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
import hashlib
import http.client
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import traceback
from urllib.parse import urlsplit
import webbrowser

from desktop_support import data_directory, migrate_legacy_database
from server.app import LocalHTTPServer, make_handler
from server.catalog import BY_ID, detail
from server.runner import capabilities, run
from server.ai_import import split_document
from server.runtime import app_dir, resource_root
from server.store import Store

APP_NAME = "GuGuGaGa"
# Keep the v2 activation protocol and data directory compatible with CodeRecall.
APP_ID = "CodeRecall.Desktop.2"
WINDOWS_APP_ID = "GuGuGaGa.Desktop"
VERSION = "2.2.1"
LOGGER = logging.getLogger("coderecall.desktop")


def configure_logging(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / "desktop.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    # --windowed has no console streams. Keep traceback/logging usable.
    if sys.stdout is None:
        sys.stdout = open(directory / "console.log", "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = sys.stdout


class InstanceMutex:
    """A per-user-data-directory Windows singleton with kernel-owned cleanup."""
    def __init__(self, directory: Path):
        self.handle = None
        self.is_owner = True
        if os.name != "nt":
            return
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        digest = hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()[:20]
        self.handle = self.kernel.CreateMutexW(None, False, "Local\\CodeRecall-" + digest)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.is_owner = ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def activate_existing(marker: Path, timeout=8.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            info = json.loads(marker.read_text(encoding="utf-8"))
            if (not isinstance(info, dict) or info.get("appId") != APP_ID
                    or type(info.get("port")) is not int or not 1 <= info["port"] <= 65535
                    or not isinstance(info.get("key"), str) or not info["key"].isascii()):
                return False
            connection = http.client.HTTPConnection("127.0.0.1", info["port"], timeout=1)
            try:
                connection.request("POST", "/api/desktop/activate", body=b"{}", headers={"Content-Type": "application/json", "X-CodeRecall-Desktop-Key": info["key"]})
                response = connection.getresponse()
                response.read()
                if response.status == 200:
                    return True
            finally:
                connection.close()
        except (OSError, ValueError, KeyError, http.client.HTTPException):
            pass
        time.sleep(0.15)
    return False


class DesktopService:
    def __init__(self, directory: Path, initial_port=8767):
        self.directory = directory
        self.key = secrets.token_urlsafe(32)
        self.on_activate = lambda: None
        self.store = Store(directory / "coderecall.db", BY_ID)
        self.server = None
        # A fixed preferred port retains browser drafts across restarts; fall back
        # to an OS-assigned free port without disturbing any other application.
        for port in dict.fromkeys((initial_port, 0)):
            try:
                self.server = LocalHTTPServer(("127.0.0.1", port), make_handler(self.store, port))
                break
            except OSError:
                if port == 0:
                    raise
        self.port = self.server.server_address[1]
        base_handler = make_handler(self.store, self.port)
        service = self

        class DesktopHandler(base_handler):
            def do_GET(self):
                if urlsplit(self.path).path == "/api/desktop/status":
                    if not self.trusted_host():
                        return self.send_json({"error": "Local access only"}, 403)
                    return self.send_json({"appId": APP_ID, "version": VERSION, "pid": os.getpid()})
                return super().do_GET()

            def do_POST(self):
                if urlsplit(self.path).path == "/api/desktop/activate":
                    supplied = self.headers.get("X-CodeRecall-Desktop-Key", "")
                    if not self.trusted_host() or not supplied.isascii() or not secrets.compare_digest(supplied, service.key):
                        return self.send_json({"error": "Invalid desktop session"}, 403)
                    service.on_activate()
                    return self.send_json({"activated": True})
                return super().do_POST()

        self.server.RequestHandlerClass = DesktopHandler
        self.thread = threading.Thread(target=self.server.serve_forever, name="coderecall-http", daemon=True)
        self.url = f"http://127.0.0.1:{self.port}"
        self.marker = directory / "instance.json"

    def start(self):
        self.thread.start()
        temporary = self.marker.with_suffix(".tmp")
        temporary.write_text(json.dumps({"appId": APP_ID, "version": VERSION, "pid": os.getpid(), "port": self.port, "key": self.key}), encoding="utf-8")
        temporary.replace(self.marker)
        LOGGER.info("Desktop service listening on %s", self.url)

    def stop(self):
        if self.thread.is_alive():
            self.server.shutdown()
            self.thread.join(timeout=3)
        self.server.server_close()
        try:
            current = json.loads(self.marker.read_text(encoding="utf-8"))
            if isinstance(current, dict) and current.get("pid") == os.getpid() and current.get("key") == self.key:
                self.marker.unlink()
        except (OSError, ValueError):
            pass


def native_window(service: DesktopService, directory: Path, smoke_report: Path | None = None):
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    window = webview.create_window(
        f"{APP_NAME} · 知识与复习", service.url,
        width=1320, height=900, min_size=(900, 640),
        background_color="#fbfbfa", hidden=smoke_report is not None,
    )
    service.on_activate = lambda: (window.restore(), window.show())
    outcome = {"passed": False, "renderer": "edgechromium", "version": VERSION}
    finished = threading.Event()

    def verify_page():
        # A developer-only smoke test of the real bundled WebView2 engine.
        # Normal launches never execute this verification or close themselves.
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and not finished.is_set():
            try:
                text = window.evaluate_js("document.body.innerText") or ""
                if "每日旅程" in text and "Hot 100" in text:
                    outcome.update(passed=True, title=window.evaluate_js("document.title"), hasDashboard=True)
                    break
            except Exception:
                pass
            time.sleep(0.15)
        finished.set()
        window.destroy()

    if smoke_report:
        window.events.loaded += lambda: threading.Thread(target=verify_page, daemon=True).start()

        def watchdog():
            if not finished.wait(timeout=40):
                outcome["error"] = "WebView2 page did not become ready within 40 seconds"
                finished.set()
                try:
                    window.destroy()
                except Exception:
                    LOGGER.exception("Could not close the smoke-test window")
        threading.Thread(target=watchdog, daemon=True).start()
    try:
        webview.start(gui="edgechromium", debug=False, private_mode=False,
                      storage_path=str(directory / "webview"),
                      icon=str(resource_root() / "packaging" / "GuGuGaGa.ico"))
    finally:
        finished.set()
        if smoke_report:
            smoke_report.parent.mkdir(parents=True, exist_ok=True)
            smoke_report.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
    if smoke_report and not outcome["passed"]:
        raise RuntimeError(outcome.get("error", "The desktop page did not load"))


def browser_fallback(service: DesktopService, directory: Path):
    """A usable fallback when Windows WebView2 is unavailable."""
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("440x270")
    root.resizable(False, False)
    root.configure(background="#f4f5f1")
    icon = resource_root() / "packaging" / "GuGuGaGa.ico"
    if icon.is_file():
        root.iconbitmap(str(icon))
    tk.Label(root, text=f"{APP_NAME} 正在运行", font=("Microsoft YaHei UI", 17, "bold"), background="#f4f5f1", foreground="#2e4234").pack(pady=(30, 15))
    tk.Label(root, text="当前使用浏览器打开工作台。\n关闭此窗口即可退出软件。", font=("Microsoft YaHei UI", 10), background="#f4f5f1", foreground="#667260", justify="center").pack(pady=7)
    ttk.Button(root, text="打开学习工作台", command=lambda: webbrowser.open(service.url)).pack(pady=13)
    tk.Label(root, text="独立窗口需要 Microsoft Edge WebView2 Runtime", font=("Microsoft YaHei UI", 8), background="#f4f5f1", foreground="#86917f").pack()
    root.after(100, lambda: webbrowser.open(service.url))
    def focus():
        root.after(0, lambda: (root.deiconify(), root.lift(), root.focus_force()))
    service.on_activate = focus
    root.mainloop()


def self_test(report_path: Path):
    """Verify real frozen resources, HTTP, storage, and both executable workers."""
    report = {"version": VERSION, "frozen": bool(getattr(sys, "frozen", False)), "passed": False, "checks": []}
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="coderecall-desktop-test-") as tmp:
            service = DesktopService(Path(tmp), initial_port=0)
            service.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", service.port, timeout=5)
                connection.request("GET", "/")
                response = connection.getresponse()
                html = response.read().decode("utf-8")
                assert response.status == 200 and "root" in html, "Packaged frontend missing"
                assert "GuGuGaGa" in html and "/gugugaga-icon.png" in html, "Packaged branding is outdated"
                report["checks"].append("packaged_frontend")
                connection.request("GET", "/gugugaga-icon.png")
                response = connection.getresponse()
                assert response.status == 200 and response.read().startswith(b"\x89PNG\r\n\x1a\n"), "Packaged icon is missing"
                assert (resource_root() / "packaging" / "GuGuGaGa.ico").is_file(), "Native icon is missing"
                report["checks"].append("application_branding_and_icon")
                connection.request("GET", "/api/bootstrap")
                response = connection.getresponse()
                payload = json.loads(response.read())
                assert response.status == 200 and len(payload["problems"]) == 100
                connection.close()
                report["checks"].append("http_hot100")
                report["capabilities"] = capabilities()
                for language in ("python", "cpp"):
                    for mode in ("leetcode", "acm"):
                        result = run(BY_ID[1], {"language": language, "mode": mode, "code": detail(1)["solutions"][language][mode]["brief"]})
                        assert result["status"] == "passed", f"{language}/{mode}: {result}"
                        report["checks"].append(f"{language}_{mode}")
                current = service.store.action({"type": "rate", "problemId": 1, "rating": "good", "day": datetime.now().date().isoformat(), "eventId": "desktop-self-test", "seconds": 1})
                assert current["cards"]["1"]["reviews"] == 1
                assert service.store.read()["events"][0]["eventId"] == "desktop-self-test"
                report["checks"].append("sqlite_persistence")
                solution = {"brief": "# my solution", "annotated": "# my annotated solution", "explanation": "## My explanation"}
                state = service.store.action({"type": "solution", "problemId": 1, "language": "python", "mode": "leetcode", "solution": solution})
                assert state["solutions"]["1:python:leetcode"]["explanation"] == solution["explanation"]
                report["checks"].append("custom_solution_persistence")
                document = split_document({"mode": "local", "deckTitle": "Desktop test", "text": "## Active recall\nExplain a concept without looking at the answer."})
                assert len(document["items"]) == 1
                state = service.store.action({"type": "knowledge-import", "document": document})
                item_id = next(iter(state["knowledge"]))
                state = service.store.action({"type": "knowledge-rate", "itemId": item_id, "rating": "good", "eventId": "desktop-knowledge-self-test", "seconds": 1})
                assert state["knowledgeCards"][item_id]["reviews"] == 1
                assert service.store.validate_import(state)["knowledge"] == state["knowledge"]
                report["checks"].append("knowledge_import_review_backup")
                avatar = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
                state = service.store.action({"type": "settings", "settings": {"avatar": avatar}})
                assert service.store.read()["settings"]["avatar"] == avatar
                assert service.store.validate_import(state)["settings"]["avatar"] == avatar
                report["checks"].append("avatar_persistence_and_backup")
                workspace_name = "企鹅的知识小屋"
                state = service.store.action({"type": "settings", "settings": {"workspaceName": workspace_name}})
                assert Store(service.store.path, BY_ID).read()["settings"]["workspaceName"] == workspace_name
                restored = Store(Path(tmp) / "restored.db", BY_ID)
                restored.action({"type": "import", "state": state})
                assert restored.read()["settings"]["workspaceName"] == workspace_name
                report["checks"].append("workspace_name_persistence_and_backup")
                report["passed"] = True
            finally:
                service.stop()
    except Exception:
        report["error"] = traceback.format_exc()
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


def show_error(message: str):
    LOGGER.error(message)
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, f"{APP_NAME} 无法启动", 0x10)
    elif sys.stderr:
        print(message, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} desktop")
    parser.add_argument("--data-dir", type=Path, help="Use an alternate local data directory")
    parser.add_argument("--self-test", type=Path, metavar="REPORT_JSON", help="Verify packaged runtime without opening a window")
    parser.add_argument("--gui-smoke-test", type=Path, metavar="REPORT_JSON", help="Verify WebView2 in a hidden window")
    parser.add_argument("--browser", action="store_true", help="Use a browser window instead of WebView2")
    args = parser.parse_args()
    if args.self_test:
        configure_logging(args.self_test.resolve().parent)
        return self_test(args.self_test)
    directory = args.data_dir.resolve() if args.data_dir else data_directory("CodeRecall-v2")
    configure_logging(directory)
    mutex = InstanceMutex(directory)
    if not mutex.is_owner:
        success = activate_existing(directory / "instance.json")
        mutex.close()
        if not success:
            show_error(f"{APP_NAME} 已在运行，但窗口尚未响应。请稍后再次打开。\n如果问题持续，请关闭现有 GuGuGaGa 或 CodeRecall 2 后重试。")
        return 0 if success else 1
    service = None
    try:
        if not (resource_root() / "dist" / "index.html").is_file():
            raise FileNotFoundError("缺少界面资源。请保留 GuGuGaGa.exe 与 _internal 文件夹在同一目录。")
        if not args.gui_smoke_test and not args.data_dir:
            candidates = [app_dir() / ".local" / "coderecall-v2.db", app_dir().parent.parent / ".local" / "coderecall-v2.db", directory.parent / "CodeRecall" / "coderecall.db", app_dir() / ".local" / "coderecall.db", app_dir().parent.parent / ".local" / "coderecall.db"]
            migrated = migrate_legacy_database(directory / "coderecall.db", candidates)
            if migrated:
                LOGGER.info("Copied existing progress from %s; original preserved", migrated)
        service = DesktopService(directory)
        service.start()
        if os.name == "nt":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
        if args.browser:
            browser_fallback(service, directory)
        else:
            try:
                native_window(service, directory, args.gui_smoke_test)
            except Exception:
                LOGGER.exception("Native window failed")
                if args.gui_smoke_test:
                    raise
                browser_fallback(service, directory)
        return 0
    except Exception:
        error = traceback.format_exc()
        LOGGER.error(error)
        if args.gui_smoke_test:
            args.gui_smoke_test.resolve().parent.mkdir(parents=True, exist_ok=True)
            args.gui_smoke_test.resolve().write_text(json.dumps({"passed": False, "error": error}, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            show_error("启动未完成，请检查软件文件是否完整。\n\n详细日志：" + str(directory / "desktop.log"))
        return 1
    finally:
        if service:
            service.stop()
        mutex.close()


if __name__ == "__main__":
    raise SystemExit(main())
