# Track A2 — Deep mobile static analysis (Bank J.Van Breda & C°, Intigriti)

**Date:** 2026-09-19
**Scope:** `be.bankvanbreda.mobile` + `be.bankdekremer.mobile`, extending Track A
(`01-mobile-config-recon.md`) now that the ABI (`arm64-v8a`) split APKs are available alongside the
base splits, giving access to the compiled .NET/MAUI assemblies that Track A couldn't see. Still zero
contact with live bank infrastructure — everything below is static analysis of client binaries the
user supplied.

**Both apps share one client codebase.** After extracting the assemblies, every one of the 224
managed DLLs has the identical name/set in both apps (`BVB.EOS.OnlineBanking.UI.Mobile.dll` and all
its dependencies) — it's the same white-labeled `BVB.EOS.OnlineBanking.UI.Mobile` product for both
brands, differing only in resources/branding and the per-brand pinned certificates (see Task 1 note
below). Every C#-level finding in this report therefore applies to **both** apps identically; only
the Android manifest package name differs.

**Tooling note (for reproducibility):** the base split alone doesn't carry the app's .NET assemblies
— they're compiled into `lib/arm64-v8a/libassemblies.arm64-v8a.blob.so` inside the ABI split, wrapped
as an ELF `.so` with the real "XABA" assembly-store payload in a non-standard `payload` ELF section
(readable via `readelf -S`). The store is format **v2** (`pyxamstore`, the obvious open-source tool,
only handles v1), so a ~100-line custom Python parser was written against the documented v2/v3 layout
(`dotnet/android` project docs) to extract and LZ4-decompress the 224 assemblies. `dotnet-sdk-8.0` +
`ilspycmd` (installed via `dotnet tool install`) were used to decompile the extracted DLLs to C#.

## Task 1 — AndroidManifest.xml audit
Confirmed identical between both apps (only the package name / crc64-hashed class-name prefixes
differ):
- **Exported components:** only `MainActivity` (the launcher + all deep-link intent-filters — expected
  to be exported), `FirebaseInstanceIdReceiver` (protected by the `com.google.android.c2dm.permission.SEND`
  signature permission), `FirebaseMessagingService` (standard FCM boilerplate), and AndroidX's
  `ProfileInstallReceiver` (protected by `android.permission.DUMP`). **No custom exported
  activity/service/receiver/provider without protection was found** — clean result.
- **`android:allowBackup="false"`** in both apps — no `adb backup` extraction vector at all; this makes
  Task 4 (local data-at-rest review via backup) moot for both apps.
- **No `android:debuggable`** attribute present (defaults false) — not debuggable in this release build.
- **Custom deep-link hosts** (`android:autoVerify="true"` App Links, all on the single `MainActivity`):
  `xs2a-api-web.{brand}.be`, `wero.bankvanbreda.be` (VanBredaOnline only), `pub.mobile.{brand}.be`,
  `connective.bankvanbreda.be` (VanBredaOnline only), `itsme.{brand}.be` (`pathPrefix` `/sharedata`,
  `/confirm`). Matches Track A's findings; see Task 5 for what each does with the incoming URI.

## Task 2 — exported component dynamic testing
**Not performed — no Android emulator/device or `adb` available in this VM.** Given Task 1 found
only the single, necessarily-exported `MainActivity` (no secondary hidden exported component), the
dynamic test's main value would have been confirming Task 5's deep-link behavior live; that's covered
by the static trace in Task 5 instead. Flagging this as a genuine gap: a follow-up session with an
emulator could dynamically confirm the SSL-handling question raised in Task 3.

## Task 3 — WebView / JS-bridge audit
No `addJavascriptInterface` call appears in smali (Java/Kotlin layer) — but that's expected for a MAUI
app: WebView usage lives in C#, calling into the *Android framework's own* `WebView` class via
bindings, which never shows up as new smali bytecode. Reading the actual C# (`CustomWebViewHandler.cs`,
`BVB.EOS.OnlineBanking.UI.Mobile.Handlers`) found real substance:

```csharp
Android.Webkit.WebView webView = new Android.Webkit.WebView(base.Context);
webView.Settings.JavaScriptEnabled = true;
webView.Settings.AllowFileAccess = true;
webView.Settings.AllowFileAccessFromFileURLs = true;
webView.Settings.AllowUniversalAccessFromFileURLs = true;
webView.AddJavascriptInterface(new JsBridge(this), "jsBridge");
webView.SetWebViewClient(new InternalWebViewClient());
```

This is the handler mapped **globally** for every `Microsoft.Maui.Controls.WebView` in the app, so it
applies wherever the app uses a WebView, not just one screen.

