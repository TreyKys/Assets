#!/usr/bin/env python3
"""
relay_audit/test_suite.py

Boundary-condition / parser-anomaly / resource-limit test harness for a local
JSON-RPC relay translation layer.

Target is intentionally configurable via the RELAY_TARGET_URL environment
variable and defaults to the loopback address (http://127.0.0.1:7546). This
script is meant to be pointed at an endpoint you directly control and are
actively watching (e.g. a relay running on the same machine you're running
this script from) -- several of the test cases below (deep recursion, large
batch payloads, delayed transmission) are intentionally resource-heavy and
should not be fired at shared or third-party infrastructure without the
operator standing by.

Usage:
    python3 test_suite.py
    RELAY_TARGET_URL=http://127.0.0.1:7546 python3 test_suite.py
"""

import json
import logging
import os
import socket
import time
import uuid
from urllib.parse import urlparse

import requests

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

TARGET_URL = os.environ.get("RELAY_TARGET_URL", "http://127.0.0.1:7546")
RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_results.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_run.log")
REQUEST_TIMEOUT = 10  # seconds, per-request safety timeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("relay_audit")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _base_record(name, description):
    return {
        "test_name": name,
        "description": description,
        "target": TARGET_URL,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status_code": None,
        "elapsed_ms": None,
        "response_snippet": None,
        "error": None,
        "outcome": None,  # ok / handled_error / unexpected_5xx / exception / timeout
    }


def _send_raw(name, description, raw_body, headers=None, timeout=REQUEST_TIMEOUT):
    """Send a raw (already-serialized) HTTP POST body -- used for cases like
    duplicate JSON keys where a Python dict can't represent the payload."""
    record = _base_record(name, description)
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    start = time.monotonic()
    try:
        resp = requests.post(TARGET_URL, data=raw_body, headers=hdrs, timeout=timeout)
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        record["status_code"] = resp.status_code
        record["response_snippet"] = resp.text[:500]
        if 500 <= resp.status_code < 600:
            record["outcome"] = "unexpected_5xx"
        else:
            record["outcome"] = "ok"
    except requests.exceptions.Timeout:
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        record["error"] = "request timed out"
        record["outcome"] = "timeout"
    except requests.exceptions.ConnectionError as e:
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        record["error"] = f"connection error: {e}"
        record["outcome"] = "exception"
    except Exception as e:
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        record["error"] = f"{type(e).__name__}: {e}"
        record["outcome"] = "exception"
    log.info("[%s] status=%s elapsed=%sms outcome=%s", name, record["status_code"],
              record["elapsed_ms"], record["outcome"])
    return record


def _send_json(name, description, payload, timeout=REQUEST_TIMEOUT):
    try:
        raw_body = json.dumps(payload)
    except (TypeError, ValueError) as e:
        record = _base_record(name, description)
        record["error"] = f"payload not serializable: {e}"
        record["outcome"] = "exception"
        return record
    return _send_raw(name, description, raw_body, timeout=timeout)


# --------------------------------------------------------------------------
# Test cases
# --------------------------------------------------------------------------

def test_duplicate_json_keys():
    """1. Duplicate JSON keys -- check which value the relay's JSON parser
    keeps (first-wins, last-wins, or a parse error)."""
    raw = '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","method":"eth_blockNumber","params":[]}'
    return _send_raw(
        "duplicate_json_keys",
        "Duplicate top-level 'method' key -- tests key precedence in the relay's JSON parser.",
        raw,
    )


def test_deep_array_recursion():
    """2. Deeply nested arrays -- tests recursive-descent parser stack limits."""
    depth = 550
    nested = []
    for _ in range(depth):
        nested = [nested]
    payload = {"jsonrpc": "2.0", "id": 2, "method": "eth_call", "params": [nested, "latest"]}
    return _send_json(
        "deep_array_recursion",
        f"Array nested {depth} levels deep in params -- tests parser/stack recursion limits.",
        payload,
        timeout=15,
    )


def test_integer_hex_boundaries():
    """3. Extreme hex values well beyond a 256-bit word."""
    huge_hex = "0x" + "f" * 128  # 512 bits of 'f'
    negative_like = "0x-1"
    non_hex = "0xzzzz"
    results = []
    for label, value in [
        ("512bit_overflow", huge_hex),
        ("malformed_negative", negative_like),
        ("non_hex_chars", non_hex),
    ]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "eth_getBalance",
            "params": [value, "latest"],
        }
        r = _send_json(
            f"integer_hex_boundary_{label}",
            f"Hex value boundary case '{label}': {value[:24]}... -- tests numeric parsing limits.",
            payload,
        )
        results.append(r)
    return results


def test_batch_payload_limits():
    """4. Large batch array -- tests per-request call-count limits."""
    batch_size = 1200
    batch = [
        {"jsonrpc": "2.0", "id": i, "method": "eth_chainId", "params": []}
        for i in range(batch_size)
    ]
    return _send_json(
        "batch_payload_limits",
        f"Single JSON-RPC batch array containing {batch_size} calls -- tests batch size limits.",
        batch,
        timeout=30,
    )


def test_type_mismatch_injection():
    """5. Objects (incl. __proto__) supplied where scalars/arrays are expected."""
    payload = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "eth_getBalance",
        "params": [{"__proto__": {"polluted": True}, "toString": "0xdeadbeef"}, "latest"],
    }
    return _send_json(
        "type_mismatch_injection",
        "Object (with __proto__ key) supplied where a string address param is expected -- "
        "tests type coercion / prototype pollution handling.",
        payload,
    )


