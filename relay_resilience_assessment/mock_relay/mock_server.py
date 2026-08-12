#!/usr/bin/env python3
"""
A tiny, deliberately-imperfect JSON-RPC mock server, used ONLY to validate
that the assessment harness itself works end-to-end (correct anomaly
detection, logging, report generation) before pointing it at a real relay.

This is not a security target and not a model of any real relay's internals
- it just needs to produce a *few* of the deviant behaviors the harness is
built to catch, so a dry run through run_all.py exercises every code path:
  - normal 200 JSON-RPC responses for well-formed requests
  - a 500 for one specific gas-exhaustion case
  - an artificial multi-second delay for another
  - a non-JSON body for a malformed-hex case
  - a connection reset for one deep-nesting depth
Run:
    python mock_relay/mock_server.py --port 7546
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # keep test output quiet

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        # Simulate a connection reset for very large nested-array payloads
        # instead of trying to actually json.loads() something absurd.
        if length > 20000:
            try:
                self.connection.close()
            except OSError:
                pass
            return

        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            self._send_json(200, {"jsonrpc": "2.0", "id": None, "result": "0x1"})
            return

        try:
            req = json.loads(text)
        except ValueError:
            # e.g. duplicate-key raw JSON - python's json module actually
            # accepts duplicate keys (last one wins) so this path mostly
            # covers genuinely malformed hex/unicode text.
            self._send_raw(200, b"not-json-response-body-for-testing")
            return

        method = req.get("method", "") if isinstance(req, dict) else ""
        params = req.get("params", []) if isinstance(req, dict) else []

        if isinstance(method, str) and "estimateGas" in method:
            data = ""
            if params and isinstance(params[0], dict):
                data = params[0].get("data", "")
            if isinstance(data, str) and data.startswith("0x5b6000"):
                # simulate the relay wedging on an infinite-loop bytecode case
                self._send_json(500, {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32000, "message": "simulation error"}})
                return

        if isinstance(method, str) and method.lower() == "eth_getbalance":
            block_tag = params[1] if len(params) > 1 else None
            if isinstance(block_tag, str) and len(block_tag) > 80:
                time.sleep(11)  # exceed the 10s anomaly threshold on purpose

        result = "0x1"
        if isinstance(method, str) and method.lower() == "eth_blocknumber":
            result = "0x10"

        self._send_json(200, {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None, "result": result})

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_raw(self, status, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7546)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), MockHandler)
    print(f"mock relay listening on http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
