# Track D.3 — i18n bundle grep

Three property bundles extracted in C.1 to `vm-results/03-bundle/i18n/`:

- `i18n.properties`         — the fallback bundle (English, 289 lines, 273 keys)
- `i18n_en.properties`      — English variant (393 lines, **366 keys**)
- `i18n_nl.properties`      — Dutch variant  (393 lines, 366 keys)

The two localized bundles have identical key sets — no divergence. The fallback
`i18n.properties` has fewer keys because it's an older subset that gets shadowed
by `i18n_en.properties` at runtime (`sap-language=EN` in every request).

No `hidden_*`, `debug_*`, `internal_*`, `staff_*`, `admin_*`, `test_*`, `dev_*`
keys exist in any bundle. The bundle is clean of obvious dev-leftovers.

## 1. Signals that survived the false-positive filter

The brief's word list (`admin`, `staff`, `reviewer`, `internal`, `debug`,
`test`, `dev`, `hidden`, `error_`, `code_`) triggered ~30 matches per bundle
after removing false positives (`test` inside `type of programme`, `super`
inside `supervisor`, `dev` inside `development`, etc.). What remains:

| Key | English text | Signal |
|---|---|---|
| `email_case_admin` | "Processed by" | Confirms `Applications.caseAdmin` OData field is rendered as a "the staff person handling your case" label. Sweep 1 already tested MERGE on `caseAdmin` → 403 (server-enforced). **The key is orphan** — no view/controller currently references it (see §3), suggesting a removed or planned "Show me who's handling my case" UI. |
| `kuleuven_staff` = "KU Leuven academic staff" | `other_staff` = "Other academic staff" | Labels for a **staff-type toggle** in the doctoral flow (`doctSupervisor` field). Both **orphan** — no view/controller in the preload references them. Either the doctoral supervisor-selection flow was removed, or it's lazy-loaded on demand (matches the pattern for `ApplicationAttachments`; see `04-views-analysis.md § 8`). |
| `he_read_only` | *(only key present, no view refers)* | **Orphan.** Hints at a "diploma is read-only because staff verified it" UI state that would render when `HigherEducations('X').editable === false`. Combined with `he_degree_checked` ("This diploma is validated; contact admissions to change it") **used by** `Curriculum.controller.js`'s `onDeleteItemOld`, this **confirms server-side row-level editability tracking on HigherEducations** — the `editable` boolean on a HigherEducations row is server-writable (staff toggles it) and applicant-visible-read-only. **Sweep-9 candidate S9-C2 reinforced:** raw MERGE on a server-marked `editable:false` HigherEducations row from applicant session — does the server respect its own flag? |
| `error_delete_appl` | "Only applications with status incomplete can be deleted" | Client-side error string for `Main.onDeleteApplication`'s status-whitelist check. Matches the `022|041|101|202` whitelist. Not a bug per se; confirms the client's model of "allowed to delete." **Sweep-9 S9-M2 hypothesis:** server should share this rule. |
| `promotor` / `copromotor` | "Supervisor" / "Proposed co-supervisor(s)" | Doctoral flow field labels for `doctSupervisor` / `doctCoSupervisor` OData fields. Track D §4 confirmed `doctCoSupervisor` is bound in the view and **is a free-text sink not tested by Sweep 7** — added to S9-V2. |
| `privacyDoorgeven` = `<br>Provide my information to:` | starts with a literal `<br>` HTML tag | **Orphan.** Whoever wrote this expected `htmlText` rendering, but no view binds the key. Dead string. |
| `boodschapIE` = "You use Internet Explorer. …" | | IE-detection message shown in `Main.onInit`. Present in the bundle; no security implication. |

## 2. HTML fragments embedded in i18n strings

`grep -E '<[a-z]+' i18n_en.properties` returns exactly one hit:

```
privacyDoorgeven=<br>Provide my information to:
```

Everything else is plain text. **No `<a href=…>`, `<img>`, `<script>`, or
event-handler attributes** appear in any i18n bundle. Formatter.js's hardcoded
disclaimers ARE HTML (with hardcoded `<br>` and `<a>` to `www.kuleuven.be`),
but those live in `model/Formatter.js`, not in the i18n bundles.

## 3. Orphan i18n keys — declared but unreferenced

**74 keys** (of 366 in `i18n_en.properties`) are declared in the bundle but
not referenced by any view/controller/fragment/util in the preload. Categories
of orphan (grouped):

- **Feature removed or refactored** — `bindTextDisccode`, `bindTextKeywords`
  (discipline dialog was refactored; new fragment uses `addDisciplineBindText`
  as literal, not this key); `verblijfsadres`, `domicilieadres` (old Dutch
  labels for stay/residence address; views use `stayAddress` now).
