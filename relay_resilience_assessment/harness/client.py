"""Thin HTTP client wrapper that sends a request, times it, classifies the
outcome, and hands the classified result to the logger.

Kept deliberately simple (stdlib `requests` only) so every scenario script
goes through the exact same anomaly-detection logic - status >= 500,
connection failure, or latency over the configured threshold.
"""
import time

import requests

import config
from harness.logger import ResultLogger
from harness.rate_limiter import RateLimiter

_rate_limiter = RateLimiter(config.RATE_LIMIT_RPS)
_logger = ResultLogger()


def send(scenario: str, case: str, payload, headers=None, timeout=None,
         expect_json=True):
    """
    payload: dict (will be JSON-encoded) or raw bytes/str (sent as-is, so
             callers can construct deliberately malformed/duplicate-key JSON
             text that a Python dict could never represent).
    Returns the logged record dict.
    """
    _rate_limiter.acquire()
    headers = headers or config.HEADERS
    timeout = timeout if timeout is not None else config.REQUEST_TIMEOUT_SECONDS

    if isinstance(payload, (dict, list)):
        import json as _json
        body = _json.dumps(payload)
    else:
        body = payload

    start = time.monotonic()
    result = {
        "status_code": None,
        "elapsed_seconds": None,
        "body_preview": None,
        "error": None,
        "is_anomaly": False,
        "anomaly_reasons": [],
    }

    try:
        resp = requests.post(
            config.TARGET_URL, data=body, headers=headers, timeout=timeout
        )
        elapsed = time.monotonic() - start
        result["status_code"] = resp.status_code
        result["elapsed_seconds"] = round(elapsed, 3)
        result["body_preview"] = resp.text[:4000]

        if resp.status_code >= 500:
            result["is_anomaly"] = True
            result["anomaly_reasons"].append(f"http_{resp.status_code}")

        if expect_json:
            try:
                result["parsed_json"] = resp.json()
            except ValueError:
                result["is_anomaly"] = True
                result["anomaly_reasons"].append("non_json_response")

        if elapsed > config.ANOMALY_LATENCY_SECONDS:
            result["is_anomaly"] = True
            result["anomaly_reasons"].append(
                f"latency_over_{config.ANOMALY_LATENCY_SECONDS}s"
            )

    except requests.exceptions.Timeout:
        elapsed = time.monotonic() - start
        result["elapsed_seconds"] = round(elapsed, 3)
        result["error"] = "timeout"
        result["is_anomaly"] = True
        result["anomaly_reasons"].append("request_timeout")

    except requests.exceptions.ConnectionError as exc:
        elapsed = time.monotonic() - start
        result["elapsed_seconds"] = round(elapsed, 3)
        result["error"] = f"connection_error: {exc}"
        result["is_anomaly"] = True
        result["anomaly_reasons"].append("connection_dropped_or_refused")

    except Exception as exc:  # pragma: no cover - defensive catch-all
        elapsed = time.monotonic() - start
        result["elapsed_seconds"] = round(elapsed, 3)
        result["error"] = f"unexpected_client_exception: {exc!r}"
        result["is_anomaly"] = True
        result["anomaly_reasons"].append("client_exception")

    return _logger.record(scenario, case, payload, result)


def liveness_probe(scenario: str, case: str = "liveness_probe"):
    """Cheap eth_chainId call used after a suspicious case to check whether
    the relay is still responsive (used by the resource-exhaustion and
    slow-body scenarios)."""
    return send(
        scenario,
        case,
        {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": "probe"},
    )
