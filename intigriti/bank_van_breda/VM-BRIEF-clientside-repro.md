# VM INSTRUCTION PACK — Bank Van Breda — Client-side XSS reproduction rig (triager-requested PoC)

## Context & authorization (read first)

This is **authorized, triager-requested work** on an in-scope Intigriti bug bounty program
(Bank J.Van Breda & Co, report `BANKVANBREDA-2DR5X96O`, severity Medium/5.4, €750 possible
bounty, status: Triage/Awaiting-feedback). The assigned triager **3athlon** asked, in writing,
for a dynamic reproduction of a stored-XSS finding before it can be validated.

**This task touches NO live system.** It is entirely **local Android/HTML development**: build a
self-contained test rig that reproduces — from already-decompiled client code the researcher
lawfully obtained — the exact rendering pipeline of the bank's mobile app, to demonstrate that an
attachment filename containing HTML renders as live DOM in a WebView configured the way the real
app configures it. No bank server is contacted. No credentials. No network calls to any KU Leuven
or Bank Van Breda host. Pure local build + a screen-recordable demo.

**What this proves and what it does NOT:** it proves the **client-side sink** fires exactly as the
report describes. It does **not** prove the bank's server stores/returns the filename unencoded —
that is the one question only the program can answer (they have source + server access; the
researcher does not, due to an account-eligibility wall). The rig is deliberately built to make
that single server-side question explicit and checkable (the A/B toggle below).

---

## The finding being reproduced (exact decompiled source)

**Sink** — `HTMLHelper.GetHTMLChatAttachmentSource(AttachmentDto att)`,
`vm-results/03-xss-escalation-evidence/HTMLHelper_GetHTMLChatAttachmentSource.cs:67`:

```csharp
return $"<a class=\"download-link\" href=\"javascript:invokeCSCode('att#{att.AttachmentID.ToString()}')\"><em><div class=\"icon download\"><!-- DL icon --></div></em><div>{att.FileName}</div>{text}</a>";
```

- `att.FileName` is interpolated **raw** into `<div>{att.FileName}</div>` — no `HtmlEncode`, no
  sanitizer, no transform.
- The whole string is assigned to a WebView's HTML (via `ConversationDetailVM.HTMLSource` →
  `ConversationDetailPage` WebView).
- `att.AttachmentID` is a `Guid` (non-injectable); the `javascript:invokeCSCode(...)` href is the
  app's **native-bridge** invocation pattern — evidence that JS in this WebView can reach native
  code. The reproduction must mirror this bridge, named faithfully (verify exact name in Part A).

**Source (attacker-controlled input)** — the filename comes from the OS document picker and is
stored verbatim:
- `ShowConversationDetailUIProcess_attachment_upload.cs`: `FileName = text` where `text =
  showConversationDetailUIProcess.m()` (picker), then `CreateAttachment(this.m_d.ToFileInfo(),
  "MESSAGE")`.
- `RegisterConversationUIProcess_attachment_upload.cs`: `FileName = text` where `text =
  registerConversationUIProcess.e()` (picker), same upload call.
- `FileInfoDto.cs`: `FileName` is a plain `string` with raw get/set — no sanitization on the DTO.

**Cross-user render context** — `ReceiverTypeCodes.cs` / `SenderTypeCodes.cs` declare `OLBUSER`,
`EMPLOYEE`, `BRANCH`, `HELPDESK` as first-class. The attachment list renders on the counterparty's
client by design, so the recipient of a payload-named attachment is a different user (incl. bank
staff).

---

## PART A — Verify the exact WebView config + bridge name (do BEFORE writing Kotlin)

The earlier submission prose said the WebView binds `jsBridge` with `invokeAction`, but the sink's
href calls `invokeCSCode`. **Do not trust the prose — cite the decompiled source.** From the Track
A2 decompiled tree on this VM (under `~/bvb_apks/` or wherever Track A2 extracted the DLLs; if
missing, re-run the Track A2 XABA-v2 extraction documented in
`vm-results/02-deep-mobile-analysis.md`):

