# Submission draft — Improper output encoding in Conversations WebView (client-side HTML/JS injection sink; potential stored cross-user XSS)

**Target program:** Bank J.Van Breda & C° (Intigriti)
**Researcher:** treyky
**Affected assets (Tier 1, in scope):** `be.bankvanbreda.mobile` (VanBredaOnline) and
`be.bankdekremer.mobile` (Bank de Kremer) — identical shared codebase (`BVB.EOS.OnlineBanking.UI.Mobile`).

---

## Suggested severity

**Medium — with High/Critical escalation potential pending server-side verification.**

I am deliberately *not* claiming a confirmed High/Critical. What I have proven from the client is a
real, unambiguous client-side injection sink (self-XSS). Whether it rises to **stored cross-user XSS
in a banking app** — the high-severity case — depends on two server-side behaviors I cannot observe
without an authenticated account (see "What I verified vs. what needs your verification" below). I'm
disclosing transparently and providing complete reproduction steps so your team can settle the
escalation directly. Please assign final severity after that verification.

---

## Summary

The in-app **Conversations** (secure-messaging) feature renders message content into an Android
`WebView` that has JavaScript enabled, a native JavaScript bridge bound, and universal file-URL access —
**and it applies no HTML output encoding to the message body or sender name** when building that HTML.
Message content is passed through `WebUtility.HtmlDecode()` (the *opposite* of escaping) before being
interpolated into the HTML string, which guarantees that any markup in a stored message body becomes
live DOM. The customer send path likewise applies no encoding. A message body containing HTML/JS
therefore executes in the WebView when the conversation is rendered.

## Affected component (from decompiled client)

- **Render sink:** `ConversationDetailPage` → WebView `Html` bound to
  `ConversationDetailVM.HTMLSource`, built per-message by
  `HTMLHelper.GetHTMLChatMessageSource(msg)`, which interpolates
  `{WebUtility.HtmlDecode(msg.Body)}` and raw `{msg.SenderFullName}` directly into the HTML string.
- **WebView configuration** (`CustomWebViewHandler.cs`, `Handlers` namespace) — mapped **globally**
  for every MAUI `WebView` in the app:
  ```csharp
  webView.Settings.JavaScriptEnabled = true;
  webView.Settings.AllowFileAccess = true;
  webView.Settings.AllowFileAccessFromFileURLs = true;
  webView.Settings.AllowUniversalAccessFromFileURLs = true;
  webView.AddJavascriptInterface(new JsBridge(this), "jsBridge");
  ```
- **Native bridge:** `JsBridge.InvokeAction(string data)` (`[JavascriptInterface]`) forwards a
  JS-supplied string to the hosting page's `InteractCommand`. This means injected JavaScript in a
  rendered message can reach a native code path via `jsBridge.invokeAction(...)`, materially raising
  impact beyond a normal web-context XSS.
- **Send path:** `Communication.AddMessage(string body, …)` / `CreateConversation(string body, …)`
  (`Services/Server/Communication.cs`) assign `Body = <raw string>` with no HTML encoding or
  sanitization on the way out.

## Impact

- **Confirmed (client-side):** self-XSS — a customer who stores HTML/JS in a message body has it
  execute in their own app's WebView on render.
- **Potential (pending your verification):** if the server stores/returns the body verbatim and permits
  a customer to address a message to another customer, this becomes **stored cross-user XSS** inside an
  authenticated banking session, with reach into native functionality via `jsBridge.invokeAction`. In a
  banking app that is a high-severity outcome (session/data exposure, potential unauthorized in-app
  actions).

---

## Reproduction steps (deliberately broad — please test all variants so a narrow test doesn't
## false-negative)

**Prerequisite:** one (ideally two) authenticated test accounts on VanBredaOnline or Bank de Kremer.

### Part A — confirm the stored sink (single account)
1. Log in. Open **Conversations** and start/open a conversation.
2. Send a message whose body is each of the following payloads (test all — different payloads survive
   different server-side filters, so testing only one risks a false negative):
   - `<img src=x onerror="alert(document.domain)">`
   - `<script>alert(document.domain)</script>`
   - `<svg/onload=alert(1)>`
   - `<img src=x onerror="jsBridge.invokeAction('xss-poc')">`  ← proves native-bridge reach
   - An HTML-entity-encoded variant, e.g. `&lt;img src=x onerror=alert(1)&gt;` ← proves the
     `HtmlDecode` step re-activates encoded markup even if input is stored encoded.
