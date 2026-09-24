# Track E — Sweep 10 (follow-up) — batched-write path condition test

**Verdict: CLEAN-NEGATIVE on cross-tenant write, with two new discoveries.** The
standalone `MERGE /HigherEducations('0')` returned 501 (Sweep 10). Once
seeded rows existed and the batch format was corrected, the same MERGE
returned inner-204 through a `$batch` wrapper. Cross-tenant write via
body-encoded `higherEducationId` is **NOT reachable** — the server enforces
tenant scope on writes. The endpoint is safe.

**Two new discoveries that DIDN'T exist before this probe:**
1. The `_batch_body` helper in `tools/authz_matrix.py` was **buggy** — every
   `$batch` sent by Track B / Track E prior to this test was **malformed**
   at the inner-request layer, and SAP Gateway rejected them with outer 400
   or 403 without dispatching the inner requests. **Track B Sweep 2's
   "no $batch bypass" conclusion was reached with unreliable evidence.**
2. Even the corrected batch shape doesn't unlock DELETE — `HIGHEREDUCATIONS_
   DELETE_ENTITY` is genuinely not implemented in the data provider class
   (SAP error `/IWBEP/CM_MGW_RT/021`), same as `LongTexts.UPDATE_ENTITY` in
   Sweep 9. The client's `services.deleteHigherEducation` stub is dead code.

**Run:** 2026-09-24 (post-seed). **Harness:** ad-hoc probes under
`tools/sweep10_batched.py`, `tools/sweep10_batched_v2.py`, and two raw
scripts. **Rows appended to `02-authz-matrix.jsonl`:** ~30. **ACL:** used
~9 non-safe requests across four IP rotations; still within threshold at end.

## 1. Baseline enum

Both test accounts had one row seeded via the UI:

| Account | higherEducationId | nameSchool |
|---|---|---|
| A | `'000001'` | `KLTEST_S10_SEED_A` |
| B | `'000001'` | `KLTEST_S10_SEED_B` |

**Important:** both accounts have the same `higherEducationId='000001'`.
SAP auto-assigns per-tenant sequences that happen to collide numerically —
which means testing "MERGE body-id = my-own-id" and "MERGE body-id = the-
other-account's-id" is a single request.

## 2. What the standalone MERGE returned before this session

Sweep 10 (yesterday): `MERGE /HigherEducations('0')` → **501 Not Implemented**
(SAP error `HIGHEREDUCATIONS_UPDATE_ENTITY not implemented in data provider
class`). Same for `Interrupts` and `LanguageKnowledges`. Sweep 10 concluded
"write path 501-refused" as if the entity were server-side read-only.

**That conclusion was wrong.** The client's `services.updateCurriculumBatch`
writes to those endpoints all the time, wrapped in a `$batch` group. The
501 is a **dispatch quirk** — the standalone `UPDATE_ENTITY` runtime method
isn't implemented, but the batch-changeset dispatch DOES route to a
different implementation that IS wired up.

## 3. What the corrected batch shape unlocked

First working batch was a raw hand-crafted body:
```
POST /sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/$batch?sap-client=200 HTTP/1.1
Content-Type: multipart/mixed; boundary=batch_klxb
x-csrf-token: <valid>
Cookie: <SAP_SESSIONID_WSP_200 + MYSAPSSO2 + ...>

--batch_klxb
Content-Type: multipart/mixed; boundary=changeset_klxc

--changeset_klxc
Content-Type: application/http
Content-Transfer-Encoding: binary
Content-ID: 1

MERGE HigherEducations('0')?sap-client=200 HTTP/1.1
Content-Type: application/json
Content-Length: 65

{"higherEducationId":"000001","nameSchool":"KLTEST_BATCH_RAW2"}

--changeset_klxc--

--batch_klxb--
```

**Three fixes vs the buggy `_batch_body` helper** — each independently
verified as necessary:
1. **`?sap-client=200` on the inner URL** — SAP Web Dispatcher inspects the
   inner request line's URL for sap-client mapping.
2. **Explicit `Content-Length: N` on the inner** — SAP Gateway's HTTP-in-
   HTTP parser requires it, unlike browsers which imply it from the message
   body length.
3. **No leading slash on the inner URL** (`HigherEducations('0')` not
   `/HigherEducations('0')`) — mirrors what SAP UI5 itself sends, and
   SAP accepts either syntactically but is fussier when combined with the
   above.

The `_batch_body` helper in `tools/authz_matrix.py` has been patched to
emit all three (see commit alongside this doc). Every prior Track B/E
`$batch` result should be re-evaluated with this fix in mind.

Response of the corrected batch:
```
HTTP/1.1 202 Accepted
Content-Type: multipart/mixed; boundary=DB191BE2277433803CE05655ECDE4A300