def test_signature_structure_anomalies():
    """6. Malformed raw-transaction / ECDSA signature fields."""
    cases = {
        "truncated_rawtx": "0xf86c8085",
        "non_hex_rawtx": "0xzzznotarealtransaction",
        "oversized_v": "0x" + "01" * 4 + "ff" * 200,
        "empty_string": "",
    }
    results = []
    for label, raw_tx in cases.items():
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "eth_sendRawTransaction",
            "params": [raw_tx],
        }
        r = _send_json(
            f"signature_anomaly_{label}",
            f"Malformed raw transaction / signature case '{label}' -- tests ECDSA/RLP validation.",
            payload,
        )
        results.append(r)
    return results


def test_null_bytes_unicode():
    """7. Null bytes and multi-byte UTF-8 injected into string fields."""
    null_byte = chr(0)
    multibyte = "\u00e9\u4e2d\U0001F600"  # e-acute, CJK char, emoji
    injected = "0x" + null_byte + null_byte + "deadbeef" + multibyte
    payload = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "eth_call",
        "params": [
            {
                "to": "0x0000000000000000000000000000000000000000",
                "data": injected,
            },
            "latest",
        ],
    }
    return _send_json(
        "null_bytes_unicode",
        "Null bytes (\\u0000) and multi-byte UTF-8 (accented + CJK + emoji) injected into a "
        "string field -- tests string sanitization / encoding handling.",
        payload,
    )
def test_method_case_sensitivity():
    """8. Method name capitalization variants."""
    variants = ["eth_chainId", "ETH_chainId", "eth_CHAINID", "Eth_ChainId", "ETH_CHAINID"]
    results = []
    for method in variants:
        payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": []}
        r = _send_json(
            f"method_case_{method}",
            f"Method name capitalization variant '{method}' -- tests case-sensitive routing.",
            payload,
        )
        results.append(r)
    return results


def test_caching_state_consistency():
    """9. Rapid sequential eth_call requests to check for response desync."""
    results = []
    payload_template = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": "0x0000000000000000000000000000000000000000", "data": "0x"}, "latest"],
    }
    for i in range(20):
        payload = dict(payload_template, id=i)
        r = _send_json(
            f"cache_consistency_{i}",
            "Rapid sequential eth_call -- tests for response desynchronization / stale cache.",
            payload,
            timeout=5,
        )
        results.append(r)
    return results


def test_connection_handshake_timeout():
    """10. Delayed transmission window -- send headers, pause, then trickle the body
    over a single raw socket. One connection, bounded delay -- not a concurrent
    slow-connection flood."""
    record = _base_record(
        "connection_handshake_timeout",
        "Single connection with a delayed/trickled request body -- tests the relay's "
        "read-timeout handling on slow clients.",
    )
    parsed = urlparse(TARGET_URL)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    body = json.dumps({"jsonrpc": "2.0", "id": 10, "method": "eth_chainId", "params": []})
    body_bytes = body.encode("utf-8")

    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=REQUEST_TIMEOUT) as sock:
            headers = (
                f"POST {parsed.path or '/'} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body_bytes)}\r\n"
                f"Connection: close\r\n\r\n"
            )
            sock.sendall(headers.encode("utf-8"))
            time.sleep(2)  # bounded delay before trickling the body
            chunk_size = max(1, len(body_bytes) // 5)
            for i in range(0, len(body_bytes), chunk_size):
                sock.sendall(body_bytes[i : i + chunk_size])
                time.sleep(0.5)
            sock.settimeout(REQUEST_TIMEOUT)
            response = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        text = response.decode("utf-8", errors="replace")
        first_line = text.splitlines()[0] if text else ""
        if " " in first_line:
            try:
                record["status_code"] = int(first_line.split(" ")[1])
            except (IndexError, ValueError):
                pass
        record["response_snippet"] = text[:500]
        if record["status_code"] and 500 <= record["status_code"] < 600:
            record["outcome"] = "unexpected_5xx"
        else:
            record["outcome"] = "ok" if response else "no_response"
    except socket.timeout:
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        record["error"] = "socket timed out"
        record["outcome"] = "timeout"
    except Exception as e:
        record["elapsed_ms"] = round((time.monotonic() - start) * 1000, 2)
        record["error"] = f"{type(e).__name__}: {e}"
        record["outcome"] = "exception"

    log.info("[connection_handshake_timeout] status=%s elapsed=%sms outcome=%s",
              record["status_code"], record["elapsed_ms"], record["outcome"])
    return record


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

TEST_FUNCS = [
    test_duplicate_json_keys,
    test_deep_array_recursion,
    test_integer_hex_boundaries,
    test_batch_payload_limits,
    test_type_mismatch_injection,
    test_signature_structure_anomalies,
    test_null_bytes_unicode,
    test_method_case_sensitivity,
    test_caching_state_consistency,
    test_connection_handshake_timeout,
]


def run_all():
    log.info("Starting relay audit against target=%s", TARGET_URL)
    all_results = []
    for fn in TEST_FUNCS:
        log.info("Running test group: %s", fn.__name__)
        try:
            result = fn()
        except Exception as e:
            result = _base_record(fn.__name__, fn.__doc__ or "")
            result["error"] = f"unhandled exception in test runner: {type(e).__name__}: {e}"
            result["outcome"] = "exception"
            log.exception("Unhandled exception running %s", fn.__name__)
        if isinstance(result, list):
            all_results.extend(result)
        else:
            all_results.append(result)

    with open(RESULTS_PATH, "w") as f:
        json.dump(all_results, f, indent=2)
    log.info("Wrote %d result records to %s", len(all_results), RESULTS_PATH)
    return all_results


if __name__ == "__main__":
    run_all()
