# Bank J.Van Breda & C° — Security Vulnerability Report

**Researcher:** treyky (Intigriti)
**Target:** `be.bankvanbreda.mobile` (VanBredaOnline) & `be.bankdekremer.mobile` (Bank de Kremer) — shared codebase `BVB.EOS.OnlineBanking.UI.Mobile`
**Report title:** Improper Output Encoding in Conversations WebView (Client-Side HTML/JS Injection Sink; Potential Stored Cross-User XSS)
**Date:** 2026-09-19

---

## EXECUTIVE SUMMARY

### 1. Key Findings
Static analysis of the two mobile banking apps (identical shared codebase) identified that the in-app
**Conversations** secure-messaging feature renders message content into an Android WebView that has
JavaScript enabled, a native JavaScript bridge (`jsBridge`) bound, and universal file-URL access —
while applying **no HTML output encoding** to the message body or sender name. The message body is
passed through `WebUtility.HtmlDecode()` (the opposite of escaping) before being interpolated into the
rendered HTML, guaranteeing that markup in a stored message becomes live DOM.

### 2. Highest-Risk Vulnerability
The Conversations output-encoding flaw is the highest-risk item. It is a **confirmed client-side
injection sink** (self-XSS demonstrable from decompiled client code). Its escalation to **stored
cross-user XSS in an authenticated banking session** — the high-severity case — depends on server-side
behavior that static analysis cannot observe and that requires an account to verify.

### 3. Recommended Controls
Apply HTML output-encoding to message body and sender name on render; sanitize server-side on
store/return; and reduce the WebView's `AllowUniversalAccessFromFileURLs` / `jsBridge` exposure on any
view that renders user-supplied content.

### 4. Overall Assessment
One confirmed client-side vulnerability with credible high-severity escalation potential, plus one
unverified authorization lead flagged for the program's awareness. Full verification of the
high-severity case is blocked by an account-access barrier described under Verification Status.

---

## VULNERABILITY FINDINGS

Findings identified:
- **Conversations WebView — improper output encoding (HTML/JS injection sink)** — *confirmed (client-side)*
- **Client-supplied `AccountID` GUID authorization surface** — *unverified lead, not a claimed finding*

| Vulnerability Name | Affected Component | Brief Description | Attacker Goal |
|---|---|---|---|
| **Conversations WebView Improper Output Encoding** | `ConversationDetailPage` / `ConversationDetailVM.HTMLSource`, built by `HTMLHelper.GetHTMLChatMessageSource(msg)`; WebView configured in `CustomWebViewHandler.cs` | The message body is interpolated as `{WebUtility.HtmlDecode(msg.Body)}` and the sender name raw (`{msg.SenderFullName}`) into an HTML string rendered by a WebView with `JavaScriptEnabled=true`, `AllowFileAccessFromFileURLs=true`, `AllowUniversalAccessFromFileURLs=true`, and a native bridge `AddJavascriptInterface(new JsBridge(...), "jsBridge")`. `HtmlDecode` un-escapes stored markup so it becomes live DOM. The send path (`Communication.AddMessage` / `CreateConversation`) also applies no encoding. **Self-XSS is demonstrable from the client code.** | Store HTML/JS in a message body so it executes in the WebView on render; via `jsBridge.invokeAction()` reach a native code path. If the server stores/returns the body unsanitized and permits addressing another customer, escalate to **stored cross-user XSS** inside an authenticated banking session. |
| **Client-supplied `AccountID` GUID** *(unverified lead — NOT a claimed finding)* | `GetAccountTransactions` and siblings (`GetDepositAccount`, `GetScheduledTransactions`, `GetStandingOrders`, `CardHolderDto`, `CreateUserDefinedNotificationDto`, `ModifyUserDefinedNotificationDto`) | These request contracts accept a client-settable `AccountID` field (JSON `"accountID"`, type `Guid?`). Whether the server verifies the supplied GUID belongs to the authenticated customer is not observable from the client. **No evidence of a server-side flaw exists** — flagged only as the natural first authorization test if credentials are provided. | (If a server-side authorization gap exists) read another customer's account/transaction data by supplying their `AccountID`. Requires a leaked GUID; not brute-forceable (GUID, not sequential). |

---

## PROOF OF CONCEPT / REPRODUCTION STEPS

*(Deliberately broad — please test all payload variants so a narrow test does not produce a false negative.)*

**Prerequisite:** one (ideally two) authenticated test accounts on VanBredaOnline or Bank de Kremer.

**Part A — confirm the stored sink (single account):**
1. Log in, open **Conversations**, start/open a conversation.
2. Send a message whose body is each of the following (test all — different payloads survive different server-side filters):
   - `<img src=x onerror="alert(document.domain)">`
   - `<script>alert(document.domain)</script>`
   - `<svg/onload=alert(1)>`
   - `<img src=x onerror="jsBridge.invokeAction('xss-poc')">` — proves native-bridge reach
   - `&lt;img src=x onerror=alert(1)&gt;` — proves the `HtmlDecode` step re-activates encoded markup
3. Reopen/refresh the conversation so `ConversationDetailPage` re-renders.
4. **Observe:** execution confirms the server stored and returned the body without sanitization — i.e. **stored XSS**, not merely self-XSS.

