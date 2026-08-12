"""
Central configuration for the relay resilience assessment harness.

All values are overridable via environment variables so the same code can be
pointed at different (authorized) targets without editing source files.
"""
import os

# Target JSON-RPC relay. Defaults to the loopback address specified in the
# assessment scope. Override with RELAY_TARGET_URL for another *authorized*
# target (e.g. a staging host you own).
TARGET_URL = os.environ.get("RELAY_TARGET_URL", "http://127.0.0.1:7546")

HEADERS = {"Content-Type": "application/json"}

# Execution constraints per the assessment brief: throttle to 10 req/s and
# do not attempt bandwidth/connection-count saturation.
RATE_LIMIT_RPS = float(os.environ.get("RELAY_RATE_LIMIT_RPS", "10"))

# A response is flagged as an "anomaly" (deviation from normal JSON-RPC
# error handling) when any of the following hold:
#   - HTTP status >= 500
#   - the connection drops / resets / is refused
#   - total round-trip time exceeds ANOMALY_LATENCY_SECONDS
#   - the body is not valid JSON where JSON was expected
#   - the process appears unresponsive to a liveness probe afterward
ANOMALY_LATENCY_SECONDS = float(os.environ.get("RELAY_ANOMALY_LATENCY", "10"))

# Hard cap so a single hung request can't stall the whole suite forever.
# Kept comfortably above ANOMALY_LATENCY_SECONDS so we can actually observe
# and record the >10s condition rather than aborting right at the boundary.
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("RELAY_REQUEST_TIMEOUT", "25"))

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
ANOMALY_DIR = os.path.join(LOG_DIR, "anomalies")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
ALL_REQUESTS_LOG = os.path.join(LOG_DIR, "all_requests.jsonl")
ANOMALIES_LOG = os.path.join(LOG_DIR, "anomalies.jsonl")
