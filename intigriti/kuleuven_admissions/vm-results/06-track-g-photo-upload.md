# Track G — ApplicantPhotos upload surface

**Verdict: CLEAN NEGATIVE — no stored XSS, no filename-injection reflection,
no observable doc-type routing to a different queue.** SAP's ArchiveLink
upload endpoint is defended in depth:

1. **MIME allowlist rejects active types at intake** (`image/svg+xml`,
   `text/html`, `application/xhtml+xml` → 400).
2. **Served response normalizes to `image/jpeg` + `nosniff` +
   `Content-Disposition: attachment; filename=entity.jpg`** — even if a
   malicious MIME slipped through, the attachment disposition + nosniff
   would neuter inline render.
3. **Client-supplied slug metadata (`fileName`, `docType`) is never
   reflected in the response or in subsequent entity reads** —
   filename-injection carriers have nowhere to land.
4. **Server re-encodes uploaded JPEG bytes** (13182 → 13178 in our
   restore test) — indicates ArchiveLink strips metadata / re-processes
   the image, further reducing polyglot / EXIF-based attack surface.

**Run:** 2026-09-25/26. **Harnesses:** `tools/track_g_photo_upload.py`
(G1.0 + G1.1 + G1.2 + restore), `tools/track_g_slug_probes.py`
(G2.1 + G2.2 + restore). **Non-safe requests total this IP:** 9.
**Test artifacts left on account A:** photo replaced with SAP-re-encoded
version of the original (4 bytes shorter due to server metadata strip;
visually identical when rendered).

## G1.0 — Baseline serve behavior (the linchpin)

`GET /ApplicantPhotos('0')/$value` from A's session returned A's real
photo with these headers:

| Header | Value |
|---|---|
| `Content-Type` | `image/jpeg` |
| `X-Content-Type-Options` | `nosniff` |
| `Content-Disposition` | `attachment; filename=entity.jpg` |
| `Content-Security-Policy` | *(none)* |
| Response size | 13,182 bytes |

**Interpretation:** three of the four exploitability-gating headers are
in place. The lack of CSP is defensible because CSP on a binary blob URL
doesn't change the outcome. `attachment` + `nosniff` + normalized
`Content-Type` are the three layers that would need to fail before any
reflected type could execute — all three are present.

Filename `entity.jpg` is **hardcoded** (not derived from the client's
slug) — a strong signal that SAP strips upload filename metadata.

## G1.1/G1.2 — Active-MIME reflection probes

Three uploads with active Content-Types, each with an inert marker
body:

| Payload | Content-Type | slug | Upload result |
|---|---|---|---|
| `<svg xmlns="..."><script>/*KLG_SVG_MARKER*/</script></svg>` | `image/svg+xml` | `ZCM_ADM027\|klg_probe.svg` | **400** |
| `<!--KLG_HTML_MARKER--><html>...` | `text/html` | `ZCM_ADM027\|klg_probe.html` | **400** |
| `<?xml..><html xmlns="..."><body>KLG_XHTML_MARKER...` | `application/xhtml+xml` | `ZCM_ADM027\|klg_probe.xhtml` | **400** |

All three returned **HTTP 400** at the upload endpoint — SAP ArchiveLink
enforces a MIME allowlist that filters `image/svg+xml`, `text/html`, and
`application/xhtml+xml` regardless of the payload body. The 400 error
bodies are identical (850 bytes each, generic SAP exception envelope) —
same "malformed request" shape as other filtered writes elsewhere in
this service.

**No stored XSS carrier is reachable via Content-Type reflection.**

## G1.3 — Sniffing / polyglot bypass — moot given G1.1's outcome

Not run because:
- The MIME allowlist rejects the SVG variant at intake, so a JPEG-that-
  parses-as-SVG polyglot would still be rejected on Content-Type.
- The served Content-Type IS forced to `image/jpeg` (verified in the
  baseline), so even if a polyglot were stored, browsers would treat it
  as jpeg — the `<img src>` render context (see G4) doesn't sniff.
