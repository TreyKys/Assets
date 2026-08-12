"""
Scenario 10: Slow HTTP Body Transmission
============================================
A "slowloris"-style single-connection test: open one TCP connection, send
valid HTTP headers with a correct Content-Length, then trickle the JSON body
in one byte at a time with a delay between bytes. This checks whether the
relay's HTTP server enforces a read/idle timeout on the request body, or
holds the connection (and whatever thread/worker services it) open
indefinitely.

Deliberately uses a single connection, not many, per the assessment's
"not bandwidth/connection saturation" constraint - this measures the
relay's *timeout policy*, not its capacity limit.

Usage:
    python s10_slow_body_transmission.py [--delay 10] [--bytes-per-write 1]

The assessment brief's reference rate is 1 byte / 10s. That is exercised
here but bounded by `--max-wait` so the script terminates and logs a result
instead of hanging forever if the relay does have no timeout at all.
"""
import argparse
import json
import socket
import sys
import time
import os
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from harness.logger import ResultLogger

SCENARIO = "s10_slow_body_transmission"


def build_payload() -> bytes:
    body = json.dumps(
        {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": "slow-body"}
    ).encode("utf-8")
    return body


def run(delay_seconds: float, bytes_per_write: int, max_wait_seconds: float):
    logger = ResultLogger()
    parsed = urlparse(config.TARGET_URL)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"

    body = build_payload()
    headers = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("utf-8")

    result = {
        "status_code": None,
        "elapsed_seconds": None,
        "body_preview": None,
        "error": None,
        "is_anomaly": False,
        "anomaly_reasons": [],
        "bytes_sent_of_body": 0,
        "total_body_bytes": len(body),
        "delay_seconds_per_write": delay_seconds,
    }

    start = time.monotonic()
    sock = None
    try:
        sock = socket.create_connection((host, port), timeout=max_wait_seconds)
        sock.sendall(headers)

        for i in range(0, len(body), bytes_per_write):
            chunk = body[i : i + bytes_per_write]
            sock.sendall(chunk)
            result["bytes_sent_of_body"] = i + len(chunk)
            elapsed_so_far = time.monotonic() - start
            if elapsed_so_far > max_wait_seconds:
                result["elapsed_seconds"] = round(elapsed_so_far, 3)
                result["error"] = (
                    f"aborted after {elapsed_so_far:.1f}s at byte "
                    f"{result['bytes_sent_of_body']}/{len(body)} - relay kept "
                    "connection open the whole time (no idle/read timeout observed "
                    f"within max_wait={max_wait_seconds}s)"
                )
                result["is_anomaly"] = True
                result["anomaly_reasons"].append("connection_held_open_no_timeout")
                break
            time.sleep(delay_seconds)
        else:
            # finished sending the whole (slow) body - now read the response
            sock.settimeout(max(1.0, max_wait_seconds - (time.monotonic() - start)))
            try:
                response = sock.recv(65536)
                elapsed = time.monotonic() - start
                result["elapsed_seconds"] = round(elapsed, 3)
                text = response.decode("utf-8", errors="replace")
                result["body_preview"] = text[:4000]
                first_line = text.split("\r\n", 1)[0] if text else ""
                if " " in first_line:
                    try:
                        result["status_code"] = int(first_line.split(" ")[1])
                    except (IndexError, ValueError):
                        pass
                if result["status_code"] and result["status_code"] >= 500:
                    result["is_anomaly"] = True
                    result["anomaly_reasons"].append(f"http_{result['status_code']}")
                if elapsed > config.ANOMALY_LATENCY_SECONDS:
                    result["is_anomaly"] = True
                    result["anomaly_reasons"].append(
                        f"latency_over_{config.ANOMALY_LATENCY_SECONDS}s"
                    )
            except socket.timeout:
                elapsed = time.monotonic() - start
                result["elapsed_seconds"] = round(elapsed, 3)
                result["error"] = "timed out waiting for response after full slow body was sent"
                result["is_anomaly"] = True
                result["anomaly_reasons"].append("no_response_after_slow_body")

    except (ConnectionError, socket.error, socket.timeout) as exc:
        elapsed = time.monotonic() - start
        result["elapsed_seconds"] = round(elapsed, 3)
        result["error"] = f"connection_error: {exc}"
        result["is_anomaly"] = True
        result["anomaly_reasons"].append("connection_dropped_or_refused")
    finally:
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    payload_description = {
        "headers": headers.decode("utf-8", errors="replace"),
        "body": body.decode("utf-8", errors="replace"),
        "transmission": f"{bytes_per_write} byte(s) every {delay_seconds}s",
    }
    return [logger.record(SCENARIO, "slow_body_single_connection", payload_description, result)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delay", type=float, default=10.0,
        help="seconds to wait between writes (assessment reference: 10)",
    )
    parser.add_argument("--bytes-per-write", type=int, default=1)
    parser.add_argument(
        "--max-wait", type=float, default=60.0,
        help="give up and record the anomaly after this many seconds total",
    )
    args = parser.parse_args()

    for r in run(args.delay, args.bytes_per_write, args.max_wait):
        print(r["case"], "->", r["result"].get("status_code"), r["result"].get("anomaly_reasons"))
