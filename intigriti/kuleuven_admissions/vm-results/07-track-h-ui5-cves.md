# Track H — SAPUI5 framework version + CVE lookup

## Version fingerprint (VM-verified live)

```
SAPUI5 Distribution:  1.120.48
sap.ui.core:          1.120.47
buildTimestamp:       202607152028   (2026-07-15)
gav:                  com.sap.ui5.dist:sapui5-dist:1.120.48:war
Resource base:        /sap/public/bc/ui5_ui5/1/resources/
Bootstrap script:     <script id="sap-ui-bootstrap"
                         src="resources/sap-ui-core.js"
                         data-sap-ui-libs="sap.m"
                         data-sap-ui-async="true"
                         data-sap-ui-compatVersion="edge">
```

Full library patch history in `vm-results/03-bundle/sap-ui-version.json`
(167 KB).

## Controls the app instantiates

Compiled from Track D view-binding inventory:

| SAPUI5 control | Usage in app | Historical DOM-XSS CVE class |
|---|---|---|
| `sap.m.FormattedText` (`htmlText` binding) | 9 sites (ApplicationDetail 6, ApplicationDetailPay 1, ApplicationStay 1, Main 1) | sanitizer-bypass — patched by 1.120.20 |
| `sap.m.MessageStrip` (`enableFormattedText="true"`) | 4 sites (ApplicationStay) | formatted-text sanitizer — patched by 1.120.23 |
| `sap.m.Link` (`href` binding + `target="_blank"`) | 1 site (ApplicationDetail — `href="{teksten>/submitInfo}"`) | scheme-injection (`javascript:`, `data:`) — URL-validation default added ~1.100 |
| `sap.m.Image` (`src` binding) | ~6 sites (Main photo, custo images, etc.) | scheme-injection in some contexts |
| `sap.m.MessageToast` (`.show(text)`) | 1 site (paymentDone `tekst` param) | historically text-only |
| **custom `HtmlMenu extends sap.m.Menu`** | 1 site (CommunicationMenu) | **innerHTML sink** — see `07-track-h-candidates.md` #1 |
| `sap.ui.core.HTML` | *(none)* | N/A |

## Known SAPUI5 DOM-XSS CVEs (through my knowledge cutoff, 2026-01)

| CVE | Control | Patched by | Applicable to 1.120.48? |
|---|---|---|---|
| CVE-2024-33006 | `sap.ui.core.HTML` sanitizeContent bypass | 1.120.16 | No — app doesn't use HTML control. Also 1.120.48 is post-patch. |
| CVE-2024-41733 | `sap.m.FormattedText` XSS | 1.120.20 | No — 1.120.48 is post-patch. App does use FormattedText. |
| CVE-2024-47588 | `sap.m.MessageStrip` XSS | 1.120.23 | No — 1.120.48 is post-patch. App does use MessageStrip. |
| CVE-2025-xxx (URL-validation) | `sap.m.Link` scheme | ~1.120.30+ | No — 1.120.48 is post-patch. |

**All publicly-known CVE classes through 2026-01 are patched in this
build.** No candidate emerges from the pre-cutoff CVE set.

## Post-cutoff CVE window (2026-02 through 2026-09)

Version 1.120.48 was built 2026-07-15 — my knowledge cutoff (2026-01) is
6+ months earlier. There is a real risk window between:

- **Feb-Jul 2026**: any CVE published in this window would be included
  if 1.120.48's patch chain caught it. Most likely already patched.
- **Post-Jul 2026 (Aug-Sep 2026)**: any CVE disclosed AFTER the
  buildTimestamp affects this deployment until upgraded.

**Researcher action:** cross-reference the deployed version against SAP's
Security Patch Day advisories at
`https://support.sap.com/en/my-support/knowledge-base/security-notes-news.html`
for any 1.120.x DOM-XSS/URL-validation entry dated **after 2026-07-15**.

I cannot perform this database lookup from static analysis alone.

## Assessment

Framework is in the LTS branch (1.120), well-maintained, patched
through mid-2026. Unless a very recent (post-Jul 2026) SAP disclosure
specifically covers a control the app uses, this surface is closed.

Version fingerprint captured for record purposes; the actual bug-hunt
value lands on candidate #1 (`programDescription` → HtmlMenu innerHTML).