3. Reopen/refresh the conversation so `ConversationDetailPage` re-renders the message.
4. **Observe:** whether any payload executes (alert fires / bridge action triggers). Execution confirms
   the server stored and returned the body without sanitization — i.e. **stored XSS**, not merely
   self-XSS.

### Part B — confirm cross-user reach (two accounts)
5. From account 1, attempt to create a conversation / send a message addressed to account 2, setting
   the receiver type to `OLBUSER` (the `ReceiverTypeCodes` enum models `OLBUSER` = online-banking user
   alongside `EMPLOYEE`/`BRANCH`/`HELPDESK`). Use each Part-A payload as the body.
6. Log in as account 2, open the received conversation.
7. **Observe:** whether the payload executes in account 2's WebView. Execution here is the
   **cross-user stored XSS** case.

### Part C — template-merge path (if Part B is blocked)
8. Independently, check whether the server-set `templateMergeContent` field on bank-authored message
   templates ever merges in an attacker-influenced value (e.g. a counterparty name / payment reference
   from a transaction the attacker controls). If a merged value is rendered unescaped, that is a
   second cross-user path into a message the victim renders, even if direct user-to-user addressing
   (Part B) is disallowed.

---

## What I verified vs. what needs your verification (full transparency)

- **Verified by me (static analysis of the decompiled client — no obfuscation on this path,
  `HTMLHelper` was cleanly readable):** the render sink un-encodes the body via `HtmlDecode` into a
  JS-enabled WebView with a native bridge; the send path applies no encoding; both together make the
  self-XSS case demonstrable from client code.
- **I could NOT verify (requires an authenticated account):** (a) does the server sanitize the body on
  store/return? (b) does the server permit a customer to address an `OLBUSER` message to another
  customer? (c) does any `templateMergeContent` template render an attacker-influenced value?
- **Why I couldn't test it myself:** account onboarding for this program requires Belgian
  self-employed / entrepreneur / liberal-profession eligibility, which I don't meet as an
  international researcher; there is no self-serve test/sandbox account available to me. I have
  separately asked the program whether read-only test credentials can be provided. In the meantime I'm
  disclosing this with complete reproduction steps so your team can confirm the escalation directly.

## Remediation

- HTML-encode `msg.Body` and `msg.SenderFullName` on output (do not `HtmlDecode` untrusted content
  into an HTML context); or render message content as text rather than HTML.
- If HTML rendering is required, sanitize server-side on store and on return, and apply a strict
  allowlist.
- Reconsider `AllowUniversalAccessFromFileURLs`/`AllowFileAccessFromFileURLs = true` and the global
  `jsBridge` exposure on any WebView that renders user-supplied content.

---

## Additional lead — NOT a claimed finding (flagged for your awareness / future verification)

I want to surface one authorization surface I identified in the same static analysis. **I am explicitly
not claiming this is a vulnerability** — I have no evidence the server is misconfigured, and I could not
test it (same account-access barrier described above). I'm mentioning it only because it's the natural
first authorization test if/when test credentials are arranged, and it maps directly to the
broken-authorization class your policy calls out as welcome.

- `GetAccountTransactions` (`Services.ApiServices.App.Contracts`) accepts a **client-supplied
  `AccountID` field** (JSON `"accountID"`, type `Guid?`). The same client-supplied-`Guid?`-`AccountID`
  pattern also appears on `GetDepositAccount`, `GetScheduledTransactions`, `GetStandingOrders`,
  `CardHolderDto`, `CreateUserDefinedNotificationDto`, and `ModifyUserDefinedNotificationDto`.
- **The only open question** (unanswerable without an account): does the server independently verify
  that the supplied `AccountID` belongs to the authenticated session's own customer, or does it trust
  the client-supplied value? If the latter, it's an IDOR; if it checks ownership (the expected secure
  behavior), it's a non-issue. I have **no data either way** — this is a pointer, not a report.
- Severity caveat if it ever is confirmed: `AccountID` is a `Guid` (not a sequential integer), so it is
  not brute-forceable at scale — per your own severity guidance this raises Attack Complexity. It would
  only be broadly exploitable if another surface leaks a second customer's account GUID.

Please treat this section as informational context, not a submission requiring triage on its own.
