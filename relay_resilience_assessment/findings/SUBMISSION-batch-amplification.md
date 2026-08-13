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

A single ~1 MB request makes the relay allocate ~75 MB and burn ~1.1 s of event-loop time; an unrelated request that normally takes 2.8 ms was frozen for ~875 ms. `< PASTE YOUR CONCURRENCY-TEST SUMMARY HERE — especially the concurrency at which health/liveness stops responding and the peak RSS. >`

## Impact / severity

- **At minimum (Medium):** unauthenticated, un-throttled, ~80× amplification with a measured near-1-second event-loop stall per request. Sustained at a trivial rate (~1 req/s) it keeps the relay's single event loop saturated, degrading availability for all users. This maps to the program's in-scope Medium impact: *"Increasing network processing node resource consumption by at least 30% without brute force actions."*
- **Potentially higher (service crash):** each in-flight request costs ~75 MB. On a memory-capped deployment (typical relay pods run 512 MB–1 GB), a small number of concurrent requests exhausts memory → Node OOM / container OOM-kill / restart loop. That is the program's explicitly in-scope impact: *"Bugs that cause the in-scope service to crash (e.g., Non-network-based DoS)."* The concurrency test measures whether this reproduces on your node; report it as a crash only if it actually does.

## Why the standard DoS objections do not apply here

- **"RPC-only, not a network/protocol threat."** The JSON-RPC Relay is a **named in-scope asset** in this program, and "bugs that cause the in-scope service to crash (non-network DoS)" is a **named in-scope impact**. Scope is defined by the program's own asset + impact lists, which this satisfies directly; it does not depend on affecting consensus.
- **"Volumetric / DDoS is out of scope."** This is **not** volumetric. Volumetric DoS needs attacker bandwidth proportional to the damage. Here a single, small, **well-formed** request (< 1 MB, at ~1 req/s) causes ~80× disproportionate server work — an **algorithmic-complexity / amplification** flaw in the application's own logic. The damage comes from the *structure* of the input, not its *volume*. The amplification factor and the single-request event-loop stall are the evidence that volume is not the mechanism.
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

Defense-in-depth: also cap the parsed **array length** independently of byte size (reject early once element count exceeds the batch limit, before allocating any response), and add a per-IP HTTP rate limiter covering the pre-dispatch branches.

## Disclosure hygiene

Reported privately via the bug bounty program; not disclosed publicly. No public issue/PR describes this specific behavior as of the reviewed commit, and the vulnerable line is present in the latest `main`.
