# Intigriti form-fill — SUBMISSION-01 (Conversations XSS)

Copy each field into the matching box on the Intigriti submission form. The DOCX
(`SUBMISSION-01-conversations-xss.docx`) goes in **Attachments**.

---

## Title
```
Improper output encoding in Conversations WebView — client-side HTML/JS injection sink (potential stored cross-user XSS)
```

## Select asset
`be.bankvanbreda.mobile` (Tier 1) — note in description it affects `be.bankdekremer.mobile` too (shared codebase).

## Endpoint / vulnerable component
```
be.bankvanbreda.mobile & be.bankdekremer.mobile — Conversations feature: ConversationDetailPage / ConversationDetailVM.HTMLSource (HTMLHelper.GetHTMLChatMessageSource), WebView configured in CustomWebViewHandler.cs
```

## Type
`CWE-79 Stored Cross-Site Scripting`

## Severity (CVSS)
`AV:N/AC:L/PR:L/UI:R/S:U/C:L/I:L/A:N` = **4.6 (Medium)**

## IP address used for testing
`15.237.193.228` (static analysis of client binaries only — no live requests were sent to bank infrastructure)

## Recommended solution
```
HTML-encode the message body and sender name on output (do not HtmlDecode untrusted content into an HTML context), or render message content as text rather than HTML. Sanitize server-side on store and return with a strict allowlist. Additionally, disable AllowUniversalAccessFromFileURLs / AllowFileAccessFromFileURLs and remove the global jsBridge exposure on any WebView that renders user-supplied content.
```

---

## Proof of Concept / description  ← paste everything below this line into that field

## Summary

The in-app **Conversations** (secure-messaging) feature of both mobile apps (identical shared codebase, `BVB.EOS.OnlineBanking.UI.Mobile`) renders message content into an Android `WebView` that has JavaScript enabled, a native JavaScript bridge (`jsBridge`) bound, and universal file-URL access — while applying **no HTML output encoding** to the message body or sender name. The message body is passed through `WebUtility.HtmlDecode()` (the opposite of escaping) before being interpolated into the rendered HTML, so any markup in a stored message becomes live DOM. The customer send path applies no encoding either.

**This report affects both `be.bankvanbreda.mobile` and `be.bankdekremer.mobile`** — they are the same white-labeled codebase differing only in branding.

> **Scope of what is proven:** the client-side injection sink is confirmed from decompiled client code (no obfuscation on this path). Escalation to **stored cross-user XSS** — the high-severity case in a banking app — depends on server-side behaviour that requires an authenticated account to verify (see *Verification status*). The CVSS above reflects the confirmed client-side sink; **if cross-user stored XSS is confirmed, this rises to High/Critical (C:H / I:H).**

## Technical detail

**Render sink** — `ConversationDetailPage` → WebView `Html` bound to `ConversationDetailVM.HTMLSource`, built per-message by `HTMLHelper.GetHTMLChatMessageSource(msg)`, which interpolates `{WebUtility.HtmlDecode(msg.Body)}` and raw `{msg.SenderFullName}` directly into the HTML string.

**WebView configuration** (`CustomWebViewHandler.cs`) — mapped globally for every MAUI `WebView` in the app:

```csharp
webView.Settings.JavaScriptEnabled = true;
webView.Settings.AllowFileAccess = true;
webView.Settings.AllowFileAccessFromFileURLs = true;
webView.Settings.AllowUniversalAccessFromFileURLs = true;
webView.AddJavascriptInterface(new JsBridge(this), "jsBridge");
webView.SetWebViewClient(new InternalWebViewClient());
```

**Native bridge** — `JsBridge.InvokeAction(string data)` (`[JavascriptInterface]`) forwards a JS-supplied string to the hosting page's `InteractCommand`, so injected JavaScript in a rendered message can reach a native code path via `jsBridge.invokeAction(...)`.

**Send path** — `Communication.AddMessage(string body, …)` / `CreateConversation(string body, …)` assign `Body = <raw string>` with no HTML encoding or sanitization.

