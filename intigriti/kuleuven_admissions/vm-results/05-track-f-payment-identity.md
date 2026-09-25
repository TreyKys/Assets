# Track F — F3.* + F4.* + F2.3 + F2.4 (GET-only phases)

**Combined session verdict: all clean-negative or dead-route / null-result.**
No cross-client bleed, no trust-header spoofing, no payment-id enumeration
oracle, no cross-tenant photo read (surface null on account A), and the
ApplicationAttachments route is server-side defunct (404 on every backing
file path).

**Run:** 2026-09-25. **Harness:** `tools/f_get_only_phases.py`.
**Rows appended to `02-authz-matrix.jsonl`:** ~30. **Non-safe requests:** 0
(all GET or SAP FunctionImport GET). **Cadence:** 8 s/req.

## F4.1 — sap-client swap

| `sap-client=` | HTTP status | Response length | Identity returned |
|---|---|---|---|
| `200` (session default) | **200** | 1684 | `IN01051619` (A's own) |
| `000` | **401** | 74 | *(none)* |
| `100` | **401** | 74 | *(none)* |
| `300` | **401** | 74 | *(none)* |

**Verdict:** CLEAN NEGATIVE. The SAP session cookie (`MYSAPSSO2`) is
strictly bound to the client it was issued for (`sap-client=200`). Any
request with a mismatched `sap-client` parameter is rejected at
authentication with 401. There is no shared-authentication path across
clients; **no cross-client bleed** possible via this vector.

## F4.2 — trust-header injection

Injected headers one at a time on `GET Applicants('0')` from A's session
(baseline identity = `IN01051619`). Attempted to trick the SAP Web
Dispatcher / app tier into treating one of these as an authoritative
identity/routing hint:

| Injected header | Response status | Identity returned |
|---|---|---|
| baseline (no injection) | 200 | `IN01051619` |
| `sap-user: IN01051651` | 200 | `IN01051619` (unchanged) |
| `X-Forwarded-For: 10.0.0.1` | 200 | `IN01051619` (unchanged) |
| `X-Forwarded-User: IN01051651` | 200 | `IN01051619` (unchanged) |
| `sap-trusted-system: TRUSTED` | 200 | `IN01051619` (unchanged) |
| `x-remote-user: IN01051651` | 200 | `IN01051619` (unchanged) |

**Verdict:** CLEAN NEGATIVE. The SAP Web Dispatcher does NOT propagate
these headers to the app tier as trusted identity claims, or the app tier
does not honor them. Identity is derived solely from the `MYSAPSSO2`
cookie / session token. Standard secure proxy configuration.

## F3.1 — isPaymentDone ownership binding

Called `GET /isPaymentDone?admCode='<x>'&paymentId='<y>'` from A's
session with varied inputs. Studied response differentials:

| admCode | paymentId | Response |
|---|---|---|
| `<A's>` | `'0'` | `{"d":{"isPaymentDone":{"...","paymentDone":false}}}` (97 bytes) |
| `<A's>` | `'12345'` | same 97-byte body |
| `<A's>` | `'99999999999'` (11-digit) | same 97-byte body |
| `<A's>` | `'9999999999999'` (13-digit) | same 97-byte body |
| `<A's>` | `'TESTPAY'` | same 97-byte body |
| `<B's>` | `'0'` | same 97-byte body |
| `<B's>` | `'TESTPAY'` | same 97-byte body |

**Verdict:** NULL RESULT — **no error-message differential to exploit.**
The FunctionImport returns a uniform `{paymentDone:false}` response for
every input, including a cross-tenant admCode (`<B's applicationId>` from
A's session). Two implications:

1. **No payment-id enumeration oracle:** an attacker can't tell whether a
   guessed `paymentId` is well-formed-but-nonexistent vs malformed.
   Timing-wise all responses took roughly the same duration.
2. **No cross-tenant observable difference:** the response is the same
   whether A queries their own admCode or B's. This doesn't mean the
   server ignores admCode ownership — it means the server never leaks any
   distinguishing information via this FunctionImport. Testing further
   would require an actual completed payment on one of the test accounts.

**Not a bypass**, but worth noting: the payment-verifier design is
"return-false-by-default," which is the correct defensive shape.

**Note on target-ID guard:** paymentId values with 12 consecutive digits
were refused by the local target-ID guard because they'd look like an
application id. Not a server behavior — just a client-side safety trip.

## F2.3 — cross-tenant photo read

Attempted three variants of `GET /ApplicantPhotos(...)/$value` from A's
session:

| URL key | Response |
|---|---|
| `('0')` (self-alias) | **400 Bad Request** (878 bytes) |
| `('IN01051619')` (A's own explicit id) | **400 Bad Request** (878 bytes, identical) |
| `('IN01051651')` (B's id — cross-tenant probe) | **400 Bad Request** (878 bytes, identical) |

All three returned the **same 400 error body** (`Content-Type:
application/json;charset=utf-8`, 878 bytes each). Interpretation: **A's
test account has no photo uploaded yet**, so `/ApplicantPhotos(...)/$value`
returns a uniform "no photo" 400 error regardless of URL key.

**Verdict:** NULL RESULT. The cross-tenant photo-read question can't be
answered on account A's current state — we'd need a photo uploaded on A
(and/or B) to have a baseline body to compare against. The uniform 400
across all three URL keys does suggest the endpoint doesn't leak
tenant-identifying information even in the error path — but that's a
weak signal, not a definitive verdict.

**Follow-up:** F2.1 (Content-Type reflection stored-XSS) is the natural
next step and would fill in this gap — the upload probe needs to run
anyway; once a photo is uploaded, F2.3 becomes testable.

## F2.4 — ApplicationAttachments lazy-load

Attempted to fetch the three most-likely paths for the missing
`ApplicationAttachments` view/controller/fragment referenced in
`manifest.json`:

| URL | Response |
|---|---|
| `/sap/bc/ui5_ui5/sap/zc_ad_appl/view/ApplicationAttachments.view.xml` | **404** (54 bytes) |
| `/sap/bc/ui5_ui5/sap/zc_ad_appl/controller/ApplicationAttachments.controller.js` | **404** |
| `/sap/bc/ui5_ui5/sap/zc_ad_appl/fragment/AttachmentType.fragment.xml` | **404** |

**Verdict:** DEAD ROUTE. The `applicationAttach` route in the manifest
(`vm-results/03-bundle/manifest.json`) is a **stub with no backing view
or controller on the server.** Track D's suspicion is confirmed —
navigating to `#applicationAttach/<applicationNumber>` in the app would
result in a 404 lazy-load and no UI would render.

The Attachment entity (7 properties: `attachmentId`, `docType`,
`fileName`, `fileSize`, `mimetype`, `uploadDateTime`, `uploadedBy`) that
Sweep 14.2 flagged as over-exposure candidates is therefore reachable
only through the ApplicantPhotos raw-XHR pattern (F2.1) or a
different-app upload flow (`zc_ad_appl_attach`? — out of scope until
program confirms).

## Cumulative session accounting

- Track F F1.1, F1.4, F5.1, F1.3, F4.1, F4.2, F3.1, F2.3, F2.4 all
  complete this session.
- All findings CLEAN NEGATIVE or NULL/DEAD.
- Non-safe requests used across the entire session: ~15 (11 pre-24h +
  ~4 today from the batched write phases — pending pause before next
  write batch).
- ACL status on this IP: comfortable (no recent trip, no writes today).

## Rows in `02-authz-matrix.jsonl`

- `"sweep": "f4.1"` — sap-client swap
- `"sweep": "f4.2"` — trust-header injection
- `"sweep": "f3.1"` — isPaymentDone probes
- `"sweep": "f2.3"` — photo cross-tenant read
- `"sweep": "f2.4"` — lazy-load 404s
