# Track H.1 — `Applications.programDescription` → `HtmlMenu.openBy` innerHTML sink — confirmation result

**Verdict: NOT WRITABLE — entity-level read-only state — candidate open with caveats**

## TL;DR

Account A's `Applications` entity is in a **non-editable lifecycle state**: every
MERGE (batched and direct, real-key and self-alias) returns 204 "success" but
silently drops ALL field writes — including a **control field** (`additionalremarks`)
that is ordinarily applicant-writable during the application-editing phase. The
Applications collection lists 0 rows for account A, and the entity returns a blank
template (`applicationId=""`, `institution="00000000"`).

This means we **cannot conclusively test** whether `programDescription` is
field-level filtered or not — the entire entity is read-only. The question remains
open: **if an applicant's application were in an active/editable state, would
`programDescription` accept and persist raw HTML?** We could not reach that state
from OData (CREATE-path also rejected), and the test accounts have no active
application in the current workflow.

The `HtmlMenu.js` `t.innerHTML = l` sink is real, and the
`CommunicationMenu.fragment.xml` binding chain is confirmed. The only missing
piece is a writable source.

## Session validation

| Check | Result |
|---|---|
| CSRF fetch | Token obtained (`uF6ykLo_WLJm...`) |
| `GET Applicants('0')` | 200, `inAccountId='IN01051619'` — **correct identity** |
| `GET Applications('000000503432')` | 200, but `applicationId=""`, `institution="00000000"` — **blank template** |
| `GET Applications('0')` | 200, same blank template |
| `GET Applications` (collection) | 200, `results: []` — **0 rows** |

The session is alive and bound to account A's identity. But account A has no
active/editable application record. The `Applications('000000503432')` endpoint
returns a SAP default-value entity rather than a 404 — a common SAP OData pattern
for entities that existed but are no longer in the current scope (academic year
rollover, submission finalization, etc.).

## Control test — `additionalremarks` (should be writable)

`additionalremarks` is a free-text field that the SAPUI5 client writes during the
normal application-editing flow (via `MERGE /Applications('<id>')`). It was chosen
as a control to distinguish between field-level filtering (only `programDescription`
is blocked) and entity-level read-only (no fields writable).

| Path | Method | Status | Readback | Written? |
|---|---|---|---|---|
| `Applications('000000503432')` | batched MERGE | outer 202 / inner 204 | `""` (unchanged) | **No** |
| `Applications('000000503432')` | direct MERGE | 204 | `""` (unchanged) | **No** |

**Both control writes silently dropped.** This proves the entity is in a read-only
state — not a field-specific filter on `programDescription`.

## Primary test — `programDescription`

| Path | Method | Status | Readback | Written? |
|---|---|---|---|---|
| `Applications('000000503432')` (real key) | batched MERGE | outer 202 / inner 204 | `""` (unchanged) | **No** |
| `Applications('0')` (self-alias) | batched MERGE | outer 202 / inner 204 | `""` (unchanged) | **No** |
| `Applications('000000503432')` | direct MERGE | 204 | `""` (unchanged) | **No** |

All three paths: 204 + silent-drop. Consistent with the control test (entity-level,
not field-level).

## HTML probes (Step 2)

**Skipped** — gated on Step 1 writability per the brief. Since the inert marker
didn't persist on any path, there's no point testing HTML shapes.

## CREATE-path probe

| Step | Result |
|---|---|
| `Applications` list before | 0 rows |
| `MERGE Applications('0')` with `{"programDescription": "KLXSSPD_CREATE_2"}` | outer 202 / inner 204 |
| `Applications` list after | 0 rows |
| Verdict | **CREATE_REJECTED** — no new record created |

The CREATE self-alias (`Applications('0')`) doesn't create a new application record
via OData MERGE. The client-side `ApplicationNew` flow likely uses a different
mechanism (FunctionImport or specific workflow trigger) to initialize a new
application.

## Restore + cleanup

