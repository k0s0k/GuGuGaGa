"""AI preview boundaries with fake transports only; no paid/network requests."""
import copy
import json
import socket
import ssl
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from server.ai_import import MAX_RESPONSE, _endpoint, _request_completion, https_context, split_document


def proposal():
    return {"format": "coderecall.knowledge", "version": 1, "deck": {"title": "模型标题"},
            "items": [{"title": "Word", "kind": "qa", "prompt": "Recall means?", "answer": "回忆", "tags": []}]}


class DocumentSplitTests(unittest.TestCase):
    def payload(self, **extra):
        return {"mode": "ai", "text": "# Recall\n回忆", "deckTitle": "我的英语笔记", "endpoint": "https://api.example.test/v1",
                "model": "some-chat-model", "apiKey": "a-test-secret", **extra}

    def test_local_headings_respect_code_fences_and_never_call_network(self):
        source = "# C++\n类负责释放资源。\n```python\n# code comment\nprint(1)\n```\n## 动画\n先设置关键帧。"
        with patch("server.ai_import._request_completion") as request:
            result = split_document(self.payload(mode="local", text=source))
        request.assert_not_called()
        self.assertEqual(len(result["items"]), 2)
        self.assertIn("# code comment", result["items"][0]["answer"])
        self.assertEqual(result["items"][1]["title"], "动画")

    def test_long_local_note_keeps_every_non_whitespace_character(self):
        source = "A" * 80000 + "\n\n" + "B" * 80000
        result = split_document(self.payload(mode="local", text=source))
        joined = "".join(item["answer"] for item in result["items"])
        self.assertEqual(joined.replace("\n", ""), source.replace("\n", ""))
        self.assertTrue(all(len(item["answer"]) <= 12000 for item in result["items"]))

    def test_local_split_preserves_leading_indented_markdown_code(self):
        result = split_document(self.payload(mode="local", text="    print('hello')\n"))
        self.assertEqual(result["items"][0]["answer"], "    print('hello')")

    def test_ai_preview_uses_fixed_schema_and_does_not_return_credentials(self):
        reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal())}}]}
        with patch("server.ai_import._request_completion", return_value=reply) as request:
            result = split_document(self.payload())
        endpoint, key, request_payload = request.call_args.args
        self.assertEqual(endpoint, ("https", "api.example.test", None, "/v1/chat/completions"))
        self.assertEqual(key, "a-test-secret")
        self.assertEqual(request_payload["max_tokens"], 8192)
        self.assertEqual(result["deck"]["title"], "我的英语笔记")
        self.assertNotIn("a-test-secret", json.dumps(result))
        self.assertNotIn("apiKey", request_payload)

    def test_fenced_json_supported_but_malformed_or_truncated_outputs_fail(self):
        content = "```json\n" + json.dumps(proposal()) + "\n```"
        with patch("server.ai_import._request_completion", return_value={"choices": [{"message": {"content": content}}]}):
            self.assertEqual(len(split_document(self.payload())["items"]), 1)
        variants = [{}, {"choices": []}, {"choices": [None]},
                    {"choices": [{"finish_reason": "length", "message": {"content": json.dumps(proposal())}}]},
                    {"choices": [{"message": {"content": "Some explanation then {}"}}]},
                    {"choices": [{"message": {"content": "{\"version\":NaN}"}}]},
                    {"choices": [{"message": {"content": json.dumps({**proposal(), "apiKey": "bad"})}}]}]
        for response in variants:
            with self.subTest(response=response), patch("server.ai_import._request_completion", return_value=response), self.assertRaises(ValueError):
                split_document(self.payload())

    def test_rejects_remote_http_and_invalid_endpoints_before_transport(self):
        bad_endpoints = ["http://api.example.test/v1", "file:///secret", "https://user:password@example.test/v1", "https://api.example.test/v1?key=secret", "https://api.example.test/#x", "https://api.example.test:bad/v1", "https://api.example.test/v1\r\nX: bad"]
        for endpoint in bad_endpoints:
            with self.subTest(endpoint=endpoint), patch("server.ai_import._request_completion") as request, self.assertRaises(ValueError):
                split_document(self.payload(endpoint=endpoint))
            request.assert_not_called()
        self.assertEqual(_endpoint("http://localhost:11434/v1")[3], "/v1/chat/completions")
        self.assertEqual(_endpoint("http://[::1]:11434/v1/chat/completions")[1], "::1")
        self.assertEqual(_endpoint("https://api.example.test")[3], "/v1/chat/completions")

    def test_input_limits_and_header_injection_are_rejected(self):
        variants = [dict(text=""), dict(text="a" * 200001), dict(apiKey="secret\r\nInjected: x"), dict(model=""), dict(mode="unknown")]
        for extra in variants:
            with self.subTest(extra=extra), patch("server.ai_import._request_completion") as request, self.assertRaises(ValueError):
                split_document(self.payload(**extra))
            request.assert_not_called()