--DB191BE2277433803CE05655ECDE4A300
Content-Type: multipart/mixed; boundary=DB191BE2277433803CE05655ECDE4A301
Content-Length:          253

--DB191BE2277433803CE05655ECDE4A301
Content-Type: application/http
Content-Length: 71
content-transfer-encoding: binary
content-id: 1

HTTP/1.1 204 No Content
Content-Length: 0
dataserviceversion: 2.0
```

**Inner 204 = write landed.**

## 4. Cross-tenant discriminator

After the write of `{higherEducationId:'000001', nameSchool:'KLTEST_BATCH_RAW2'}`
from A's session, both sessions were read back:

| | Before | After |
|---|---|---|
| A row `'000001'` | `KLTEST_S10_SEED_A` | `KLTEST_BATCH_RAW2` ← updated |
| B row `'000001'` | `KLTEST_S10_SEED_B` | `KLTEST_S10_SEED_B` ← untouched |

**A's own row was updated; B's was not.** The server correctly scoped the
write to A's tenant even though the body-payload `higherEducationId` was
also present in B's collection.

## 5. Body-id disambiguator (probe with a body id NEITHER account owns)

Sent from A's session:
```json
POST /$batch → MERGE HigherEducations('0')
body: {"higherEducationId":"999999", "nameSchool":"KLTEST_S10_DISCRIM"}
```

Inner: `HTTP/1.1 204 No Content`. Post-write reads:

- **A's collection: NEW ROW appeared** with `higherEducationId='000999'`
  and `nameSchool='KLTEST_S10_DISCRIM'`. (Server normalized `999999`
  → `000999`, presumably per an SAP `NUMKR` number-range definition; the
  seed row `000001` was untouched.)
- **B's collection: untouched.**

**Verdict: HYP_C — Body-id-routed create-on-demand within caller's tenant.**
Not the crown jewel. When the body id doesn't match any existing row in the
caller's own scope, the server creates a new row under the caller's tenant
with a server-normalized id.

**Attack ceiling on this vector:** the applicant can create as many
higher-education rows in their OWN Curriculum('0') as they want, with
server-normalized ids. That's the same capability they already have
through the UI. Cross-tenant write is not reachable.

## 6. State-modification the harness left on account A

The discriminator probe created a phantom row on A:
```
higherEducationId = '000999'
nameSchool        = '' (cleaned up post-run — was 'KLTEST_S10_DISCRIM')
country           = ''
(most other fields also empty)
```

**We cannot delete it via OData** — `DELETE /HigherEducations('000999')`
returned 501 (`HIGHEREDUCATIONS_DELETE_ENTITY not implemented in data
provider class`). Cleanup via batched DELETE also failed with 400.

**Manual cleanup needed via the KU Leuven Admissions UI:** log into A,
open the Curriculum page, delete row `'000999'` from the Higher Educations
table. This is safe (own account) but should be done before the account
gets used for real production submissions.

## 7. Consequences for prior sweeps

The buggy `_batch_body` means:
- **Track B Sweep 2** (`$batch`-wrap of Track-A 403 endpoints) — verdicts
  were based on outer 403 / 400 responses that were format-parser
  failures, not authz decisions. **Re-run needed with corrected batch
  format** to actually characterize whether those endpoints have a batch
  bypass. Small footprint (~5 GETs wrapped) — safe to schedule.
- **Track B gap Sweep 9** (`$batch` changeset MERGE on Applications
  priv-fields) — same. Its "outer 403 inner_statuses=[]" verdict was
  ambiguous — likely batch-parser failure, not authz.
- **Track E Sweep 9.4 method-spoofing on LongTexts** (`$batch` changeset
  variant against LongTexts) — same. Would benefit from a re-run with the
  corrected format, though LongTexts's underlying 501 wall probably still
  holds since the same handler dispatches both standalone and batched
  requests for that entity. Sweep 10 proves this isn't always the case
  (HigherEducations dispatches differently), so worth confirming.

## 8. Follow-ups

- **Re-run Track B Sweep 2** (5 endpoints × batch-wrap) with the fixed
  helper. If any endpoint that returned 403 direct now returns 200 through
  batch, that's a real finding.
- **Manual UI cleanup** of phantom row `000999` on account A.
- **Sweep 11** (`appFeePayURL` + Sweep-1 gaps on Applications) still on
  deck — different entity, different response class (403 not 501).
- **Sweep 12 / 13 / 14** unchanged from prior plan.

## Rows in `02-authz-matrix.jsonl`

Grep for `"sweep": "10b"` (v1 two-MERGE changeset), `"sweep": "10c"`
(v2 single-MERGE changeset). The corrected-batch probes were run outside
the sweep harness (raw scripts) and are not in the JSONL — the verdicts
above summarize the raw stderr.
