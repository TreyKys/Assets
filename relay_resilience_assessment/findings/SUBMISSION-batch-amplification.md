# Unauthenticated request amplification in JSON-RPC Relay batch-size rejection leads to relay resource exhaustion / service unavailability

**Asset:** JSON RPC Relay (`hiero-ledger/hiero-json-rpc-relay`) — a listed in-scope asset.
**Vulnerable file:** `src/server/koaJsonRpc/index.ts` — `KoaJsonRpc.handleBatchRequest()`
**Reviewed at commit:** `068507991e407b3484cecc21a0ec28fec0af632a` (line present in latest `main`).
**Category:** Algorithmic/amplification resource-exhaustion DoS (not volumetric).
**Severity requested:** Medium — or High if the concurrency test below crashes the service on your representative node (see "Impact / severity").

---

## Summary

The relay enforces a maximum batch size (`BATCH_REQUESTS_MAX_SIZE`, default 100). The **rejection** of an over-limit batch is implemented by building a response array with **one error object per element of the oversized request**:

```ts
if (body.length > this.batchRequestsMaxSize) {
  const responseBody = jsonRespError(null,
    predefined.BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED(body.length, this.batchRequestsMaxSize), requestId);
  ctx.body = Array(body.length).fill(responseBody);   // length = attacker-controlled oversized count
  ctx.status = 200;
  return;
}
```

`body.length` is bounded only by the byte size limit, not by the batch limit. A single well-formed request just under `INPUT_SIZE_LIMIT` (default 1 MB) contains ~524,000 array elements; the relay answers it with ~524,000 serialized error objects (~80× the request). The response is produced by one **synchronous** `JSON.stringify`, which blocks the Node.js single-threaded event loop for the full serialization, stalling all other in-flight requests. The branch executes **before any rate limiting**, and no per-IP HTTP throttle fronts it.

## Steps to reproduce

Tools: `findings/poc_batch_amplification.py` (single-request proof) and `findings/poc_batch_amplification_concurrent.py` (crash/severity test), both stdlib-only.

1. Point at a relay you control: `export RELAY_TARGET_URL=http://127.0.0.1:7546`
2. Single-request proof: `python findings/poc_batch_amplification.py`
3. Severity/crash test (test instance only): `python findings/poc_batch_amplification_concurrent.py --levels 1 2 4 8 16 --relay-pid <relay pid>`

Or minimal manual repro (mechanism, no size-limit confound):
```bash
python3 -c "print('[' + '1,'*4999 + '1]')" > batch.json   # 5000 elements, ~10 KB
curl -s -o resp.json -w 'resp bytes: %{size_download}\n' \
  -X POST -H 'Content-Type: application/json' --data @batch.json http://127.0.0.1:7546
# resp.json is a 5000-element array of "Batch request amount 5000 exceeds max 100" — ~0.75 MB from ~10 KB
```

## Measured results (default config)

Measured against a stock relay (chainId 298 / local node), `INPUT_SIZE_LIMIT=1`, `BATCH_REQUESTS_MAX_SIZE=100`:

| Stage | Request | Response | Factor | Relay busy | Bystander latency |
|---|---|---|---|---|---|
| Mechanism proof | 9.5 KB, 5,000 elems | 0.749 MB | **78×** | 10 ms | — |
| Magnitude + impact | 0.95 MB, 498,073 elems | **75.5 MB** | **79×** | **1,127 ms** | baseline **2.8 ms → 875 ms peak** during the request |

A single ~1 MB request makes the relay allocate ~75 MB and burn ~1.1 s of event-loop time; an unrelated request that normally takes 2.8 ms was frozen for ~877 ms.

**Concurrency test (measured, default config):**

| Concurrency | Requests served | Bystander health/liveness | Observation |
|---|---|---|---|
| 1 | 1/1 OK (1,182 ms) | 3/3 OK | served |
| 2 | 2/2 OK | 5/5 OK | degrading |
| **4** | **0/4 — all failed** | **1/2 OK, 1 FAILED** | relay died mid-response: `IncompleteRead(7.7 MB read, 71 MB more expected)` |
| 8 | 0/8 — all failed | — | `BrokenPipe` (connections reset) in ~10 ms |
| 16 | 0/16 — all failed | — | `BrokenPipe` in ~62 ms |

At **~4 concurrent requests (~4 MB sent once)** the relay stops serving valid traffic *and its own health/liveness endpoint fails* — unrelated clients lose service, not merely experience latency.

**Confirmed process crash (OOM) under concurrency.** The `IncompleteRead` (relay terminating a response mid-stream) corresponds to the Node process being killed. The `json-rpc-relay` container is memory-capped at **768 MiB** (verified via `docker stats`), and each in-flight amplified response is ~75 MB, so a handful of concurrent requests exhausts the cgroup. Kernel log during the concurrency test:

```
node invoked oom-killer: gfp_mask=0x... order=0, oom_score_adj=0
oom-kill:constraint=CONSTRAINT_MEMCG,...,task=node,pid=<pid>,uid=1000
Memory cgroup out of memory: Killed process <pid> (node) total-vm:13821472kB, anon-rss:679396kB...
```

The relay's Node process was OOM-killed by the kernel (container cgroup limit, `CONSTRAINT_MEMCG` — not host exhaustion) and restarted by the container runtime (PID changed across runs). This is a **non-network, unauthenticated service crash** under modest concurrency — the program's explicitly in-scope *"bugs that cause the in-scope service to crash"* impact.