1. Find the WebView configuration class (the submission names it `CustomWebViewHandler.cs`). Grep
   the decompiled C# for: `JavaScriptEnabled`, `AllowFileAccess`, `AllowFileAccessFromFileURLs`,
   `AllowUniversalAccessFromFileURLs`, `AddJavascriptInterface`, `invokeCSCode`, `InvokeAction`.
2. Record the EXACT values: which settings are `true`, the exact JS-interface name bound via
   `AddJavascriptInterface(..., "<name>")`, and the exact native method the `javascript:` href
   calls (`invokeCSCode` and/or `invokeAction`).
3. Save findings to `pov/EXTRACTED-webview-config.md` with file:line citations. **Every setting in
   the Kotlin reproduction must trace to a line here.** If a specific value cannot be re-extracted,
   note it explicitly as "per submission, not re-verified" rather than asserting it.

If the decompiled tree is gone and cannot be rebuilt, proceed using the submission's documented
config but mark each unverified value clearly in the README's source-mapping table.

---

## PART B — The Android reproduction project

Build under `intigriti/bank_van_breda/pov/bvb-filename-xss-repro/`. Standard single-module Gradle
Android project, Kotlin, minSDK 24 / target 34. Package `be.research.bvbrepro` (clearly a research
artifact, not impersonating the bank package name).

### Design principle: every file cites the decompiled source it ports

