# VM BRIEF — KU Leuven Admissions — Track H.1: confirm the `programDescription` → innerHTML stored XSS

**The one live candidate from Track H.** `Applications.programDescription` is an applicant-set
free-text field that flows into `HtmlMenu.openBy`'s raw `t.innerHTML = l` sink (via
`CommunicationMenu.fragment.xml`), and it slipped through every prior write sweep (not in Sweep 1
priv-fields, not in Sweep 7's 25 free-text sinks, not in Track E Sweep 13's 24). This brief
answers the single gating question: **does the server accept and persist HTML in
`programDescription` on MERGE?** If it stores raw HTML, an innerHTML sink receiving it is stored
XSS by definition — no executing payload needs to touch the server to prove it.

**Safety principle for this brief (important):** if this field is staff-reviewed (our whole
cross-user thesis), an executing payload left in it could fire on a real staff screen. So **no
executing payload is ever written to the server.** We prove the vuln with an inert marker (is it
writable?) and a **non-executing** HTML probe (is it stored raw or encoded?). The executing
demonstration is the researcher's own browser, own session, cleaned up immediately — not part of
this VM brief.

## Scope + guardrails (unchanged)

- ONLY `webwsp.aps.kuleuven.be/.../ZC_AD_APPLICANT_SRV/*`, account A (`000000503432`) only.
- Use the patched `$batch` helper (`dfb7693`) — the client writes `programDescription` via
  `services.insertApplication` → `MERGE /Applications('<id>')` under `setUseBatch(true)`, so the
  batched path is the faithful one. If batched MERGE misbehaves, a direct MERGE is an acceptable
  fallback (Applications accepts direct MERGE for legit fields).
- ACL: ~5 non-safe total. Well under threshold; single egress fine.
- **Mandatory baseline capture + restore** (see Step 0 and Step 4).

## Step 0 — Baseline capture (do FIRST, before any write)

`GET /Applications('000000503432')` and save the **entire** entity, and specifically the current
`programDescription` value verbatim (it holds A's real selected-program description). This is the
value Step 4 restores. Save to `vm-results/07-track-h1-evidence/baseline_application.json`.

## Step 1 — Probe 1: inert marker (is the field writable at all?)

Batched single-op changeset:
```
MERGE Applications('000000503432')
body: {"programDescription": "KLXSSPD_INERT_1"}
```
Read back `GET /Applications('000000503432')`. Record:
- inner batch status
- `programDescription` value on readback
- `field_changed` (True if it now reads `KLXSSPD_INERT_1`)

Outcomes:
- **field_changed=True** → field is applicant-writable. Proceed to Step 2.
- **204 + field_changed=False** → silent-drop (the F1.1 pattern); field is filtered. Candidate
  closed — skip to Step 4 (restore is a no-op but verify) and write the negative.
- **400/403** → rejected. Candidate closed — Step 4, write the negative.

## Step 2 — Probe 2: non-executing HTML (stored raw or encoded?)

Only if Step 1 showed the field writable. Two shapes, one at a time, readback after each:

1. `body: {"programDescription": "<b>KLXSSPD_2</b>"}`
2. `body: {"programDescription": "<img src=x>KLXSSPD_3"}`  ← note: **no `onerror`, no handler — inert**

For each readback, classify the stored value:
- **Stored RAW** (readback contains literal `<b>` / `<img`) → **this is the finding.** Raw HTML
  persisted into a field that feeds an `innerHTML` sink = stored XSS. The `<b>` vs `<img` pair
  tells us whether a weak tag filter exists (e.g., `<b>` survives but `<img>` stripped).
- **Stored ENCODED** (readback contains `&lt;b&gt;`) → server HTML-encodes on store. Then the
  innerHTML sink would render the encoded entities as text — safe. Candidate closed at the
  storage layer.
- **Stored STRIPPED** (markup removed, marker remains) → sanitized on store. Closed.

Record exact readback bytes for each in `07-track-h1-evidence/`.

## Step 3 — (Do NOT run an executing payload here)

The executing confirmation (`<img src=x onerror=...>` firing in HtmlMenu) is deliberately **not**
a VM step. If Step 2 shows raw storage, the vulnerability is proven at the storage+sink level from
static analysis of the sink (`HtmlMenu.js` `t.innerHTML = l`, already in evidence) plus the raw
readback. The live execution is the researcher's browser job (below), on their own session, with
immediate cleanup — so no executing payload is ever persisted server-side where staff could load
it.

## Step 4 — Restore (mandatory) + verify

Batched MERGE `programDescription` back to the **exact baseline value** captured in Step 0. Read
back and confirm it equals the baseline. Emit `cleanup_ok=True/False`. If cleanup fails, halt and
shout — A's real program description must be left as found.

## Deliverable

`vm-results/07-track-h1-programdescription-confirm.md`:
- Verdict: one of
  - **STORED RAW HTML — XSS CONFIRMED (self-demonstrable; cross-user via staff-review architecturally argued)**
  - **WRITABLE BUT ENCODED/STRIPPED — closed at storage layer**
  - **NOT WRITABLE (silent-drop / 403) — closed**
- The probe→readback table (inert, `<b>`, `<img>`), exact stored bytes.
- Baseline value + `cleanup_ok`.
- If RAW: the researcher's live-confirm recipe (Step 5 below), and the file:line sink evidence
  (`control/HtmlMenu.js` innerHTML assignment + `fragment/CommunicationMenu.fragment.xml` binding).
- Commit + push. If verdict is STORED RAW, that's the reportable finding — note it prominently.

## Step 5 — Researcher live-confirm recipe (hand off, do NOT run on VM)

Only meaningful if the VM verdict is STORED RAW. For the researcher, in their own browser, own
A session:
1. Via the app's normal ApplicationNew flow OR one manual MERGE, set `programDescription` to
   `<img src=x onerror=alert('KLXSS_HTMLMENU')>` — **on your own account only.**
2. Load Main view → open the Chat/Communication menu → `HtmlMenu.openBy`'s MutationObserver runs →
   the `alert` fires. Screenshot it.
3. **Immediately** restore `programDescription` to its baseline value. Do not leave the executing
   payload persisted — if the field is staff-reviewed, a reviewer loading your application would
   trigger it, which is beyond proof-of-concept.
4. That screenshot + the VM's raw-storage readback + the sink file:line = the complete PoC.

## Non-goals

No executing payloads written from the VM. No cross-account writes (A only). No staff-side testing
(we don't have staff access; the cross-user leg is the architectural argument, made in the report,
not something to reach by touching a staff surface). Restore A's real `programDescription` before
ending.
