# Context, requirements and sample data

[← Back to the index](README.md)

Purpose of the product, the brief's requirements restated, and what the sample data reveals.

## Purpose and business objectives

| | |
|---|---|
| **Product purpose** | Lawyers get an AI review of a contract that they can **trust** and **afford**. |
| **Business constraints** | Reviews are **slow** (5–30 s, sometimes over 60 s), **unreliable** (about 30% fail), and **scarce** (10 per month, shared by the firm). |
| **PM objective** | Responsiveness and convenience: never wait in front of nothing, see value early, don't have to come back. |
| **Customer objective** (senior partner, who pays) | Trust and cost control: never mistake a non-final result for a final one, never spend a review unknowingly, never be misled about when a review will happen. |
| **Evaluation objective** | Correct rules, product judgment, explicit decisions (including what we refused), proportionate architecture, tests, and documentation. |

**Product principle used to settle the conflicts:** in a legal product, a wrong belief costs more than a wait. A lawyer who acts on a partial or outdated result exposes the firm to professional liability. So **the customer's trust constraints are hard constraints**, and **the PM's goals are met wherever they don't break them**.

---

## Requirements as stated (normalized)

| ID | Type | Requirement (from the brief) |
|---|---|---|
| F1 | Flow | A lawyer sees the workspace's documents and, for each one, the state of its **latest** review. |
| F2 | Flow | A lawyer requests an AI review of a document and **follows it until it completes or fails**. |
| F3 | Flow | A lawyer reads a completed review: flagged clauses, each with **severity** and **explanation**. |
| R1 | Rule | **10 reviews per calendar month** for the **whole workspace**. **Failed reviews don't count.** |
| R2 | Rule | **At most one review in progress per document**, whoever requested it. |
| R3 | Rule | The fake AI returns the document's findings **one at a time** over **5–30 s**. About **1 in 5** runs fail with an error after returning some or none of the findings. About **1 in 10** runs are slow and finish after **60–120 s**. |
| R4 | Rule | A review still in progress **60 s after it was requested** has **failed permanently**. Later findings or completion **must not** turn it into a completed review or consume the plan. **A retry is a new review.** |
| R5 | Rule | **No authentication.** The current user is chosen in the UI from the 3 lawyers. |
| D1–D3 | Decision | Take a position on the previous review, on early findings, and on requests beyond the plan. |
| C1 | Constraint | Not in scope: upload, parsing, auth, billing, real AI. One workspace. |
| C2 | Constraint | Web frontend + backend API + relational DB (SQLite is fine). |
| C3 | Constraint | 4 h timebox. Prefer smaller and clearer. Document what's unfinished and the time spent. |
| C4 | Deliverable | Git repo. README with run/test instructions, decisions and their reasons, assumptions, limitations, time, AI tools used. AI session log. |

---

## What the data tells us ("read the data: it is part of the brief")

| # | Observation | Consequence |
|---|---|---|
| D-1 | 13 documents, 3 lawyers: Chiara (Partner), Riccardo (Senior associate), Sofia (Trainee lawyer). | Titles suggest a hierarchy, but **no permissions are defined** (see Q4). |
| D-2 | **Commercial lease — Via Tortona 12** exists twice. `a8d4…` (v2, 19 pages, 24 Sep) **supersedes** `125c…` (v1, 18 pages, 3 Sep). Same title. | The list must tell them apart: upload date, plus a clear **"Previous version"** label on v1. Whether v1 can be reviewed again is open (Q6). It is allowed for now. Between versions, finding 8.3 disappears (fixed), 4.2 remains, and 12.1 is new. |
| D-3 | **Consulting agreement — Delta Advisory** has `findings: []`. | A **completed review with 0 findings** is a legitimate, billable outcome. It must be visually distinct from every non-final state. |
| D-4 | **Franchise agreement — Kappa Coffee** has **16 findings**. | It stress-tests streaming: one finding every ~0.3–2 s. The final list is long; it is sorted by severity (BR-17). |
| D-5 | 3 findings have `clause: null` **and** `excerpt: null` (NDA "governing law", SaaS "DPA", Shareholders "deadlock"). These are *missing*-clause findings. | The UI needs explicit copy: *"General — concerns something missing from the contract"*. Never render "null" or an empty quote. |
| D-6 | Clauses are strings: `"12"`, `"7"`, `"20"`, `"4.2"`, `"16.1"`. | Use **natural sort** (4.2 < 12 < 16.1). Lexical sort gives "12" < "4.2". |
| D-7 | Within each document, findings are **not** sorted by severity (e.g. NDA: 5.1 high, 3.2 medium, — low; Franchise mixes them). | The order is the "AI's order". Decide the display order: see BR-17. |
| D-8 | Findings have **no id**. | We generate one (`review_id` + `seq`) for streaming keys and deduplication. |
| D-9 | Severity values are only `high`, `medium`, `low`. | Use a closed enum. Validate at seed time. |
| D-10 | No workspace, plan or review entities exist in the data. | We introduce them. The initial state is "every document not reviewed, 10 of 10 available". |
| D-11 | The fake AI returns **the same findings every time** for a document. | Re-reviewing an unchanged document spends a review for an identical result. Allowed, as the brief doesn't restrict it. |
| D-12 | `uploadedBy` references valid lawyers (Sofia 3, Chiara 5, Riccardo 5). | Show it in the list. It is useful context, not a permission. |
| D-13 | The brief says `samples/documents.json`, but the files were delivered at the repository root. | Resolved: moved to `samples/` to match the brief. |
