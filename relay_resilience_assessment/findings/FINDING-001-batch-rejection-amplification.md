# FINDING-001 — Oversized-batch rejection amplifies a 1 MB request into an ~80 MB response (un-rate-limited event-loop-blocking DoS)

- **Component:** `hiero-json-rpc-relay` — HTTP JSON-RPC server (`KoaJsonRpc`)
- **Affected code:** `src/server/koaJsonRpc/index.ts`, `handleBatchRequest()` (the `body.length > batchRequestsMaxSize` branch)
- **Type:** Non-network-based / resource-amplification DoS (structural logic flaw, not bandwidth flooding)
- **Preconditions:** default configuration only (no non-default settings required)
- **Severity (honest):** **Low–Medium**, pending empirical confirmation on a representative node. Rationale for the ceiling: the effect is a *transient* resource spike; the relay recovers when the flood stops (no persistent state corruption, no fund loss, no consensus impact). Rationale it is not merely informational: it is unauthenticated, un-rate-limited, ~80× amplification, and blocks the single-threaded event loop — so it plausibly meets the program's Medium bar ("increasing processing-node resource consumption by ≥30% without brute-force actions"). The measurement PoC decides where in Low–Medium it lands.
- **Status:** Code-path confirmed by source review. **NOT yet empirically confirmed** against a live node (the analysis container cannot reach the target). Run `poc_batch_amplification.py` against your own instance before treating this as validated or submitting it.

---

## Root cause

`handleBatchRequest` rejects batches larger than `BATCH_REQUESTS_MAX_SIZE`. The rejection itself is the bug: it builds a response array whose length equals the **attacker-controlled, oversized** element count of the request it is rejecting.

```ts
// src/server/koaJsonRpc/index.ts  (handleBatchRequest)
if (body.length > this.batchRequestsMaxSize) {
  const responseBody = jsonRespError(
    null,
    predefined.BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED(body.length, this.batchRequestsMaxSize),
    requestId,
  );
  ctx.body = Array(body.length).fill(responseBody); // <-- length == oversized request's element count
  ctx.status = 200;
  ctx.state.status = `${ctx.status} (${INVALID_REQUEST})`;
  return;
}
```

The `.fill(responseBody)` shares a single object by reference (an intentional micro-optimization, per the inline comment), so the *array* holds only ~`body.length` pointers. But when Koa serializes `ctx.body` for the HTTP response, `JSON.stringify` walks all `body.length` elements and emits a **full copy** of the ~158-byte error object for each. The de-duplication never reaches the wire.

## Two properties that make it exploitable

1. **The amplification scales with element count, and element count is only bounded by the byte limit.**
   The request body limit is `INPUT_SIZE_LIMIT` (default **1 MB**, `src/config-service/services/globalConfig.ts`). A body of `[1,1,1,…,1]` costs ~2 bytes per element, so 1 MB parses to **~524,288 elements**. Each serialized response element is ~158 bytes → response ≈ **79.5 MB**. Measured factor: **~80×**.
   If an operator raises `INPUT_SIZE_LIMIT` (e.g. for `JUMBO_TX_ENABLED`), the response grows linearly — a 16 MB limit yields an ~1.3 GB response (guaranteed OOM).

2. **This branch runs before any rate limiting.**
   The only rate limiter (`IPRateLimiterService.shouldRateLimit`) is invoked inside `getRequestResult` (`src/server/koaJsonRpc/index.ts`), which is reached only for *valid* single/batch sub-requests. The oversized-batch branch `return`s earlier. The Koa middleware chain in `src/server/server.ts` (CORS, timing, health, metrics, request-id, then `rpcApp`) contains **no HTTP-level per-IP rate limiter**. So the amplification path has no throttle in front of it.

## Impact

Each request forces the relay to:
- allocate the parsed input array (~524k numbers),
- allocate the ~524k-pointer response array, and
- **synchronously** build an ~80 MB string in one `JSON.stringify` call.

`JSON.stringify` is synchronous and blocks Node's single event-loop thread for the whole serialization. During that window, every other in-flight request on the process stalls. Repeated at a low rate (this is structural amplification, not bandwidth flooding — a few such 1 MB requests per second), this produces sustained GC/memory pressure and event-loop stalls: elevated latency for all users and, on a memory-constrained pod, OOM.

Default `BATCH_REQUESTS_ENABLED = true` and `BATCH_REQUESTS_MAX_SIZE = 100` mean stock deployments are affected.

## Reproduction (measure on your own instance)

`poc_batch_amplification.py` (same directory) sends **one** crafted 1 MB request and, concurrently, a stream of trivial `eth_chainId` probes, then reports:
- response size and amplification factor actually returned by the node,
- wall-clock time the relay took to answer the amplified request,
- the latency inflation of the concurrent probes during that window (the event-loop-blocking signal).

Run it only against a relay you operate:

```bash
RELAY_TARGET_URL=http://127.0.0.1:7546 python findings/poc_batch_amplification.py
```

A material amplification factor (≈80× at a 1 MB limit) plus a visible probe-latency spike confirms the finding. If the probes are unaffected and memory is flat, downgrade accordingly and do not submit.

## Suggested fix

Reject oversized batches with a **single** error object, not one per element:

```ts
if (body.length > this.batchRequestsMaxSize) {
  ctx.body = jsonRespError(null, predefined.BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED(body.length, this.batchRequestsMaxSize), requestId);
  ctx.status = 200; // or 400
  return;
}
```

Per JSON-RPC 2.0, a batch that violates a server limit may be answered with a single top-level error; a same-length array of identical errors is not required. Optionally also cap parsed array length independently of byte size, and/or add an HTTP-level per-IP rate limiter covering the pre-dispatch branches.

## Honest limitations / before submitting

- **Not empirically confirmed from the analysis environment** — the sandbox cannot reach `:7546`. The 80× figure is computed from the code and the default limits; confirm the real factor and the latency/memory impact with the PoC on your node.
- **Severity is transient/recoverable** — argue Medium at most; do not inflate to High/Critical.
- **Duplicate check required** — search the repo's issues/PRs and the bounty program's known-issues for "batch" / "amplification" / this file before submitting. Amplification-on-rejection is a known *class*; confirm this specific instance isn't already reported or fixed on a newer commit than the reviewed HEAD (`068507991e40…`, 2026-08-11).
