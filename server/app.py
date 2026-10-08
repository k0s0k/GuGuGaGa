import argparse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import secrets
import socket
import sys
from urllib.parse import urlsplit
from .catalog import BY_ID, summaries, detail, CATEGORY_ORDER
from .runner import capabilities, run
from .store import Store
from .runtime import resource_root
from .ai_import import split_document
from .knowledge import validate_document

ROOT = resource_root()
TOKEN = secrets.token_urlsafe(32)


class LocalHTTPServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR can let two processes listen on the same port,
    # causing requests to reach an unrelated application instead of this one.
    allow_reuse_address = not hasattr(socket, "SO_EXCLUSIVEADDRUSE")

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_handler(store, port, static_root=None):
    # Vite 在开发模式下保留浏览器 Host 并代理 /api 到 8766。
    allowed_ports = {port, 5173}
    frontend = Path(static_root) if static_root is not None else ROOT / "dist"

    def local_authority(value, origin=False):
        if not isinstance(value, str) or not value or value.strip() != value:
            return False
        try:
            parsed = urlsplit(value if origin else "http://" + value)
            return (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")
                    and parsed.port in allowed_ports and parsed.username is None and parsed.password is None
                    and not parsed.path and not parsed.query and not parsed.fragment)
        except ValueError:
            return False

    class Handler(SimpleHTTPRequestHandler):
        server_version = "CodeRecall/2.0"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(frontend), **kwargs)

        def log_message(self, fmt, *args):
            if "/api/" not in str(args[0]) or (len(args) > 1 and str(args[1]) != "200"):
                super().log_message(fmt, *args)

        def send_json(self, value, status=200):
            data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def trusted_host(self):
            hosts = self.headers.get_all("Host", [])
            return len(hosts) == 1 and local_authority(hosts[0])

        def list_directory(self, path):
            self.send_error(403, "Directory listing is disabled")
            return None

        def do_HEAD(self):
            if not self.trusted_host():
                self.send_response(403)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            return super().do_HEAD()

        def do_GET(self):
            if not self.trusted_host():
                return self.send_json({"error": "仅支持本机访问"}, 403)
            path = urlsplit(self.path).path
            try:
                if path == "/api/bootstrap":
                    return self.send_json({"problems": summaries(), "categories": CATEGORY_ORDER, "state": store.read(), "capabilities": capabilities(), "token": TOKEN})
                if path == "/api/state":
                    return self.send_json(store.read())
                if path.startswith("/api/problems/"):
                    return self.send_json(detail(int(path.rsplit("/", 1)[1])))
                if path.startswith("/api/"):
                    return self.send_json({"error": "接口不存在"}, 404)
                if not (frontend / "index.html").exists():
                    return self.send_json({"message": "前端尚未构建。请先执行 npm install 与 npm run build，开发时可运行 npm run dev。"}, 503)
                if path == "/" or ("." not in path.rsplit("/", 1)[-1]):
                    self.path = "/index.html"
                elif path == "/favicon.ico":
                    self.path = "/favicon.svg"
                return super().do_GET()
            except ConnectionError:
                return
            except (ValueError, KeyError, TypeError):
                return self.send_json({"error": "题目不存在"}, 404)
            except Exception as exc:
                print(f"Request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
                return self.send_json({"error": "读取失败，请查看服务端日志并重试"}, 500)

        def do_POST(self):
            tokens = self.headers.get_all("X-CodeRecall-Token", [])
            if not self.trusted_host() or len(tokens) != 1 or not tokens[0].isascii() or not secrets.compare_digest(tokens[0], TOKEN):
                return self.send_json({"error": "会话已失效，请刷新页面"}, 403)
            origins = self.headers.get_all("Origin", [])
            origin = origins[0] if origins else None
            if len(origins) > 1 or (origin is not None and not local_authority(origin, origin=True)) or self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.send_json({"error": "不允许跨站请求"}, 403)
            try:
                if self.headers.get_content_type() != "application/json":
                    return self.send_json({"error": "请使用 application/json 请求格式"}, 415)
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
                    return self.send_json({"error": "请求长度格式错误"}, 400)
                try:
                    length = int(lengths[0])
                except ValueError:
                    return self.send_json({"error": "请求长度格式错误"}, 400)
                max_body = 64 * 1024 * 1024 if urlsplit(self.path).path == "/api/action" else 8 * 1024 * 1024
                if not 0 < length <= max_body:
                    return self.send_json({"error": f"请求大小无效（最多 {max_body // 1024 // 1024} MB）"}, 413)
                self.connection.settimeout(10)
                body = self.rfile.read(length)
                if len(body) != length:
                    return self.send_json({"error": "请求内容不完整，请重试"}, 400)
                def invalid_constant(value):
                    raise ValueError("JSON 不支持 NaN 或 Infinity")
                payload = json.loads(body, parse_constant=invalid_constant)
                if not isinstance(payload, dict):
                    raise ValueError("请求格式错误")
                path = urlsplit(self.path).path
                if path == "/api/action":
                    return self.send_json(store.action(payload))
                if path == "/api/knowledge/split":
                    return self.send_json(split_document(payload))
                if path == "/api/knowledge/validate":
                    return self.send_json(validate_document(payload))
                if path == "/api/run":
                    pid = int(payload.get("problemId"))
                    if pid not in BY_ID:
                        raise ValueError("题目不存在")
                    return self.send_json(run(BY_ID[pid], payload))
                return self.send_json({"error": "接口不存在"}, 404)
            except ConnectionError:
                return
            except socket.timeout:
                return self.send_json({"error": "读取请求超时，请重试"}, 408)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.send_json({"error": "JSON 格式无效，请检查请求或备份文件"}, 400)
            except RecursionError:
                return self.send_json({"error": "JSON 嵌套过深，请简化文件结构"}, 400)
            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                return self.send_json({"error": str(exc) or "请求格式错误"}, 400)
            except Exception as exc:
                print(f"Request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
                return self.send_json({"error": "操作未完成，请查看服务端日志并重试"}, 500)
    return Handler


def main():
    parser = argparse.ArgumentParser(description="CodeRecall local server")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data", default=str(ROOT / ".local" / "coderecall-v2.db"))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口必须位于 1–65535")
    if Path(args.data).resolve() == (ROOT / ".local" / "coderecall-v2.db").resolve():
        from desktop_support import migrate_legacy_database
        migrate_legacy_database(Path(args.data), [ROOT / ".local" / "coderecall.db"])
    store = Store(args.data, BY_ID)
    try:
        server = LocalHTTPServer(("127.0.0.1", args.port), make_handler(store, args.port))
    except OSError as exc:
        parser.exit(1, f"无法监听 127.0.0.1:{args.port}，请检查端口是否被占用，或使用 --port 指定其他端口。\n{exc}\n")
    print(f"CodeRecall: http://127.0.0.1:{args.port}", flush=True)
    print(f"Local data: {Path(args.data).resolve()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCodeRecall stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
