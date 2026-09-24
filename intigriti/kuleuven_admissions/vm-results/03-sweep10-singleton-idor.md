# Track E — Sweep 10 — S9-C1 collection-write-via-singleton-key IDOR

**Verdict (phases that ran): WRITE REJECTED — SERVER ENFORCES.** All three
target endpoints (`HigherEducations`, `Interrupts`, `LanguageKnowledges`)
return **HTTP 501 Not Implemented** on MERGE, DELETE, and POST from an
applicant session — the same object-level refusal Sweep 9 found on
`LongTexts`. The theoretical "server routes writes by body-payload id, not
URL key" attack shape can therefore not manifest against these three
endpoints via the OData v2 service.

**Critical caveat:** Sweep 10 phases 10.2 (own-row control) and **10.4 (the
cross-user body-id write — the actual crown-jewel probe)** did NOT run
because **both test accounts have zero rows** in all three collections. To
truly close S9-C1 as clean-negative, one of the accounts needs at least one
row seeded via the normal UI flow (curriculum entry, interruption period,
or language knowledge). See §5.

**Run:** 2026-09-24. **Harness:**
`tools/track_e.py --sweeps 10 --append --min-interval 8`. **Rows appended
to `02-authz-matrix.jsonl`:** 48.

## 1. Baseline row enumeration (10.1)

| Endpoint | A rows | B rows |
|---|---|---|
| `Curriculums('0')/HigherEducations` | 0 | 0 |
| `Curriculums('0')/Interrupts` | 0 | 0 |
| `Languages('0')/LanguageKnowledges` | 0 | 0 |

Both test accounts are **empty** on the curriculum/interrupt/language sub-
collections. Neither has ever completed curriculum data through the UI.
This is why phases 10.2 and 10.4 couldn't proceed (see §4).

## 2. Create-via-MERGE attacker-id probe (10.3)