**Scope of the crash claim (measured honestly):** a *single* boosted request (below) does **not** by itself crash a freshly-started relay — it returns a graceful HTTP 500 (the oversized response trips a caught serialization error). The OOM crash was reproduced under **concurrency** (multiple ~75 MB responses in flight against the 768 MiB cap), not from one request.

## Exacerbation: client-controlled Request-Id header multiplies the response size

The per-element error message embeds a request ID that is taken directly from a **client-controlled, unbounded header** and never truncated:

```ts
// src/server/server.ts
const requestId = options.query || options.header || uuid();   // options.header = ctx.get('Request-Id')
// ...reflected into every element by jsonRespError:
//    message: `[Request ID: ${requestId}] Batch request amount ${n} exceeds max ${max}`
```

Because that string is repeated once per element, the attacker controls a per-element multiplier on top of the ~80× structural factor. Projected response size for a ~0.95 MB body (498,073 elements):

| `Request-Id` header | Response size | Factor |
|---|---|---|
| 0 (uuid) | ~74 MB | ~77× |
| **1 KB** | **~560 MB** | **~589×** |
| 4 KB | ~2.0 GB | ~2,125× |
| 16 KB (near Node's default max header) | ~7.9 GB | ~8,269× |

V8's maximum string length is ~512 MB. A single ~1 MB request carrying a **~1 KB** `Request-Id` header drives the projected response past that ceiling, so the serialization hits `RangeError: Invalid string length`. **Measured outcome on the tested node:** the relay catches this and returns a graceful **HTTP 500** (21-byte body) in ~1.9 s — i.e. one request forces the relay to allocate/attempt a ~500 MB serialization and burn ~2 s of event-loop time, but does **not** crash a freshly-started relay by itself. The multiplier's real value is that it drives per-request memory cost from ~75 MB toward the ~500 MB range, which sharply lowers the concurrency needed to reach the 768 MiB cgroup OOM. (Stage C of `poc_batch_amplification.py` reproduces the 500; the concurrency test reproduces the OOM.)

## Impact / severity

- **At minimum (Medium):** unauthenticated, un-throttled, ~80× amplification with a measured near-1-second event-loop stall per request. Sustained at a trivial rate (~1 req/s) it keeps the relay's single event loop saturated, degrading availability for all users. This maps to the program's in-scope Medium impact: *"Increasing network processing node resource consumption by at least 30% without brute force actions."*
- **Confirmed (service crash under concurrency):** each in-flight amplified response costs ~75 MB (more with the Request-Id multiplier). On the tested deployment (768 MiB container cap), a handful of concurrent requests exhausted the memory cgroup and the kernel OOM-killer terminated the Node process, which the container runtime restarted. This is the program's explicitly in-scope impact: *"Bugs that cause the in-scope service to crash (e.g., Non-network-based DoS)"* — reproduced. Note (honest scope): a single request yields a graceful HTTP 500, not a crash; the crash requires modest concurrency against the memory cap.

## Why the standard DoS objections do not apply here

- **"RPC-only, not a network/protocol threat."** The JSON-RPC Relay is a **named in-scope asset** in this program, and "bugs that cause the in-scope service to crash (non-network DoS)" is a **named in-scope impact**. Scope is defined by the program's own asset + impact lists, which this satisfies directly; it does not depend on affecting consensus.
- **"Volumetric / DDoS is out of scope."** This is **not** volumetric. Volumetric DoS needs attacker bandwidth proportional to the damage. Here a single, small, **well-formed** request causes disproportionate server work — an **algorithmic-complexity / amplification** flaw in the application's own logic (~80×, and one ~1 MB request already burns ~1–2 s of event-loop time and forces tens-to-hundreds of MB). The OOM crash is reached with only a handful of concurrent such requests (~4 MB total, once) — orders of magnitude below any bandwidth-flood threshold. The damage comes from the *structure* of the input, not its *volume*.
- **"A WAF / Cloudflare / Nginx would block it."** The payload is **valid JSON of legal size** (`[1,1,…]`, under the app's own 1 MB limit) sent at a trivial rate — nothing a generic WAF signature or rate rule flags. More fundamentally, the relay **implements this batch-size limit itself**; the bug is that its own safety check is written unsafely. Requiring an external appliance to compensate for a defect inside the application's own trust boundary is not a mitigation, and the project ships docker-compose/Helm assets that expose the relay directly. (We acknowledge a body-size limit tuned below 1 MB would reduce the ceiling — but not the mechanism, which triggers on any over-limit batch.)

## Suggested fix

Reject an over-limit batch with a **single** top-level error, never an array sized to the request:

```ts
if (body.length > this.batchRequestsMaxSize) {
  ctx.body = jsonRespError(null,
    predefined.BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED(body.length, this.batchRequestsMaxSize), requestId);
  ctx.status = 200; // or 400
  return;
}
```

Defense-in-depth:
- Cap the parsed **array length** independently of byte size (reject early once element count exceeds the batch limit, before allocating any response).
- **Bound / validate the client-supplied `Request-Id` (and `query`) header length** before reflecting it into responses — a client-controlled string that is echoed per-element must be length-limited (e.g. to a UUID-sized value).
- Add a per-IP HTTP rate limiter covering the pre-dispatch branches.

## Disclosure hygiene

Reported privately via the bug bounty program; not disclosed publicly. No public issue/PR describes this specific behavior as of the reviewed commit, and the vulnerable line is present in the latest `main`.