- **Feature never wired** — `kuleuven_staff`, `other_staff`, `email_case_admin`,
  `he_read_only`, `attachment_type`, `attachments`, `select_attachment_type`,
  `type_mismatch`, `uploadErrors`, `noDisciplineText` (attachment flow, staff-
  selection flow, disccode-search UI — likely lazy-loaded views not shipped in
  the preload; see missing `ApplicationAttachments.view.xml`).
- **Info-panel text never rendered** — `info_text`, `disclaimer`, `privacy`,
  `privacyDoorgeven`, `student_service`, `traveling_to_Leuven`, `housing_info`,
  `contact_details`, `social_media`, `kuleuven_website`, `other_website`,
  `fair`, `brochure`, `here`.
- **Field labels for unbound OData fields** — `mc_opleiding`, `gekozen_opleiding`,
  `functie_beperking`, `alumnus`, `employer`, `disciplines`, `keyword`,
  `program_first_option`, `program_second_option`, `program_third_option`,
  `options`, `decision`, `proposition`, `list_interrupts`.
- **Validation strings for unwired rules** — `GsmRequired`, `curAdStateNok`,
  `perAdStateNok`, `dateBeforePast`, `naamIncorrect`, `voornaamIncorrect`,
  `rrnrGbDatNietCorrect`, `akkoord`, `verwijder`, `kies_MC`, `kies_opo`,
  `kies_programma`, `kotvraag`.

**Full list**:

```
Code0..3 Field0..3 (actually used by utils/DiscCodeValueHelpHelper — not
  orphan; earlier scan missed util files)
GsmRequired addresses admission_code akkoord alumnus appDescription appTitle
attachment_type attachments bindTextDisccode bindTextKeywords brochure
contact_details create curAdStateNok dateBeforePast decision disciplines
disclaimer domicilieadres email_case_admin employer exch_endda fair finish
follow_up functie_beperking gekozen_opleiding he_read_only here housing_info
info_text instelling keyword kies_MC kies_opo kies_programma kotvraag
kuleuven_staff kuleuven_website list_interrupts main mc_opleiding
naamIncorrect noDisciplineText options other_staff other_website
perAdStateNok privacy privacyDoorgeven program_first_option
program_second_option program_third_option proposition rrnrGbDatNietCorrect
scholarships searchDisccode (actually used by utils — not orphan) social_media
street_number_box student_service title title_main traveling_to_Leuven
type_mismatch uploadErrors verblijfsadres verwijder voornaamIncorrect
```

(Subtract `Code0..3`, `Field0..3`, `searchDisccode`, `appTitle` that ARE used
by `utils/DiscCodeValueHelpHelper.js` and `locate-reuse-libs.js` respectively
— the earlier scan didn't look under `utils/`. Corrected orphan count: **65**.)

## 4. What this tells us about the OData surface

- **Server-side per-row `editable` flag on HigherEducations is real** —
  `he_read_only` + `he_degree_checked` both exist, one is used, the other
  would be used when the row is read-only. Reinforces S9-C2.
- **`caseAdmin` field is intentionally visible** to applicants (via the
  never-wired `email_case_admin` label). Sweep 1's 403 on `caseAdmin` MERGE is
  the correct server behavior: the field is server-write-only but
  applicant-read-only.
- **Doctoral flow has a two-way staff-type toggle** (`kuleuven_staff` vs.
  `other_staff`) that isn't in the current preload — same class as the missing
  `ApplicationAttachments` view. If the app lazy-loads a doctoral-form
  extension from `/sap/bc/ui5_ui5/sap/zc_ad_appl/…`, that's an additional
  in-scope client asset to fetch. **Track D follow-up (needs live network).**
- **The bundle has no debug/staging/hidden strings** — no reference to
  `dev`, `qa`, `staging`, `sandbox`, `preview`, `internal`, `todo`, `fixme`,
  or `test`-marker phrases. The bundle looks like a production build.

## 5. Cross-reference to earlier tracks

- Track A already documented the OData reads/writes that these i18n strings
  label. The i18n bundle **adds no new endpoints or fields**; it only clarifies
  intent for already-known fields.
- Track B Sweep 1's rejected priv-fields (`statusCode`, `caseAdmin`,
  `isAppFeePayed`, `followUpAdmLetter`, `institution`, …) all have applicant-
  facing i18n labels here — the client design *always intended* those fields
  to be applicant-read-only. Sweep 1's 403 wall matches that intent.
- Track B Sweep 7's stored-XSS payload never persisted, and this bundle's clean
  HTML content means there's no stored-XSS chain hiding in the i18n strings
  themselves.

## 6. No new Sweep-9 candidates emerge from D.3

The i18n grep reinforces existing hypotheses (`S9-C2` via `he_read_only`, `S9-V2`
via `promotor`/`copromotor` and doctoral field labels) but doesn't surface any
new endpoints or unrouted-but-referenced flows beyond what Track C/D already
listed. `ApplicationAttachments` and a doctoral supervisor flow are lazy-loaded
UIs worth fetching directly if network reachability to
`webwsp.aps.kuleuven.be` returns.