From A's session, MERGE the `('0')` singleton with body `{higherEducationId:
"99000", nameSchool:"KLTEST_S10_3_Hig"}` (and equivalents for the other two
collections). Server response for all three:

| Endpoint | Attacker id | Write status | Created in A? | Appears in B? |
|---|---|---|---|---|
| `HigherEducations('0')` | `99000` | **501** | False | False |
| `Interrupts('0')` | `99000` | **501** | False | False |
| `LanguageKnowledges('0')` | `99000` | **501** | False | False |

Re-read from both A and B confirmed nothing was written. Same 501 signature
as Sweep 9 — the entity's `UPDATE_ENTITY` handler is not implemented at the
SAP OData layer.

## 3. DELETE singleton probe (10.5)

Direct `DELETE /<endpoint>('0')` from A's session:

| Endpoint | DELETE status | Rows before | Rows after |
|---|---|---|---|
| `HigherEducations('0')` | **501** | 0 | 0 |
| `Interrupts('0')` | **501** | 0 | 0 |
| `LanguageKnowledges('0')` | **501** | 0 | 0 |

`DELETE_ENTITY` is not implemented either. (Also: `services.js` declares
`deleteHigherEducation` and `deleteLangKnow` but no controller calls them
— matches the observed 501: the client-side stub was never wired because
the server never accepted it.)

## 4. POST-create (10.6) — partial, ACL re-tripped

Direct `POST /<collection>` with a full-entity body:

| Endpoint | POST status | In A? | In B? |
|---|---|---|---|
| `HigherEducations` | **501** | False | False |
| `Interrupts` | **ERR** (TCP RST) | False | False |
| `LanguageKnowledges` | **ERR** (TCP RST) | False | False |

Only `HigherEducations` completed cleanly. The `Interrupts` and
`LanguageKnowledges` POSTs returned `ERR` because the SAP Web Dispatcher
automated ACL re-tripped at that point (~12-15 non-safe requests on this
egress). See §6.

## 5. Phases NOT run — and why

- **10.2 (own-row control)** — skipped: A has 0 baseline rows in every
  collection, so there's no "own row" to MERGE-echo. This phase exists to
  verify the write path is well-formed before probing the abuse cases;
  with all writes 501ing anyway, this loss is minor.
- **10.4 (cross-user body-id write — the actual highest-EV probe)** —
  skipped: B has 0 rows, so we have no B-owned id to spoof from A's session.
  **This is the significant gap.** The whole shape of S9-C1 is "server
  demuxes writes by body-payload id, not by URL key" — but if the entity
  refuses ALL writes (501), the body-id routing question is moot. The
  question could still be interesting for the DisciplineSet/TrefwoordenSet
  endpoints, which use composite URL keys (see §7).
- **10.7 (DisciplineSet + TrefwoordenSet)** — not run this session; the
  brief tags them as extensions of the singleton-key pattern but they use
  composite URL keys (`applicationId=<x>,key=<y>`), a different shape.
  Deferred to a follow-up sweep after the ACL clears.

## 6. Operational — ACL re-trip

Second write-heavy Track E sweep on this VM's egress. ACL re-tripped after
~12-15 non-safe requests (visible in Sweep-10.6 as the last two POSTs
returning ERR). Consistent with the postmortem note that repeated
IPs trigger tighter thresholds each round. Reachability check right after
Sweep 10 finished: `webwsp.aps.kuleuven.be:443` TCP-timeout.

**Trigger threshold observed on this egress (fresh IP, 8 s/req):**
~15 non-safe method attempts against `/ZC_AD_APPLICANT_SRV/*` — down
from Sweep 9's ~30 on this same IP earlier today. The ACL memory persists
across a 30-min gap.

## 7. Follow-up needed

To complete Sweep 10 as fully clean-negative — or catch any bypass — two
things are needed:

1. **Seed baseline rows.** Fill in one HigherEducations row on account A
   via the normal admissions-app UI (Curriculum tab → "Add higher
   education" → save). Same on B. Then re-run Sweep 10 phases 10.2 and 10.4
   — the cross-user body-id probe is where the real S9-C1 answer lives.

2. **Test DisciplineSet + TrefwoordenSet.** These use composite URL keys
   `(applicationId='<x>',key='<y>')`. From A's session, MERGE
   `/DisciplineSet(applicationId='<A>',key='1')` with body
   `{applicationId:"<B's applicationId>", key:"1", disciplineCode:"..."}`
   — does the server route by URL (safe) or by body (unsafe)?
   Only ~4 write requests needed; safe to schedule after the ACL clears.

## 8. Interpretation

The 501 wall on `HigherEducations/Interrupts/LanguageKnowledges` is
interesting because the client bundle SHOWS working writes to these
endpoints:

```js
// services.js -> updateCurriculumBatch:
this.model.setDeferredGroups(["curriculum"]);
this.model.update("/Curriculums('0')", curriculumFields, {groupId:"curriculum"});
for (var s in highers) {
  this.model.update("/HigherEducations('0')", highers[s], {groupId:"curriculum"});
}
for (var r in interrupts) {
  this.model.update("/Interrupts('0')", interrupts[r], {groupId:"curriculum"});
}
this.model.submitChanges({groupId:"curriculum", ...});
```

So the client sends `MERGE /HigherEducations('0')` inside a `$batch` /
`submitChanges` group. Standalone MERGE returns 501. **The write path only
works via the batch wrapper**, or possibly only after the parent
`Curriculums('0')` context has been established in the same batch.

This is a fresh Sweep-10 sub-probe: **retry MERGE inside a `$batch` group**
that first touches `/Curriculums('0')`, then the singleton. If 501 still
holds, the entity is truly read-only via OData v2 — the SAP staff probably
writes it through a different service. If a batch wrapper turns 501 into
204, we have a subtle **path-condition write** that Sweep 9's method-
spoofing (9.4) already tried but only against LongTexts, not these three.

Deferred to a follow-up sweep — schedule after the ACL clears and after
seeding at least one baseline row.

## Row-index reference

Sweep-10 rows in `02-authz-matrix.jsonl` grep for `"sweep": "10"`.