**Part B — confirm cross-user reach (two accounts):**
5. From account 1, address a message to account 2 with receiver type `OLBUSER` (the `ReceiverTypeCodes` enum models `OLBUSER` = online-banking user), using each Part-A payload as the body.
6. Log in as account 2, open the received conversation.
7. **Observe:** execution here is the **cross-user stored XSS** case.

**Part C — template-merge path (if Part B is blocked):**
8. Check whether the server-set `templateMergeContent` field on bank-authored message templates merges any attacker-influenced value (e.g. a counterparty name/reference from a transaction). If a merged value renders unescaped, it is a second cross-user path.

---

## RISK ASSESSMENT

| Vulnerability | Likelihood | Impact | Risk Rating |
|---|---|---|---|
| Conversations WebView Improper Output Encoding | Medium | High *(if cross-user confirmed)* / Low *(self-XSS only)* | **Medium — High if server-side escalation confirmed** |
| Client-supplied `AccountID` GUID *(unverified lead)* | Unknown | Unknown | **Not rated — requires verification; no evidence of a flaw** |

**Brief explanation of the ratings:**
1. **Conversations WebView Improper Output Encoding (Medium, escalating to High):** the client-side sink is confirmed with no obfuscation caveat — the injection point is real and unambiguous. Impact hinges on server behavior: if it is only self-XSS, impact is Low; if the server stores/returns unsanitized content and permits cross-customer messaging, it becomes stored XSS in an authenticated banking session with native-bridge reach — a High-impact outcome. Severity is therefore stated as Medium with explicit High escalation pending the account-only verification below.
2. **Client-supplied `AccountID` GUID (Not rated):** this is a pointer, not a finding. There is no evidence the server fails to authorize the supplied GUID; rating it would be speculation. Included only so the program can prioritize it during any future credentialed testing.

---

## RECOMMENDED CONTROLS

| Vulnerability | Recommended Control | How This Control Reduces Risk |
|---|---|---|
| Conversations WebView Improper Output Encoding | Output Encoding & Server-Side Sanitization | HTML-encode `msg.Body` and `msg.SenderFullName` on output (do not `HtmlDecode` untrusted content into an HTML context), or render as text rather than HTML. Sanitize server-side on store and return with a strict allowlist. This removes the injection sink entirely. |
| WebView configuration | Least-Privilege WebView Configuration | Disable `AllowUniversalAccessFromFileURLs` / `AllowFileAccessFromFileURLs` and remove the global `jsBridge` exposure on any WebView that renders user-supplied content, limiting the blast radius if any injection reaches the WebView. |
| Client-supplied `AccountID` GUID *(if verification confirms a gap)* | Server-Side Authorization Enforcement | Ensure every request carrying a client-supplied `AccountID` is authorized server-side against the authenticated session's own customer, so a supplied identifier cannot reference another customer's resource. |

---

## VERIFICATION STATUS (full transparency)

- **Verified by me** (static analysis of decompiled client — no obfuscation on this path; `HTMLHelper` was cleanly readable): the render sink un-encodes the body via `HtmlDecode` into a JS-enabled WebView with a native bridge; the send path applies no encoding; together these make the self-XSS case demonstrable from client code.
- **Not verified — requires an authenticated account:** (a) does the server sanitize the body on store/return? (b) does the server permit a customer to address an `OLBUSER` message to another customer? (c) does any `templateMergeContent` template render an attacker-influenced value? For the `AccountID` lead: does the server authorize the supplied GUID against the session owner?
- **Why I could not verify it myself:** account onboarding for this program requires Belgian self-employed / entrepreneur / liberal-profession eligibility, which I do not meet as an international researcher, and no self-serve test/sandbox account is available to me. I have separately asked the program whether read-only test credentials can be provided. I am disclosing this now with complete reproduction steps so the team can confirm the escalation directly.

**Offer to complete verification myself (recommended):** Verifying the high-severity escalation of this
finding requires server-side behaviour that is only observable from an authenticated session —
specifically whether message content is sanitised on store/return and whether cross-customer messaging
is permitted. If confirming this internally is complex or time-consuming on your side, I would welcome
being provided with one or two read-only test/sandbox accounts so I can complete the verification
myself, document the full reproduction with evidence, and continue testing the related authenticated
surfaces (including the client-supplied `AccountID` authorization pattern noted above) for further
issues. I am happy to work within any constraints you set — a scoped test account, a monitored testing
window, or specific hosts — and will test only my own accounts and never touch real customer data.

---

## CONCLUSION

The Conversations messaging feature contains a confirmed client-side HTML/JS injection sink caused by
decoding message content into a JavaScript-enabled WebView with a native bridge and no output encoding.
Self-XSS is demonstrable from the client code; whether it escalates to stored cross-user XSS — a
high-severity outcome in a banking application — depends on server-side behaviors that require an
account to verify, which is currently blocked by an eligibility barrier. Applying output encoding and
server-side sanitization, and reducing the WebView's file-access and bridge exposure, removes the sink.
The client-supplied `AccountID` GUID pattern is flagged separately as an unverified authorization lead
for future credentialed testing, not as a claimed finding.
