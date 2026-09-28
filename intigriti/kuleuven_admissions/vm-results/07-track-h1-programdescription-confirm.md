# Track H.1 — `Applications.programDescription` → `HtmlMenu.openBy` innerHTML sink — confirmation result

**Verdict: NOT WRITABLE (silent-drop) — closed**

`programDescription` rejects applicant-supplied writes via OData MERGE. The write is
acknowledged at the transport layer (inner batch status 204, i.e. "success") but the stored
value never changes — a silent-drop, matching the F1.1 pattern already seen in prior sweeps.
Since the field isn't writable at all, the HTML-storage question (raw vs. encoded vs. stripped)
never arises, and the `HtmlMenu.js` `t.innerHTML = l` sink — while real — has no reachable
applicant-controlled path through this field. Candidate closed at Track H.

## Scope + method

- Endpoint: `webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/Applications('000000503432')`
- Account: A only (`000000503432`)
- Path: batched MERGE (`$batch` → single-op changeset), matching the app's own
  `services.insertApplication` write path (`setUseBatch(true)`)
- All probe payloads were non-executing by design (inert marker, then `<b>`/`<img>` without
  handlers) — moot here since Step 1 already showed the field non-writable, so Step 2 (the HTML
  probes) was correctly never run per the brief's own gating logic.

## Probe → readback table

| Step | Payload sent | Outer/inner batch status | Readback value | Classification |
|---|---|---|---|---|
| 0 — Baseline | (read only) | 200 | `""` (empty) | baseline captured |
| 1 — Inert marker | `programDescription = "KLXSSPD_INERT_1"` | outer 202 / inner 204 | `""` (unchanged) | **not written — silent-drop** |
| 2a — `<b>` (non-executing) | *not run* | — | — | skipped (gated on Step 1 writability) |
| 2b — `<img src=x>` (no handler) | *not run* | — | — | skipped (gated on Step 1 writability) |

Inner status 204 with an unchanged readback is the same silent-filter behavior documented
elsewhere in this engagement (Sweep 1 priv-fields, F1.1) — the server accepts the batch
sub-request but discards the field write server-side rather than rejecting it (no 400/403).

## Baseline + cleanup

- Baseline `programDescription`: `""` (empty at time of test — account A had not set a program
  description).
- Restore MERGE issued anyway as a matter of process (`programDescription = ""`, i.e. re-asserting
  the baseline): outer 202 / inner 204.
- Verification re-read: `programDescription == ""` — **`cleanup_ok = True`**.
- Net effect on account A's real data: none. The field was never actually changed at any point
  (the Step 1 write silently no-op'd), so there was nothing to restore in practice; the restore
  step ran regardless, per protocol.

## Bonus probe — CREATE-path self-alias (`MERGE Applications('0')`)

Also tested (extension of the Track B CREATE-path question): does the zero-key CREATE alias have
looser field filtering than the UPDATE path on a real `applicationId`? Result: **rejected, no
side effect.**

- `Applications` list before: 0 rows.
- `MERGE Applications('0')` with `programDescription = "KLXSSPD_CREATE_1"`: outer 202 / inner 204.
- `Applications` list after: 0 rows — **no new record created** (`new_ids = []`).
- Verdict: `CREATE_REJECTED`. No cleanup needed (nothing was created).

## Conclusion

`Applications.programDescription` is not an applicant-writable field on either the UPDATE path
(real `applicationId`) or the CREATE-path self-alias (`Applications('0')`). It cannot be used to
reach the `HtmlMenu.openBy` `innerHTML` sink from an applicant session. **Track H.1 candidate is
closed as NOT WRITABLE.** No further action needed on this field; the sink itself
(`control/HtmlMenu.js`, `t.innerHTML = l`, bound via `fragment/CommunicationMenu.fragment.xml`)
remains real but currently has no known applicant-reachable source feeding it, per the full Track
H static-analysis sweep in `07-track-h-candidates.md`.