- `nosniff` is set (blocks Chrome's MIME sniffing).

The one interesting G1.3-adjacent observation from the restore probe:
uploading the exact baseline JPEG bytes (13182) resulted in a served
`$value` of 13178 bytes. **Server-side JPEG re-encoding / metadata strip
is present.** That would matter for G3 SSRF/XXE probing — but G3 requires
uploading an SVG the server would parse as SVG, which G1.1 blocked.

## G1.4 — Stored-XSS beacon — moot

The three-layer defense in G1.0 (`attachment`, `nosniff`, normalized MIME)
means no browser context we can reach would execute a stored payload
even if we managed to store one. G1.4 is off the table.

## G2.1 — Filename injection

Four uploads with a valid JPEG body but manipulated `<filename>` after
the pipe in `slug`:

| slug filename | Upload | fileName reflected in response body | fileName reflected in entity readback |
|---|---|---|---|
| `<img src=x onerror=/*KLG_FN*/>.jpg` | **201** | `""` (empty) | `null` |
| `../../../klg_trav.jpg` | **201** | `""` (empty) | `null` |
| `klg_g2_2_adm028.jpg` (control) | **201** | `""` (empty) | `null` |
| `klg_g2_2_letter.jpg` (control) | **201** | `""` (empty) | `null` |

**Every filename got 201 Created — including the HTML-metachar and path-
traversal payloads.** But **none reflected in any readable field**:

- The POST response body's `fileName` came back as an empty string on
  every probe.
- Reading `GET /ApplicantPhotos('0')` afterwards showed `fileName=null`.
- The `Content-Disposition` header on `$value` is hardcoded to
  `filename=entity.jpg` regardless of what we uploaded (per G1.0).

**Filename injection has no observable carrier.** Even if a staff-side
review UI displayed the uploaded filename, our injected string never
becomes part of that flow — SAP normalizes/drops it at the ArchiveLink
layer.

**Not the Bank Van Breda parallel** we hoped for. In that finding, the
server stored + reflected the client's filename verbatim into a review
UI. Here, the field simply isn't stored.

## G2.2 — Doc-type routing (the genuinely novel angle)

Two uploads varying the `<doctype>` before the pipe in `slug`:

| slug docType | Upload | docType reflected in response | docType reflected in entity readback |
|---|---|---|---|
| `ZCM_ADM028` | **201** | `""` | `null` |
| `ZCM_ADM_LETTER` | **201** | `""` | `null` |

Both **accepted with 201 Created** — including the outbound-document
`ZCM_ADM_LETTER` type. **BUT the same reflection blackout as G2.1:**
we cannot tell from any observable OData field where the file was
routed. Two hypotheses:

1. **SAP normalizes ANY docType to the canonical `ZCM_ADM027`** — every
   upload gets stored as an applicant photo regardless of the client's
   claimed docType. Safe. **This is the most likely interpretation**
   given every subsequent entity read shows the photo still exists at
   `ApplicantPhotos('0')` (i.e., the ADM028/ADM_LETTER uploads didn't
   go somewhere else — they replaced or added to the applicant's photo
   slot).
2. **SAP silently accepts the alternate docType and stores the file
   there**, but the OData service doesn't surface the docType in the
   response. Under this hypothesis, my `ZCM_ADM_LETTER` upload could be
   sitting in a staff-authored-document store, invisible to the OData
   layer. **We cannot verify this from the applicant OData surface.**

Under hypothesis 1: **clean-negative for doc-type routing.**
Under hypothesis 2: potentially reportable, but unprovable from the
applicant's visibility — the program would need SAP GUI or ArchiveLink
console access to disambiguate. **We cannot claim this without
verification.**

**Recommended follow-up**: ask the program (via responsible disclosure)
to check whether `ZCM_ADM_LETTER` documents were created on account A's
inAccountId around this timestamp. If yes, the routing filter is
missing; if no, hypothesis 1 holds.

## G3 — Server-side image processing — deferred

G1.3 indicated server-side JPEG re-encoding (baseline 13182 → served
13178 bytes on re-upload). That's a G1.3 signal that the server IS
processing images, which would open SVG-XXE / SVG-SSRF as a class.

However:
- G1.1 confirmed SVG uploads are 400-rejected at intake.
- The server-side processor is therefore only reachable for image
  MIMEs that survive the allowlist (JPEG, PNG, presumably GIF).
- JPEG-to-JPEG re-encoding doesn't invoke an XML parser and doesn't
  have obvious XXE/SSRF surface.

G3 skipped — no SVG parser to attack, no interactsh listener stood up.

## G4 — Render context (offline)

Where does `$value` render? From the extracted client bundle at
`vm-results/03-bundle/`:

```
controller/Main.controller.js:
    _getPicture: function() {
      var e = this.getView().byId("applFoto");
      i.getPicture().then(function() {
        e.setSrc("/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/
                  ApplicantPhotos('0')/$value?" + (new Date).getTime())
      }).catch(function() {
        // fallback img/OliFoto{EN,NL}.jpg
      })
    }
```

And `view/Main.view.xml:7`:
```xml
<Image id="applFoto" visible="{custo>/showPhoto}"
       width="123.9px" height="159.3px"
       decorative="false" alt="{i18n>upload_picture}"
       press="onPhotoUpload"/>
```

**Sole render context of `$value` is `<Image src>` (SAPUI5 `sap.m.Image`
element)** which becomes an HTML `<img src>`. In modern browsers:

- **`<img src=<svg with script>>` does NOT execute scripts.** SVG's
  script tag only executes in `<object>`, `<iframe>`, or direct
  navigation contexts.
- The `<img>` still respects `Content-Disposition: attachment` — but
  `<img src>` embeds specifically override attachment disposition
  (browsers ignore disposition for cross-origin image loads).
- `nosniff` on the response prevents Chrome from re-interpreting a
  reflected `text/html` body as HTML.

**Cross-user render surface (the severity multiplier):** we cannot
directly enumerate staff-side views, but the ApplicantPhoto entity's
`uploadedBy` field (metadata inspection from Sweep 14.2 — never client-
bound) strongly implies a staff-facing review UI exists that would load
`$value` too. Whether that staff UI honors `<img src>` or uses an
`<iframe>`/direct navigation is unknown from what we can see. If it uses
`<img src>` (the applicant-side pattern), the SVG-script vector remains
inert cross-user. If it navigates directly, the attachment disposition
would trigger a download.

**Bottom line:** even a hypothetical stored SVG-with-script would be
non-executable in the render contexts we can observe. The XSS chain is
architecturally closed.

## G5 — Cross-tenant upload — deferred

The upload endpoint is `POST /ApplicantPhotos` (collection, no URL key).
The client sends only `slug: <docType>|<filename>` and the binary body.
**There is no field in either the URL or the slug where a caller can
specify a different applicant's inAccountId.** The server binds the
upload to the caller's session identity — a cross-tenant photo write
from A→B is not reachable through this endpoint's client-observable API.

A theoretical bypass would need one of:
- Injecting a media-metadata property via the request body — but binary
  uploads don't carry OData property JSON.
- URL-keying the POST — but the endpoint doesn't accept a key on POST.
- Slug parsing that recognizes an extra field before/after the doctype
  and filename — untested.

The one-shot cost of testing slug-parsing variants (e.g., adding a
third segment `ZCM_ADM027|klg.jpg|IN01051651`) would be 1 non-safe
upload. Given we're at the ACL threshold on this IP, deferred for a
future run.

## Cumulative Track G accounting

- Non-safe HTTP requests this IP: 9 (3 rejected uploads + 1 restore in
  G1; 4 accepted uploads + 1 restore in G2).
- Test-state debris on account A: the current photo is a SAP-re-encoded
  version of the original (4 bytes shorter due to server metadata
  strip). Visually identical when rendered. No exogenous test payload
  persists (no injected filename, no injected docType observably
  landed).
- Restore verification: byte-compare showed `observed_len=13178 vs
  baseline_len=13182` — the 4-byte diff is SAP's server-side JPEG
  metadata strip, not a residual test artifact.

## Rows in `02-authz-matrix.jsonl`

- `"sweep": "g1.0"` — baseline serve headers
- `"sweep": "g1"` — G1.1 SVG, G1.2 HTML+XHTML uploads
- `"sweep": "g2"` — G2.1 filename injection, G2.2 doc-type variants
- `"sweep": "g_restore"` / `"g2_restore"` — cleanup
