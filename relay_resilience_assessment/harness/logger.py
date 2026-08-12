"""Structured logging for the resilience assessment.

Every request/response pair is appended to logs/all_requests.jsonl as a
compact audit trail. Any response that deviates from normal JSON-RPC error
handling (HTTP 5xx, connection drop, timeout > ANOMALY_LATENCY_SECONDS, or a
non-JSON body where JSON was expected) is additionally written as its own
file under logs/anomalies/, paired with the exact payload that triggered it,
plus appended to logs/anomalies.jsonl for quick scanning.
"""
import json
import os
import time
import uuid

import config


def _ensure_dirs():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    os.makedirs(config.ANOMALY_DIR, exist_ok=True)
    os.makedirs(config.REPORT_DIR, exist_ok=True)


class ResultLogger:
    def __init__(self):
        _ensure_dirs()

    def record(self, scenario: str, case: str, payload, result: dict):
        """
        scenario: e.g. "s01_duplicate_keys"
        case: short identifier for the specific sub-case within the scenario
        payload: the exact bytes/str/dict sent (kept verbatim for repro)
        result: dict describing what happened - status_code, elapsed,
                body (truncated), error, is_anomaly, anomaly_reasons, etc.
        """
        _ensure_dirs()
        record = {
            "timestamp": time.time(),
            "scenario": scenario,
            "case": case,
            "payload": _safe_payload(payload),
            "result": result,
        }
        with open(config.ALL_REQUESTS_LOG, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

        if result.get("is_anomaly"):
            anomaly_id = f"{int(time.time())}_{scenario}_{case}_{uuid.uuid4().hex[:8]}"
            anomaly_path = os.path.join(config.ANOMALY_DIR, f"{anomaly_id}.json")
            with open(anomaly_path, "w") as f:
                json.dump(record, f, indent=2, default=str)
            with open(config.ANOMALIES_LOG, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        return record


def _safe_payload(payload):
    """Keep payloads inspectable in JSON logs without ever raising: bytes get
    decoded best-effort, huge payloads get length-noted instead of dumped in
    full so a single deeply-nested/huge case doesn't blow up the log file."""
    try:
        if isinstance(payload, bytes):
            text = payload.decode("utf-8", errors="replace")
        elif isinstance(payload, (dict, list)):
            text = json.dumps(payload)
        else:
            text = str(payload)
    except Exception as exc:  # pragma: no cover - defensive only
        return {"unserializable": True, "error": str(exc)}

    if len(text) > 20000:
        return {
            "truncated": True,
            "original_length": len(text),
            "preview": text[:2000],
        }
    return {"truncated": False, "raw": text}