Each Kotlin file opens with a comment block naming the exact decompiled file + line it reproduces,
so the triager (or the bank's engineers) can lay the two side-by-side and verify identical control
flow. Do not write "based on" — write the exact source location.

### Files

**`app/src/main/java/be/research/bvbrepro/HtmlHelper.kt`** — the sink, line-for-line:
```kotlin
// Ported verbatim from the decompiled Bank Van Breda mobile client.
// Source: BVB.EOS.OnlineBanking.UI.Mobile.Model/HTMLHelper.cs
//   method GetHTMLChatAttachmentSource(AttachmentDto att), return at line 67
//   (evidence: vm-results/03-xss-escalation-evidence/HTMLHelper_GetHTMLChatAttachmentSource.cs)
// Original C#:
//   return $"<a class=\"download-link\" href=\"javascript:invokeCSCode('att#{att.AttachmentID}')\">
//            ...<div>{att.FileName}</div>{text}</a>";
// The filename is interpolated RAW. No HtmlEncode. This file preserves that exactly.
object HtmlHelper {
    fun getHtmlChatAttachmentSource(att: AttachmentDto): String {
        // att.FileName interpolated with no encoding — identical to HTMLHelper.cs:67
        return "<a class=\"download-link\" " +
               "href=\"javascript:invokeCSCode('att#${att.attachmentId}')\">" +
               "<em><div class=\"icon download\"><!-- DL icon --></div></em>" +
               "<div>${att.fileName}</div></a>"
    }

    // Control: a hypothetical server-side HTML-encoding of the filename before render.
    // Demonstrates that the client sink's safety is ENTIRELY determined by whether the
    // server returns the filename raw or encoded — which is the one question for the program.
    fun getHtmlChatAttachmentSourceServerEncoded(att: AttachmentDto): String {
        val encoded = att.fileName
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\"", "&quot;").replace("'", "&#39;")
        return "<a class=\"download-link\" " +
               "href=\"javascript:invokeCSCode('att#${att.attachmentId}')\">" +
               "<em><div class=\"icon download\"><!-- DL icon --></div></em>" +
               "<div>$encoded</div></a>"
    }
}
```

**`app/src/main/java/be/research/bvbrepro/AttachmentDto.kt`** — the DTO shape, citing
`AttachmentDto.cs` / `FileInfoDto.cs` (FileName is a raw string).

**`app/src/main/java/be/research/bvbrepro/NativeBridge.kt`** — the native bridge, named EXACTLY as
Part A found it bound (if `AddJavascriptInterface(x, "jsBridge")` then interface name `jsBridge`
with the method the href calls). A `@JavascriptInterface`-annotated method that logs to Logcat when
called, so a filename payload invoking it proves JS→native reach. Cite the WebView-handler source
line from Part A.

**`app/src/main/java/be/research/bvbrepro/BvbWebViewConfig.kt`** — applies the EXACT settings Part A
verified:
```kotlin
// Ported from <WebView handler class>.cs (see pov/EXTRACTED-webview-config.md for file:line)
webView.settings.javaScriptEnabled = true
webView.settings.allowFileAccess = true                    // cite line
webView.settings.allowFileAccessFromFileURLs = true        // cite line
webView.settings.allowUniversalAccessFromFileURLs = true   // cite line
webView.addJavascriptInterface(NativeBridge(ctx), "<exact name from Part A>")
```
Only include settings actually verified in Part A; annotate any unverified one.

**`app/src/main/java/be/research/bvbrepro/MainActivity.kt`** — the harness UI:
- A dropdown/list of the four payload filenames (from `payloads.json`).
- A free-text field to type an arbitrary filename.
- **Two buttons** — the credibility centerpiece:
  - **"Server returns RAW"** → `HtmlHelper.getHtmlChatAttachmentSource(att)` → load into WebView →
    payload executes.
  - **"Server ENCODES"** → `HtmlHelper.getHtmlChatAttachmentSourceServerEncoded(att)` → load →
    filename renders as inert text, no execution.
- A read-only text area showing the exact HTML string being loaded (so the viewer sees the sink).
- Load HTML via `loadDataWithBaseURL("file:///android_asset/", html, "text/html", "UTF-8", null)`
  to exercise the file-URL-access config faithfully.

**`app/src/main/assets/payloads.json`** — the test filenames:
```json
[
  {"label":"classic-img","fileName":"<img src=x onerror=alert('poc-filename-xss')>.pdf"},
  {"label":"script-tag","fileName":"<script>alert('poc-script')</script>.pdf"},
  {"label":"native-bridge-reach","fileName":"<img src=x onerror=invokeCSCode('poc-native-reach')>.pdf"},
  {"label":"svg","fileName":"<svg/onload=alert('poc-svg')>.pdf"}
]
```
(Use the real bridge-call name from Part A in the `native-bridge-reach` payload.)

**`app/src/main/res/layout/activity_main.xml`**, **`AndroidManifest.xml`**, **`build.gradle.kts`**
(app + root), **`settings.gradle.kts`**, **`gradle/wrapper/`** — standard. App label
"BVB Filename XSS Repro (research)". No INTERNET permission needed (nothing talks to a network) —
omit it, and note in the README that the rig is fully offline.

---

## PART C — Standalone HTML harness (trivially recordable fallback + supplementary proof)

Android WebView is Chromium; the raw-interpolation sink behaves identically in any browser. Produce
`pov/bvb-filename-xss-repro/sink-demo.html` — a single self-contained file that:
- Contains the exact `GetHTMLChatAttachmentSource` template as a JS string-builder (cite line 67 in
  a comment).
- Has the same two-button A/B (raw vs encoded) and the same four payloads.
- On "RAW": sets a container's `innerHTML` to the built string → payload fires.
- On "ENCODE": sets it to the encoded string → inert text.
- Prints the exact HTML being injected on-screen.

This gives the researcher a zero-setup, screen-recordable proof (just open in a browser) that
demonstrates the sink mechanics, as a companion to the Android APK which demonstrates it in the
app's actual WebView configuration. Both get delivered.

---

## PART D — Attempt a verified build (produce an APK if the toolchain cooperates)

The researcher will likely build in Android Studio, but a VM-produced debug APK is a bonus. Attempt
a headless build:
1. Ensure JDK 17 (`apt-get install -y openjdk-17-jdk` if needed).
2. Fetch Android cmdline-tools, `sdkmanager --install "platforms;android-34" "build-tools;34.0.0"
   "platform-tools"`, accept licenses.
3. `cd pov/bvb-filename-xss-repro && ./gradlew assembleDebug`.
4. If it builds: copy the APK to `pov/bvb-filename-xss-repro/artifacts/bvb-filename-xss-repro-debug.apk`
   and record the build log.
5. If the SDK download or build fails (disk, network policy, KVM): **do not block.** Commit the
   full source project + the HTML harness; note in the README that the APK should be built in
   Android Studio, and that `sink-demo.html` needs no build at all.

**Do NOT attempt to run an Android emulator / record video on the VM** — KVM is likely unavailable
and it's fragile. Video recording is the researcher's step (real device or their own emulator), or
trivially the browser for `sink-demo.html`.

---

## PART E — README (`pov/bvb-filename-xss-repro/README.md`)

Sections, in order:

1. **Purpose & scope** — one paragraph: this reproduces the client-side sink from Bank Van Breda
   report `BANKVANBREDA-2DR5X96O` at triager request. State plainly: proves the client sink fires;
   does NOT prove server storage behavior; that server question is the program's to confirm.
2. **Provenance** — how the C# was obtained (Track A2 APK decompilation of `be.bankvanbreda.mobile`
   + `be.bankdekremer.mobile`, shared `BVB.EOS.OnlineBanking.UI.Mobile` codebase; XABA-v2 extraction
   + ilspycmd; methodology referenced in the submission). No secrets, no credentials, offline rig.
