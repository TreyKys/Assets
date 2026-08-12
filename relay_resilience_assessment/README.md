# JSON-RPC Relay Resilience Assessment

A Python test harness for authorized resilience/robustness testing of a
locally controlled JSON-RPC relay that translates standard EVM RPC calls to
a non-EVM backend. Covers 10 input-validation and robustness scenarios:
duplicate JSON keys, gas-estimation resource exhaustion, hex/integer
boundary handling, state-cache consistency after reverts, prototype
pollution, ECDSA signature edge cases, null-byte/Unicode handling, deeply
nested arrays, method-name case normalization, and slow HTTP body
transmission (slowloris-style, single connection).

**Scope note:** this is a structural-robustness/logic-flaw test suite, not
a load or denial-of-service tool. It throttles all requests to 10 req/s
(`config.RATE_LIMIT_RPS`) and, for the slow-body scenario, uses exactly one
connection rather than many. Only point it at a relay you own or are
explicitly authorized to test.

## Layout

```
relay_resilience_assessment/
├── config.py              # target URL, headers, rate limit, anomaly thresholds
├── harness/
│   ├── client.py           # HTTP client: sends, times, classifies every request
│   ├── logger.py            # writes logs/all_requests.jsonl + logs/anomalies/*
│   └── rate_limiter.py       # shared 10 req/s token bucket
├── scenarios/
│   ├── s01_duplicate_keys.py
│   ├── s02_gas_estimation_exhaustion.py
│   ├── s03_hex_integer_boundaries.py
│   ├── s04_state_cache_consistency.py
│   ├── s05_prototype_pollution.py
│   ├── s06_ecdsa_signature_edge_cases.py
│   ├── s07_null_byte_unicode.py
│   ├── s08_deeply_nested_arrays.py
│   ├── s09_method_case_normalization.py
│   └── s10_slow_body_transmission.py
├── run_all.py              # runs every scenario, then generates the report
├── generate_report.py       # parses logs/ -> reports/report.md
├── mock_relay/mock_server.py # tiny local fixture used only to self-test the harness
├── logs/                    # created at runtime (git-ignored)
└── reports/                 # report.md generated at runtime (git-ignored)
```

## Setup

```bash
cd relay_resilience_assessment
python3 -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

By default the target is `http://127.0.0.1:7546` (loopback, per the
assessment scope). Override with an environment variable if your relay
listens elsewhere on infrastructure you control:

```bash
export RELAY_TARGET_URL=http://127.0.0.1:7546
```

## Running

Run everything and generate the report:

```bash
python run_all.py
```

Scenario 10 (slow body) defaults to the assessment's reference rate of one
byte every 10 seconds, which takes several minutes for even a tiny payload.
Tune it explicitly, or skip it and run it separately:

```bash
python run_all.py --skip slow_body                     # skip it in the main run
python scenarios/s10_slow_body_transmission.py --delay 10 --max-wait 120
```

Run a single scenario on its own (useful while iterating on one finding):

```bash
python scenarios/s01_duplicate_keys.py
python scenarios/s02_gas_estimation_exhaustion.py
```

Regenerate just the report from whatever is already in `logs/`:

```bash
python generate_report.py
```

## What counts as an "anomaly"

Every request and response is appended to `logs/all_requests.jsonl`. A
response is additionally written to its own file under `logs/anomalies/`
(paired with the exact payload that caused it) and to
`logs/anomalies.jsonl` when any of the following hold:

- HTTP status >= 500
- the connection drops, resets, or is refused
- round-trip time exceeds `config.ANOMALY_LATENCY_SECONDS` (default 10s)
- the body is not valid JSON where JSON was expected

A normal JSON-RPC error object (e.g. `{"error": {"code": -32600, ...}}`)
with a 200/4xx status is expected, correct behavior and is **not** flagged
- the point of this suite is to find where the relay's error handling
*breaks*, not to enumerate its ordinary validation responses.

## Validating the harness itself (no live relay required)

`mock_relay/mock_server.py` is a minimal fixture - not a security target -
that deliberately reproduces a handful of the deviant behaviors above (a
500 on one gas-exhaustion payload, an induced >10s delay, a connection
reset on an oversized nested-array payload, and no read-timeout on a slow
body) so you can confirm the harness's detection and reporting logic before
pointing it at anything real:

```bash
python mock_relay/mock_server.py --port 7546 &
RELAY_TARGET_URL=http://127.0.0.1:7546 python run_all.py --slow-body-delay 0.2 --slow-body-max-wait 15
```

## Known limitations

- **Scenario 4** (state cache consistency) sends structurally representative
  call sequences, but a definitive verdict on stale-cache behavior requires
  pairing it with your actual deployed test contract, since this harness
  has no bytecode of its own to guarantee a real on-chain revert.
- **Scenario 6** (ECDSA edge cases) exercises the relay's *parsing/bounds
  validation* of v/r/s - it does not have a matching private key, so these
  are not cryptographically valid signatures for any real message.
- Both are still useful signal (parser crashes/500s are real either way);
  the report notes this so findings aren't over-claimed.