**Net:** the app both sends and renders conversation content unescaped into a JS-enabled WebView with a native bridge. `HtmlDecode` guarantees stored markup becomes live DOM.

## Steps to reproduce

*Deliberately broad — please test all payload variants so a narrow test does not produce a false negative.* Prerequisite: one (ideally two) authenticated test accounts.

**Part A — confirm the stored sink (single account):**
1. Log in, open **Conversations**, start/open a conversation.
2. Send a message whose body is each of the following (test all — different payloads survive different server-side filters):
   - `<img src=x onerror="alert(document.domain)">`
   - `<script>alert(document.domain)</script>`
   - `<svg/onload=alert(1)>`
   - `<img src=x onerror="jsBridge.invokeAction('xss-poc')">` — proves native-bridge reach
   - `&lt;img src=x onerror=alert(1)&gt;` — proves the `HtmlDecode` step re-activates encoded markup
3. Reopen/refresh the conversation so `ConversationDetailPage` re-renders.
4. **Observe:** execution confirms the server stored and returned the body without sanitization — i.e. stored XSS, not merely self-XSS.

**Part B — confirm cross-user reach (two accounts):**
5. From account 1, address a message to account 2 with receiver type `OLBUSER` (the `ReceiverTypeCodes` enum models `OLBUSER` = online-banking user), using each Part-A payload as the body.
6. Log in as account 2, open the received conversation.
7. **Observe:** execution here is the cross-user stored XSS case.

**Part C — template-merge path (if Part B is blocked):**
8. Check whether the server-set `templateMergeContent` field on bank-authored message templates merges any attacker-influenced value (e.g. a counterparty name/reference from a transaction). If a merged value renders unescaped, it is a second cross-user path.

## Impact

- **Confirmed (client-side):** self-XSS — a customer who stores HTML/JS in a message body has it execute in their own app's WebView on render.
- **Potential (pending your verification):** if the server stores/returns the body verbatim and permits addressing another customer, this becomes **stored cross-user XSS** inside an authenticated banking session, with reach into native functionality via `jsBridge.invokeAction` — a high-severity outcome (session/data exposure, potential unauthorized in-app actions).

## Verification status (full transparency)

- **Verified by me** (static analysis of decompiled client — no obfuscation on this path): the render sink un-encodes the body via `HtmlDecode` into a JS-enabled WebView with a native bridge; the send path applies no encoding; together these make the self-XSS case demonstrable from client code.
- **Not verified — requires an authenticated account:** (a) does the server sanitize the body on store/return? (b) does the server permit a customer to address an `OLBUSER` message to another customer? (c) does any `templateMergeContent` template render an attacker-influenced value?
- **Why I could not verify it myself:** account onboarding for this program requires Belgian self-employed / entrepreneur / liberal-profession eligibility, which I do not meet as an international researcher, and no self-serve test/sandbox account is available to me. I am disclosing this now with complete reproduction steps so the team can confirm the escalation directly.

**Offer to complete verification myself (recommended):** If confirming this internally is complex or time-consuming on your side, I would welcome one or two read-only test/sandbox accounts so I can complete the verification myself, document the full reproduction with evidence, and continue testing the related authenticated surfaces (including a client-supplied `AccountID` authorization pattern I identified in `GetAccountTransactions` and five sibling contracts) for further issues. I will test only my own accounts and never touch real customer data, and am happy to work within any constraints (scoped test account, monitored window, specific hosts).

---

## Additional note for the description (optional — the unverified IDOR lead)

You may include this at the end of the description, or omit it. It is **not** a claimed finding:

> Additional lead (NOT a claimed finding): `GetAccountTransactions` and five sibling contracts (`GetDepositAccount`, `GetScheduledTransactions`, `GetStandingOrders`, `CardHolderDto`, `CreateUserDefinedNotificationDto`, `ModifyUserDefinedNotificationDto`) accept a client-supplied `AccountID` (`Guid?`). Whether the server authorizes it against the session owner is not observable from the client — flagged only as the natural first authorization test if credentials are provided. I have no evidence of a server-side flaw; this is a pointer, not a report.