3. **Source-mapping table** — every Kotlin/HTML file → the exact decompiled `.cs` file:line it
   reproduces. This is the auditability core. Mark any value not re-verified in Part A.
4. **The A/B design (why two buttons)** — explain that the client sink's safety is entirely
   determined by server behavior on `AttachmentDto.FileName`. Button RAW shows the outcome if the
   server returns the filename verbatim (stored XSS). Button ENCODE shows the outcome if the server
   HTML-encodes on store/delivery (safe). Same WebView, same template, same client code.
5. **The one question for the program** — verbatim framing the triager can act on:
   > This rig reduces the finding to a single server-side question the program can answer in
   > minutes with source access: when a client uploads an attachment with
   > `FileName = "<img src=x onerror=alert(1)>"`, does the server store and return that string
   > verbatim to the recipient's client, or does it HTML-encode it first? The "Server returns RAW"
   > button demonstrates the former (confirmed stored XSS via `HTMLHelper.cs:67`); the "Server
   > ENCODES" button demonstrates the latter (mitigated). The answer determines validity.
6. **How to reproduce** — (a) `sink-demo.html`: open in any browser, press RAW, see alert; press
   ENCODE, see inert text. (b) Android: open in Android Studio, build, run on device/emulator,
   select payload, press RAW (alert + Logcat native-bridge line), press ENCODE (inert).
7. **Honest limitations** — no live server tested; account-eligibility wall documented in the
   submission; cross-user (staff-side) render is architectural per `ReceiverTypeCodes`, not
   demonstrated against a real staff client.

---

## PART F — Division of labor (VM vs researcher)

**VM does:** Part A verification doc; the full Android project (all files, citations); the HTML
harness; attempt the Gradle build + APK; the README; commit + push everything.

**Researcher does (cannot be done on VM):** build/open in Android Studio if the VM build failed;
run on a real device or their own emulator; **record the video** (boot → pick payload → press RAW →
alert fires → show Logcat native-bridge line → press ENCODE → inert text → repeat for a 2nd
payload); OR just screen-record `sink-demo.html` in a browser for the zero-setup version. Then
attach video + APK + repo link to the ticket with the honest cover message.

---

## Deliverables (commit each as produced)

Under `intigriti/bank_van_breda/pov/`:
- `EXTRACTED-webview-config.md` — Part A citations
- `bvb-filename-xss-repro/` — the Android project (full source)
- `bvb-filename-xss-repro/sink-demo.html` — the standalone harness
- `bvb-filename-xss-repro/README.md` — provenance, source-map, A/B rationale, the one question
- `bvb-filename-xss-repro/artifacts/…apk` — if the build succeeded
- `bvb-filename-xss-repro/BUILD-LOG.md` — what built, what didn't, why

## Non-goals / hard limits

- **No network calls to any Bank Van Breda, KU Leuven, or bank host. No live testing. No
  credentials.** This is a local rig only.
- Do not impersonate the bank's app package name or branding — it's a clearly-labeled research
  artifact (`be.research.bvbrepro`).
- Do not overstate: the README must state the rig proves the client sink, not the server behavior.
- If the decompiled tree is unavailable, reproduce from the committed evidence snippets in
  `vm-results/03-xss-escalation-evidence/` and mark anything not independently re-verified.
