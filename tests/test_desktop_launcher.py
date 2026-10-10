"""Exercise the HTTP service and native desktop selection without opening a GUI."""
from contextlib import ExitStack
import http.client
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import tempfile
import threading
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from desktop import APP_ID, DesktopService, InstanceMutex, activate_existing, native_icon, native_window
from server.app import LocalHTTPServer


class OtherAppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"existing unrelated application"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def request(port, path, method="GET", headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, path, body=b"{}" if method == "POST" else None, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        connection.close()


class DesktopServiceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="coderecall-launcher-test-")))
        self.stack.enter_context(patch("server.app.SimpleHTTPRequestHandler.log_message"))

    def start_service(self, port=0):
        service = DesktopService(self.root / "data", initial_port=port)
        self.stack.callback(service.stop)
        service.start()
        return service

    def test_occupied_preferred_port_falls_back_without_disturbing_listener(self):
        other = LocalHTTPServer(("127.0.0.1", 0), OtherAppHandler)
        other_thread = threading.Thread(target=other.serve_forever, daemon=True)
        other_thread.start()

        def close_other():
            other.shutdown()
            other.server_close()
            other_thread.join(timeout=3)

        self.stack.callback(close_other)
        preferred = other.server_address[1]
        service = self.start_service(preferred)
        self.assertNotEqual(service.port, preferred)
        self.assertEqual(request(preferred, "/"), (200, "existing unrelated application"))
        status, body = request(service.port, "/api/desktop/status")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["appId"], APP_ID)
        service.stop()
        self.assertEqual(request(preferred, "/"), (200, "existing unrelated application"))

    def test_activation_rejects_missing_wrong_non_ascii_token_and_untrusted_host(self):
        service = self.start_service()
        service.on_activate = Mock()
        headers_to_reject = [
            {},
            {"X-CodeRecall-Desktop-Key": "wrong-token"},
            {"X-CodeRecall-Desktop-Key": "caf\u00e9"},
            {"X-CodeRecall-Desktop-Key": service.key, "Host": "example.org"},
        ]
        for headers in headers_to_reject:
            with self.subTest(headers=headers):
                status, body = request(service.port, "/api/desktop/activate", "POST", headers)
                self.assertEqual(status, 403, body)
        service.on_activate.assert_not_called()
        self.assertTrue(activate_existing(service.marker, timeout=0.5))
        service.on_activate.assert_called_once_with()

    def test_status_rejects_nonlocal_host(self):
        service = self.start_service()
        status, _ = request(service.port, "/api/desktop/status", headers={"Host": "example.org"})
        self.assertEqual(status, 403)

    def test_stop_removes_only_own_instance_marker_and_closes_listener(self):
        service = self.start_service()
        marker = json.loads(service.marker.read_text(encoding="utf-8"))
        self.assertEqual(marker["port"], service.port)
        self.assertEqual(marker["pid"], os.getpid())
        self.assertEqual(marker["key"], service.key)
        service.stop()
        self.assertFalse(service.thread.is_alive())
        self.assertFalse(service.marker.exists())
        self.assertEqual(service.server.fileno(), -1)
        service.stop()  # Shutdown and cleanup are safe to repeat.

    def test_stop_preserves_marker_owned_by_another_instance(self):
        service = self.start_service()
        replacement = {"appId": APP_ID, "pid": os.getpid(), "key": "replacement-instance", "port": service.port}
        service.marker.write_text(json.dumps(replacement), encoding="utf-8")
        service.stop()
        self.assertEqual(json.loads(service.marker.read_text(encoding="utf-8")), replacement)

    def test_invalid_marker_data_is_treated_as_stale(self):
        marker = self.root / "invalid-instance.json"
        for value in (None, [], "invalid", {"appId": "another-app", "port": 8767},
                      {"appId": APP_ID, "port": True}, {"appId": APP_ID, "port": 65536},
                      {"appId": APP_ID, "port": 8767, "key": None}):
            with self.subTest(value=value):
                marker.write_text(json.dumps(value), encoding="utf-8")
                self.assertFalse(activate_existing(marker, timeout=0.05))
        service = self.start_service()
        service.marker.write_text("[]", encoding="utf-8")
        service.stop()
        self.assertEqual(service.marker.read_text(encoding="utf-8"), "[]")

    def test_frozen_static_payload_is_served_from_bundle_root(self):
        bundle = self.root / "portable" / "_internal"
        frontend = bundle / "dist"
        (frontend / "assets").mkdir(parents=True)
        html = "<!doctype html><title>portable frontend</title><div id='root'>打包资源</div>"
        (frontend / "index.html").write_text(html, encoding="utf-8")
        (frontend / "assets" / "test.js").write_text("window.packagedAsset = true;", encoding="utf-8")
        self.stack.enter_context(patch("server.app.ROOT", bundle))
        service = self.start_service()
        self.assertEqual(request(service.port, "/"), (200, html))
        self.assertEqual(request(service.port, "/assets/test.js"), (200, "window.packagedAsset = true;"))


