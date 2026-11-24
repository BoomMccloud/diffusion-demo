"""Loopback Chat Completions relay for Pi's normal and summary requests."""

import http.client
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_URL = "http://127.0.0.1:8741/v1"
SETTINGS = {"compaction": {"enabled": True, "reserveTokens": 40960, "keepRecentTokens": 12000}}
MODEL = {
    "contextWindow": 131072,
    "maxTokens": 32768,
    "compat": {"maxTokensField": "max_tokens", "supportsDeveloperRole": False},
}


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


class CloverRelay(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(204 if self.path == "/health" else 404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        authorization = self.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            self.send_error(401, "Expected bearer authorization")
            return
        try:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        except (KeyError, ValueError):
            self.send_error(400, "Expected JSON body")
            return
        endpoint = self.server.upstream
        thinking = len(endpoint) != 1 or bool(payload.get("tools"))
        flags = {"enable_thinking": thinking, "preserve_thinking": thinking}
        payload["chat_template_kwargs"] = flags
        payload["temperature"] = 0
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "X-User-ID": "user-1",
            "X-Session-ID": self.server.session_id,
        }
        if len(endpoint) == 1:
            upstream = UnixHTTPConnection(endpoint[0], timeout=600)
        else:
            host, port = endpoint
            upstream = http.client.HTTPConnection(host, int(port), timeout=600)
        try:
            try:
                upstream.request("POST", self.path, json.dumps(payload).encode(), headers)
                response = upstream.getresponse()
            except OSError:
                self.send_error(502, "Clover upstream connection failed")
                return
            print(json.dumps({
                "status": response.status,
                "authorized": True,
                "user_id": headers["X-User-ID"],
                "session_id": headers["X-Session-ID"],
                "thinking": flags,
                "tools": bool(payload.get("tools")),
                "max_tokens": payload.get("max_tokens"),
            }), flush=True)
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            self.end_headers()
            while chunk := response.read1(65536):
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        finally:
            upstream.close()


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8741), CloverRelay) as server:
        _, server.session_id, *endpoint = sys.argv
        server.upstream = endpoint or ("43.107.54.53", "31002")
        server.serve_forever()