- **`jsBridge` JS interface:** exposes exactly one native method, `invokeAction(data)`
  (`[JavascriptInterface] public void InvokeAction(string data)` in `JsBridge.cs`), which forwards the
  raw string straight to a bindable `InteractCommand` on the hosting page's ViewModel — i.e. it's a
  generic "send a string from the webpage's JS to whatever the current page's view-model does with
  it" bridge. Grepping for `InteractCommand` usage shows it is bound in exactly one place:
  `Areas.Communication.Conversations.ConversationDetailVM` — the secure-messaging/"Conversations"
  screen, which renders correspondence content in this WebView. Tracing the handler further
  (`ConversationDetailVM.d(string)`) was not completed in this session (heavily
  compiler-generated/obfuscated nesting); **this is the concrete next step**: confirm whether
  conversation/message content ever includes anything other than the bank's own sanitized text before
  it reaches this WebView, since if it does, that content's JS could call `jsBridge.invokeAction()`.
- **`AllowFileAccessFromFileURLs` + `AllowUniversalAccessFromFileURLs` both `true`**, combined with
  `JavaScriptEnabled = true` and a live native JS bridge, is the well-known "WebView universal file
  access" misconfiguration pattern (a `file://`-origin page can bypass same-origin policy). Whether
  this is exploitable depends on whether anything ever loads untrusted content into this shared
  handler — `MapWebSource` in the same file supports **both** fixed inline HTML
  (`HtmlWebViewSource` → `LoadDataWithBaseURL`) and a dynamic URL (`UrlWebViewSource` → `LoadUrl`), so
  it is not automatically a dead end the way a fixed-HTML-only WebView would be. Not conclusively
  resolved in this session which pages use the dynamic-URL path with content outside the bank's direct
  control.
