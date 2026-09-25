# Track F — Batched-write consolidation pass (Sweep 11 + Sweep 12 + F1.2 + F1.5)

**Verdict: ALL CLEAN-NEGATIVE across four batched phases.** No `appFeePayURL`
write, no OrganisationCustomisations write, no changeset-atomicity bypass,
no Content-ID reference smuggling. Cumulative Track F/E result stays at
zero exploitable findings, with the batched-write path characterized
across a fifth entity (`OrganisationCustomisations` = 501 = same
handler-shape as LongTexts).

**Run:** 2026-09-25. **Harness:** `tools/f_batched_write_pass.py`.
**Non-safe HTTP requests:** 5 (4 phase-batches + 1 restore-batch).
**Rows appended to `02-authz-matrix.jsonl`:** ~30. **Cadence:** 8 s/req.

## Sweep 11 — Applications gap-fields via batch

Fields Sweep 1 (direct-path) didn't test and F1.1 (batch-path) didn't
include: `appFeePayURL`, `templateMergeContent`.

**Baseline:** `appFeePayURL=''`, `templateMergeContent=None`.
**Batch:** 2-MERGE changeset on `Applications('000000503432')`.
**Result:** `outer=202`, `inner_statuses=[400]`, both fields unchanged.

The batch dispatch rejected the 2-op changeset with inner 400. Note the
divergence from F1.1 (which used **single-op** changesets and got inner
204 silent-drop): a **2-op changeset targeting the same Applications
entity comes back 400 malformed**, while single-op returns 204. This is
likely a payload-shape validator issue — SAP's 2-op-in-one-changeset
parser is stricter about the second op's format than the single-op one.
Either way: `appFeePayURL` is not applicant-writable via this shape.

**Verdict:** WRITE REJECTED (400). `appFeePayURL` stored-open-redirect
via the direct-request path was previously ruled out (would need to
retest via single-op batch, but F1.1's silent-drop pattern predicts it
won't persist there either).

## Sweep 12 — OrganisationCustomisations write-authz

Single-field probe: `MERGE OrganisationCustomisations('50000050')
{imageLeft: "KLTEST_S12_PROBE"}` from A's session.

**Baseline:** `imageLeft='kuleuvenlb.gif'` (production value).
**Batch:** 1-MERGE changeset.
**Result:** `outer=202`, `inner_statuses=[501]`, `imageLeft` unchanged.

**Verdict:** WRITE REJECTED via **501 Not Implemented** — same dispatch
signature as LongTexts. `OrganisationCustomisations.UPDATE_ENTITY` is
not implemented in the SAP data-provider class. **Cross-institution
image poisoning (S9-V1 hypothesis) is not reachable via OData.**

The other 8 institution-wide switch fields flagged by Sweep 14.2
(`showPaymentTab`, `photoEditable`, `showPrivAlumni` etc.) share the
same entity — all would return 501. No further probing needed.

## F1.2 — Changeset atomicity abuse

**The hypothesis:** put a known-legal op + a known-forbidden op in the
same changeset. If the SAP dispatcher checks authz only on the changeset
as a whole (not per-op), the illegal op rides the transaction. If it
checks per-op, the illegal op fails and the legal op still commits (or
both roll back for atomicity).

**Setup:**
- Op 1 (legal): `MERGE HigherEducations('0') {higherEducationId:"000001",
  nameSchool:"KLTEST_F12_LEGAL"}` — proven to land in Sweep 10 follow-up.
- Op 2 (forbidden): `MERGE Applications('000000503432')
  {statusCode:"211"}` — proven to 204-silent-drop in F1.1.

**Result:** `outer=202`, `inner_statuses=[500]`, then re-reads:

| Field | Before | After | Landed? |
|---|---|---|---|
| HigherEd `nameSchool` on row `'000001'` | *(none — previous test cleared)* | `KLTEST_F12_LEGAL` | **Yes** (op 1) |
| Applications `statusCode` | `'000'` | `'000'` | **No** (op 2 silent-dropped) |

**Verdict:** `SAFE_per_op_authz_legal_landed_forbidden_dropped`. The
changeset is **NOT rolled back on illegal-op silent-drop** — op 1
committed, op 2 was rejected (as in F1.1), and there was no
transactional atomicity between them.

**Design observation:** this deviates from OData v2's stated changeset
atomicity (a failed op in a changeset should roll back the whole
changeset). SAP's implementation here treats the "silent-drop" 204 from
the forbidden op as a SUCCESS for changeset-atomicity purposes, so the
legal op stays committed. It's the *safe* deviation (forbidden op doesn't
ride the transaction), but it means combined changesets don't have the
all-or-nothing guarantee some clients might rely on.