| Field | Baseline | After restore | Verified? |
|---|---|---|---|
| `programDescription` | `""` | `""` | **Yes** (`cleanup_ok=True`) |
| `additionalremarks` | `""` | `""` | **Yes** (`cleanup_ok=True`) |

No net change to account A's data — all writes were silently dropped, so restore
was a no-op verified by readback.

## Analysis: why the candidate stays open

The first run (pre-rerun) concluded "NOT WRITABLE (silent-drop)" and closed the
candidate. The rerun adds critical nuance:

1. **The silent-drop is entity-level, not field-level.** Every field — including
   the control field `additionalremarks` — gets the same treatment. This is a
   lifecycle/state guard, not a `programDescription`-specific filter.

2. **The entity is in a non-editable state.** Account A has no active application
   in the current scope. The blank-template response (`applicationId=""`) confirms
   this. An application in the `editing` lifecycle phase (before submission) would
   likely accept MERGE writes on applicant-owned fields — that's how the SAPUI5
   client saves application data.

3. **We cannot reach the editable state from OData.** The CREATE-path is rejected,
   and we can't change the application's lifecycle state. To test the real question
   (does `programDescription` persist raw HTML during active editing?), a researcher
   would need to:
   - Create a new application through the SAPUI5 UI (the ApplicationNew flow)
   - Before submitting, attempt the MERGE write on `programDescription`
   - This is a manual browser-side test, not automatable from this harness

4. **The sink is real and confirmed.** `control/HtmlMenu.js` line with
   `t.innerHTML = l` is a genuine innerHTML assignment. The binding chain
   (`programDescription` → `CommunicationMenu.fragment.xml` MenuItem `text=` →
   `HtmlMenu.openBy()` → `innerHTML`) is confirmed by static analysis.

## Verdict classification

| Aspect | Status |
|---|---|
| Is the innerHTML sink real? | **Yes** — `HtmlMenu.js`, `t.innerHTML = l` |
| Is the binding chain confirmed? | **Yes** — `programDescription` → MenuItem text → innerHTML |
| Is `programDescription` field-level filtered? | **Inconclusive** — entity is read-only, masking any field-level behavior |
| Is the entity writable at all? | **No** — lifecycle state prevents all writes |
| Can we reach an editable state from OData? | **No** — CREATE rejected |
| Overall H.1 candidate status | **Open / inconclusive** — needs active-application test |

## Recommended next step (manual, for researcher)

1. Log into the SAPUI5 app as account A (or B)
2. Start a new application via the ApplicationNew flow (the UI's "Create Application" button)
3. Before submitting, use browser DevTools or a proxy to capture the `MERGE /Applications('<new_id>')` request
4. Modify the request body to include `"programDescription": "KLXSSPD_TEST"` (inert marker)
5. If the MERGE persists the value: repeat with `"<b>KLXSSPD_B</b>"` (non-executing HTML)
6. If stored raw: the chain is live — `programDescription` → MenuItem text → `HtmlMenu.innerHTML` = stored DOM-XSS
7. **Immediately restore** the field to its original value

The key difference: during active editing, the Applications entity accepts MERGE writes
on applicant-owned fields. The question is whether `programDescription` is in that set,
and if so, whether it's sanitized before storage.

## Evidence files

| File | Contents |
|---|---|
| `07-track-h1-evidence/rerun_baseline_real.json` | Baseline entity fields (real key) |
| `07-track-h1-evidence/rerun_baseline_self.json` | Baseline entity fields (self-alias) |
| `07-track-h1-evidence/rerun_results.json` | Full probe results (all paths) |
| `07-track-h1-evidence/baseline_application.json` | First-run baseline (full entity) |

## Run metadata

- **Date:** 2026-09-28
- **Harness:** `tools/track_h1_rerun.py`
- **Non-safe requests:** 7 (3 batched MERGE via $batch POST + 3 direct MERGE + 1 restore MERGE)
- **Safe requests:** 11 GETs (CSRF + identity + baselines + readbacks + list-before/after + restore-verify)
- **Cadence:** 8 s/req
- **ACL impact:** minimal (well under threshold)
- **Net data change:** none (all writes silently dropped; restore verified)