class InstanceMutexTests(unittest.TestCase):
    def test_second_instance_cannot_own_mutex_and_release_allows_restart(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            first = InstanceMutex(root)
            stack.callback(first.close)
            self.assertTrue(first.is_owner)
            second = InstanceMutex(root)
            stack.callback(second.close)
            self.assertFalse(second.is_owner)
            second.close()
            first.close()
            first.close()
            restarted = InstanceMutex(root)
            stack.callback(restarted.close)
            self.assertTrue(restarted.is_owner)

    def test_distinct_data_directories_have_independent_instances(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            first = InstanceMutex(root / "one")
            stack.callback(first.close)
            second = InstanceMutex(root / "two")
            stack.callback(second.close)
            self.assertTrue(first.is_owner)
            self.assertTrue(second.is_owner)

    @unittest.skipIf(os.name == "nt", "POSIX flock lifecycle")
    def test_process_exit_releases_lock_without_deleting_lock_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = subprocess.Popen(
                [sys.executable, "-c", "from desktop import InstanceMutex; from pathlib import Path; import sys,time; "
                 "lock=InstanceMutex(Path(sys.argv[1])); print(lock.is_owner, flush=True); time.sleep(60)", str(root)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                self.assertEqual(child.stdout.readline().strip(), "True")
                blocked = InstanceMutex(root)
                self.addCleanup(blocked.close)
                self.assertFalse(blocked.is_owner)
            finally:
                child.kill()
                child.communicate(timeout=5)
            self.assertTrue((root / "instance.lock").is_file())
            restarted = InstanceMutex(root)
            self.addCleanup(restarted.close)
            self.assertTrue(restarted.is_owner)
            restarted.close()


class NativeWindowTests(unittest.TestCase):
    def test_native_renderer_and_icon_follow_platform(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for platform, renderer, extension in (("darwin", "cocoa", ".icns"), ("win32", "edgechromium", ".ico")):
                with self.subTest(platform=platform), patch("desktop.sys.platform", platform), \
                        patch("desktop.resource_root", return_value=root):
                    webview = Mock()
                    webview.settings = {}
                    service = Mock(url="http://127.0.0.1:8767")
                    with patch.dict(sys.modules, {"webview": webview}):
                        native_window(service, root / "user-data")
                    self.assertEqual(native_icon(), root / "packaging" / ("GuGuGaGa" + extension))
                    self.assertEqual(webview.start.call_args.kwargs["gui"], renderer)
                    self.assertEqual(webview.start.call_args.kwargs["icon"], str(native_icon()))
                    self.assertFalse(webview.start.call_args.kwargs["private_mode"])
                    self.assertTrue(webview.settings["ALLOW_DOWNLOADS"])
                    service.on_activate()
                    webview.create_window.return_value.restore.assert_called_once()
                    webview.create_window.return_value.show.assert_called_once()


if __name__ == "__main__":
    unittest.main()
