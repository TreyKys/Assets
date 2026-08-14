# Outreach drafts for FINDING-001 (private disclosure, no fee)

Use ONE of these as your first message. Never paste the technical body into a
Discord channel, even a "security" one — DM only, after confirming you're
talking to a verified team member, or use GitHub/email directly.

---

## 1. Discord — first message to a verified team member (DM only)

Use this to *open the door*. No technical detail yet.

> Hi — I'm a security researcher and I found what looks like a reproducible
> denial-of-service vulnerability in the JSON-RPC Relay (hiero-json-rpc-relay).
> I have it fully documented with a proof-of-concept and a one-line fix, and
> I'd like to report it responsibly and privately. Could you point me to the
> right person or process for that? Happy to share full details via GitHub
> Security Advisory, email, or however your team prefers.

If they ask "just tell me here" — politely decline and ask for a private
channel (DM, email, or the GitHub advisory) instead, since it's a live,
unpatched issue.

---

## 2. GitHub Security Advisory (repo: hiero-ledger/hiero-json-rpc-relay)

Path: repo → Security tab → "Report a vulnerability" (if enabled), or open
a private security advisory. This is the best default — it goes straight to
maintainers, is private by design, and timestamps your report.

**Title:**
Unauthenticated single request crashes the relay via batch-rejection response amplification (OOM)

**Body:**

> ## Summary
> A single unauthenticated HTTP request can crash the JSON-RPC Relay process.
> The relay's oversized-batch rejection builds a response with one error
> element per element of the *rejected* request
> (`Array(body.length).fill(responseBody)` in
> `src/server/koaJsonRpc/index.ts`), so a small request produces a
> disproportionately large response (~80x). The response also reflects the
> client-controlled `Request-Id` header once per element with no length
> bound, letting an attacker tune the response size. In the ~400-950 byte
> `Request-Id` range, the response lands just under V8's ~512MB max string
> length, so the string *is* built and then copied to a socket buffer —
> transiently doubling memory and exceeding a memory-capped deployment's
> limit.
>
> ## Impact
> Confirmed via kernel log: six distinct OOM kills of the relay's Node
> process, one per crafted request, on a relay container capped at 768MiB
> (`docker stats`). Each request is ~1MB, well-formed JSON, unauthenticated,
> and no concurrency is required. Repeated every few seconds this is a
> sustained crash-loop, taking the relay offline for all clients.
>
> ## Reproduction
> Attached: two PoC scripts (stdlib-only Python) —
> `poc_batch_amplification.py` (confirms the amplification mechanism) and
> `poc_single_request_crash_sweep.py` (sweeps Request-Id header size across
> the crash window and confirms the OOM). Both were run against a local
> Hedera node instance I control. I'm happy to walk through the exact
> commands and kernel log output.
>
> ## Suggested fix
> Reject an over-limit batch with a single top-level error object instead of
> an array sized to the request:
> ```ts
> if (body.length > this.batchRequestsMaxSize) {
>   ctx.body = jsonRespError(null, predefined.BATCH_REQUESTS_AMOUNT_MAX_EXCEEDED(body.length, this.batchRequestsMaxSize), requestId);
>   ctx.status = 200; // or 400
>   return;
> }
> ```
> Also worth bounding the length of the `Request-Id`/`query` header before
> it's reflected into any response, and capping parsed batch array length
> independently of byte size.
>
> ## Disclosure
> I'm reporting this privately, only here, and haven't shared any technical
> detail anywhere else — including Discord, where I've noticed a few other
> researchers this week discussing findings more openly than they probably
> should, likely because the Immunefi Novice submission fee ($100) is a real
> barrier for independent researchers. I get why the fee exists, but I think
> it's actively pushing people toward less responsible disclosure than the
> program wants — I chose to hold this privately and come straight to you
> instead. If there's a way to recognize that — through the Immunefi program,
> a discretionary reward, or a fee waiver for this report — I'd genuinely
> appreciate it. No obligation either way; I wanted this fixed regardless,
> and I'm glad to keep helping on future findings if that's useful to you.

---

## 3. Email to a security@ / bug-bounty contact

Same content as #2, formatted as a normal email, with a clear subject line:

**Subject:** Security report — unauthenticated crash in hiero-json-rpc-relay (private disclosure)

Open with 1-2 lines identifying yourself and the ask (private disclosure,
not a public post), then paste the body from #2 above, then close with:

> Let me know the best way to share the full PoC and logs — happy to do a
> call/screen-share to walk through it if that's easier.