class TransportTests(unittest.TestCase):
    def test_packaged_mac_adds_bundled_ca_without_disabling_tls_validation(self):
        context = Mock(check_hostname=True, verify_mode=ssl.CERT_REQUIRED)
        root = Path("GuGuGaGa.app/Contents/Frameworks")
        with patch.object(sys, "platform", "darwin"), patch.object(sys, "frozen", True, create=True), \
                patch("server.ai_import.resource_root", return_value=root), \
                patch("server.ai_import.ssl.create_default_context", return_value=context) as factory:
            self.assertIs(https_context(), context)
        factory.assert_called_once_with()
        context.load_verify_locations.assert_called_once_with(cafile=str(root / "packaging/cacert.pem"))
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def fake_connection(self, status=200, body=b"{}"):
        response = Mock(status=status)
        response.read.return_value = body
        connection = Mock()
        connection.getresponse.return_value = response
        return connection

    def test_redirect_never_followed_and_no_provider_body_echoed(self):
        connection = self.fake_connection(302, b"my-private-token")
        with patch("server.ai_import.http.client.HTTPSConnection", return_value=connection), self.assertRaisesRegex(ValueError, "重定向") as failure:
            _request_completion(("https", "api.example.test", None, "/v1/chat/completions"), "my-private-token", {})
        self.assertNotIn("my-private-token", str(failure.exception))
        connection.request.assert_called_once()
        connection.close.assert_called_once()
        connection.getresponse.return_value.read.assert_not_called()

    def test_http_errors_size_limit_and_bad_json_have_safe_errors(self):
        deeply_nested = b"[" * 2000 + b"0" + b"]" * 2000
        for status, body in ((401, b"secret"), (429, b"secret"), (500, b"secret"), (200, b"x" * (MAX_RESPONSE + 1)), (200, b"not json"), (200, deeply_nested)):
            connection = self.fake_connection(status, body)
            with self.subTest(status=status, size=len(body)), patch("server.ai_import.http.client.HTTPSConnection", return_value=connection), self.assertRaises(ValueError) as failure:
                _request_completion(("https", "api.example.test", None, "/v1/chat/completions"), "secret", {})
            self.assertNotIn("secret", str(failure.exception))
            connection.close.assert_called_once()

    def test_timeout_closes_connection_and_success_sets_timeout_and_auth(self):
        connection = self.fake_connection(200, b'{"choices": []}')
        with patch("server.ai_import.http.client.HTTPSConnection", return_value=connection) as factory:
            self.assertEqual(_request_completion(("https", "api.example.test", None, "/v1/chat/completions"), "secret", {"model": "example"}), {"choices": []})
        self.assertEqual(factory.call_args.kwargs["timeout"], 60)
        self.assertEqual(connection.request.call_args.kwargs["headers"]["Authorization"], "Bearer secret")
        connection = self.fake_connection()
        connection.request.side_effect = socket.timeout()
        with patch("server.ai_import.http.client.HTTPSConnection", return_value=connection), self.assertRaisesRegex(ValueError, "超时"):
            _request_completion(("https", "api.example.test", None, "/v1/chat/completions"), "secret", {})
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