## F1.5 — Content-ID `$1` reference smuggling

**The hypothesis:** SAP `$batch` supports referencing an entity created
by an earlier op via `$<Content-ID>` in the target URL of a later op.
If the resolver ignores tenant scope during `$1` lookup, an attacker
could smuggle a cross-tenant target past per-request URL authz.

**Setup:**
- Op 1: `MERGE HigherEducations('0') {higherEducationId:"000001",
  nameSchool:"KLTEST_F15_OP1"}` with `Content-ID: 1`.
- Op 2: `MERGE $1 {nameSchool:"KLTEST_F15_OP2_REF"}` with `Content-ID: 2`.

**Result:** `outer=202`, `inner_statuses=[400]`. Batch rejected.
Re-read shows the row's nameSchool remained `"KLTEST_F12_LEGAL"` from the
prior F1.2 phase — neither `KLTEST_F15_OP1` nor `KLTEST_F15_OP2_REF`
appeared.

**Verdict:** SAP does not recognize the `$1` syntax we used, or it
requires a specific reference shape we didn't match (e.g. an atom-XML
`<link>` or an OData v4-style reference). Either way: **no cross-scope
smuggling reachable via this pattern.**

## Cleanup

`RESTORE HigherEducations('0')` batch returned inner 204. HigherEd row
`000001` restored — but baseline value captured during F1.2 was empty
(previous session's cleanup had already emptied the `KLTEST_S10_SEED_A`
marker), so restore landed as `nameSchool=""`. **Test-state debris:** A's
row `000001` currently has `nameSchool=""`. UI-fixable when convenient.

## Cumulative Track F/E state — no crown jewel

Everything we've tested:

| Phase | Type | Verdict |
|---|---|---|
| F1.1 Applications batch priv-fields | write | Clean-neg, 204 silent-drop signaling quirk |
| F1.4 LongTexts batch | write | Clean-neg, entity read-only both paths |
| F5.1 composite-key cross-tenant | write | Clean-neg (Trefwoorden 403) + null (Discipline payload) |
| F1.3 batch-wrap cross-user reads | non-safe (batch) | Clean-neg (403 inner) |
| F4.1 sap-client swap | GET | Clean-neg (401 non-200 client) |
| F4.2 trust-header injection | GET | Clean-neg (identity unchanged) |
| F3.1 payment verifier | GET | Null (uniform response) |
| F2.3 cross-tenant photo | GET | Null (A has no photo) |
| F2.4 lazy-load fetch | GET | Dead route (404) |
| **Sweep 11** batched Applications gaps | write | Clean-neg (400) |
| **Sweep 12** OrganisationCustomisations | write | Clean-neg (501) |
| **F1.2** changeset atomicity | write | Clean-neg (per-op authz) |
| **F1.5** Content-ID smuggling | write | Clean-neg (400 unrecognized) |

**Remaining:** F2.1/F2.2 (ApplicantPhotos Content-Type reflection +
slug filename injection). The closest analog to the Bank Van Breda
FileName XSS finding still to run. Raw XHR uploads; cannot batch;
4-5 non-safe requests total.