- **`InternalWebViewClient` overrides `OnReceivedSslError`** (confirmed in both smali and the extracted
  C#: `BVB.EOS.OnlineBanking.UI.Mobile.Droid.Handlers.Helpers.InternalWebViewClient`). This is
  meaningfully different from "absence of SSL pinning" (explicitly excluded by program policy) — it's
  about whether the app *accepts connections with invalid certificates at all* (wrong host, expired,
  untrusted CA), which is a distinct and more severe bug class if true. **Could not be conclusively
  verified**: the assembly carries a `DotfuscatorAttribute` (confirmed via IL dump — PreEmptive
  Dotfuscator control-flow protection is in active use), and this specific method's decompiled C# is a
  heavily flattened switch/goto state machine with opaque predicates that ILSpy could not cleanly
  reconstruct. The decompiled fragment does contain a reachable-looking `handler.Proceed()` call, but
  I can't state with confidence, from static analysis alone, under exactly what condition that path is
  taken versus the safe default (cancel). **This is a clean candidate for dynamic verification**: point
  a MITM proxy with a self-signed/invalid cert at whatever this WebView loads and observe whether it
  renders anyway — that would resolve this in one test, and needs the emulator/device access Task 2
  didn't have.
- **MAUI's `HybridWebView`** framework class is present (linked into the binary) but a
  repository-wide search found **zero usages** of it in the app's own code — dead end, confirmed per
  the brief's own framing ("if the WebView only ever loads the bank's own fixed pages... say so"; here
  it's simply unused).

## Task 4 — local data-at-rest review
**N/A / moot** — `allowBackup="false"` (Task 1) means `adb backup` extraction isn't possible at all,
and no rooted device/emulator was available in this VM to pull `/data/data/<package>` directly. Not
pursued further; flagging as a gap for a future session with device access, though the backup vector
specifically is already closed by the manifest setting regardless.

## Task 5 — deep link logic review
Traced `BVB.EOS.OnlineBanking.UI.Mobile.Services.ApplinkReceiver` (the class that receives every
incoming deep-link/App-Link URI) for each custom host found in Task 1. Despite the same
Dotfuscator control-flow obfuscation affecting readability, the case bodies themselves (the actual
statements, as opposed to which order they run in) are legible enough to establish the following per
host:

- **`itsme.{brand}.be`** (`/sharedata`, `/confirm`): only processed `if
  App.Services.ItsmeService.WaitingForItsmeCallback` — i.e. the app must already be in a
  locally-initiated "expecting an itsme callback" state before it will parse anything from the
  incoming URI (`ParseItsmeRedirectURL(url)`). This is a reasonable state-gating mitigation against a
  cold, unsolicited deep link driving the itsme flow. Whether `ParseItsmeRedirectURL` itself validates
  a nonce/state parameter tying the specific response to the specific request it started (full CSRF/
  callback-confusion protection) wasn't traced further this session — worth a follow-up read of
  `ItsmeService` if Track B ever gets to this surface.
- **`connective.{brand}.be`**: same pattern — gated on `App.Services.ConnectiveService.WaitingForConnectiveCallback`,
  then `ParseConnectiveRedirectURL(url)`; if the parsed response's `Status == "SIGNED"` it shows an
  alert and force-logs-out (treats a connective callback arriving after the session moved on as
  reason to restart clean). Same follow-up caveat as itsme above.
- **`xs2a-api-web.{brand}.be`** and **`wero.bankvanbreda.be`**: **not parsed here at all** — the
  handler just sets a flag and **stores the raw incoming URL verbatim** (`App.Services.XS2A.XS2ARequestUrl
  = url` / `App.Services.Wero.WeroRequestUrl = url`) for a downstream page to consume, and if the app
  was already running (not a cold start), it calls `App.Services.Security.LogoutAndRestart(...)` —
  so an incoming XS2A/Wero deep link while logged in **forces the current session to log out and
  restart** to reprocess the link fresh. This is very likely intentional (PSD2 XS2A payment-initiation
  links are *supposed* to carry a merchant/PSP-supplied payment amount/IBAN for the user to confirm —
  that's the entire point of the XS2A PIS flow, directly comparable to the brief's cited
  `exodus://fiatOnramp` pattern), so pre-filling payment details from the link is by design, not a bug
  in itself. The security question that actually matters — whether the confirmation screen the user
  sees re-derives/re-validates the amount and IBAN from the *server* rather than trusting whatever the
  deep link's URL parameters said — requires tracing the page(s) that consume `XS2ARequestUrl`, which
  wasn't completed this session given time already spent on Tasks 3/6. **Flagging as the single
  highest-value follow-up for a next session**: find and read whatever page reads
  `App.Services.XS2A.XS2ARequestUrl`, specifically whether it calls back to the server to confirm the
  payment details before display, or renders the URL's own values directly.
- A forced logout from an attacker-crafted deep link matching these hosts is a mild nuisance
  (denial-of-service-adjacent) at most on its own — not the kind of state-changing/financial action the
  brief is asking about, so not flagged as a standalone finding.

## Task 6 — auth/session code review
- **Session token:** `SessionToken` is a plain string property, carried as a **request-body JSON
  field** (`"sessionToken"`) on outgoing DTOs (e.g. `LogonXs2aWeb`, `Xs2aSessionDto`) rather than an
  `Authorization` header — i.e. this API's session model is bespoke rather than standard bearer-token
  auth. Not a vulnerability by itself, but worth knowing for Track B request crafting.
- **Certificate pinning** (found while tracing `BaseServiceAgent`'s constructor): the app pins a list
  of hardcoded RSA public keys, selected by matching substrings (`dev-`, `test-`, `training-`,
  `accept-`, `payments-`, `bankvanbreda`, `bankdekremer`) against the API base URL passed in. Per the
  brief, pinning implementation/absence is explicitly **zero-payout / out of scope**, so this wasn't
  pursued further — noted only because it's also *why* Track A couldn't find a literal hardcoded base
  URL anywhere in the client: the real API host is supplied at runtime (build-variant/MDM/bootstrap
  config), not baked into this generic binary, and the pinning code only ever sees/matches against
  *substrings* of that runtime-supplied URL.
- **Client-suppliable account identifiers — the concrete Track B lead requested by this task:**
  `GetAccountTransactions` (`BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts`) has a
  client-settable `AccountID` field (JSON property `"accountID"`) of type `Guid?`. The same pattern —
  a client-supplied `Guid? AccountID` — repeats across `GetDepositAccount`, `GetScheduledTransactions`,
  `GetStandingOrders`, `CardHolderDto`, `CreateUserDefinedNotificationDto`, and
  `ModifyUserDefinedNotificationDto`. **This is exactly the client-suppliable-identifier pattern Track B
  should target**: once test credentials exist, the question is whether the server independently
  verifies that the supplied `AccountID` GUID belongs to the authenticated session's own customer, or
  trusts the client. Two notes for triage/severity once that's tested:
  - Using a `Guid` (not a sequential integer) means this **isn't brute-forceable at scale** — per the
    program's own severity guidance, GUID-based identifiers raise Attack Complexity, which matters for
    scoring even if an authz gap is confirmed.
  - A confirmed authz gap would still be exploitable (and scored higher) if any *other* surface in the
    app discloses another customer's account GUID — e.g. shared statement links, notification payloads,
    or the `xs2a-api-web`/`connective` deep-link flows from Task 5. Worth keeping an eye out for a leaked
    GUID anywhere else during Track B rather than assuming it's purely theoretical because it's a GUID.

## Summary
- Manifest: clean (no unprotected exported components, `allowBackup=false`, not debuggable).
- WebView: real substance found — a global custom `WebViewHandler` with JS enabled, universal
  file-URL access, a live JS bridge (bound to the Conversations/messaging screen), and a custom
  `OnReceivedSslError` override whose exact behavior static analysis (hampered by confirmed Dotfuscator
  control-flow obfuscation) couldn't fully pin down. **Two concrete next steps flagged, both requiring
  either more RE time or dynamic testing with a device**: (1) confirm what content can reach the
  Conversations WebView, (2) MITM-test the SSL error path directly.
- Deep links: itsme/connective callbacks are gated behind an app-local "waiting for callback" state
  (good); XS2A/Wero links pass the raw URL to a downstream payment-confirmation flow not traced this
  session — flagged as the top follow-up.
- Auth: session token travels in the request body, not a header (bespoke, not itself a bug).
- **Primary Track B lead:** `GetAccountTransactions` and five other request contracts take a
  client-supplied `Guid? AccountID` — the natural first IDOR probe once test credentials exist, with
  the GUID-vs-sequential-ID caveat noted above for severity framing.
