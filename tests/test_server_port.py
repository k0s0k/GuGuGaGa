"""Regression: Windows must not silently reuse another application's port."""
from http.server import BaseHTTPRequestHandler
import unittest
from server.app import LocalHTTPServer


class LocalPortTests(unittest.TestCase):
    def test_occupied_port_is_rejected_instead_of_shared(self):
        with LocalHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler) as first:
            with self.assertRaises(OSError):
                second = LocalHTTPServer(first.server_address, BaseHTTPRequestHandler)
                second.server_close()


if __name__ == "__main__":
    unittest.main()
