# Lexroom · Contract Review Flow — Product & Technical Analysis

Sources: `Business Case - Senior Full Stack Engineer .pdf`, `samples/documents.json`, `samples/lawyers.json`.
Perspective: Senior Product Owner with a Senior Software Engineer background.

## Documents

| Topic | File |
|---|---|
| [Context, requirements and sample data](01-context-and-requirements.md) | 01-context-and-requirements.md |
| [Pitfalls, ambiguities and assumptions](02-issues-and-assumptions.md) | 02-issues-and-assumptions.md |
| [The three contested points: decisions](03-decisions.md) | 03-decisions.md |
| [Domain model and business rules](04-domain-model-and-business-rules.md) | 04-domain-model-and-business-rules.md |
| [User flows and sequence diagrams](05-user-flows.md) | 05-user-flows.md |
| [Screens and UI states](06-screens-and-ui-states.md) | 06-screens-and-ui-states.md |
| [Error and edge-case catalogue](07-errors-and-edge-cases.md) | 07-errors-and-edge-cases.md |
| [API contract (sketch)](08-api-contract.md) | 08-api-contract.md |
| [Acceptance criteria (Given / When / Then)](09-acceptance-criteria.md) | 09-acceptance-criteria.md |
| [Scope and questions](10-scope-and-questions.md) | 10-scope-and-questions.md |
| [Suggestions for future improvements](11-future-improvements.md) | 11-future-improvements.md |

## Identifiers used across the documents

| Prefix | Meaning | Defined in |
|---|---|---|
| F1–F3, R1–R5, C1–C4 | Flows, rules and constraints from the brief | [Context and requirements](01-context-and-requirements.md) |
| D-1 … D-13 | Observations on the sample data | [Context and requirements](01-context-and-requirements.md) |
| A1 … G6 | Pitfalls and assumptions, grouped by topic (A plan, B lifecycle, C concurrency, D reading, E identity, F tensions, G technical) | [Pitfalls and assumptions](02-issues-and-assumptions.md) |
| BR-1 … BR-22 | Normative business rules | [Domain model and business rules](04-domain-model-and-business-rules.md) |
| Q1 … Q7 | Questions and their status | [Scope and questions](10-scope-and-questions.md#questions-and-decisions) |

---

## TL;DR

**What we build:** one law-firm workspace, three lawyers, 13 documents, a *fake* AI reviewer, and three flows:

1. **Browse:** list the documents and show the state of each one's latest review.
2. **Request & follow:** request an AI review and follow it live until it completes or fails.
3. **Read:** read a completed review, meaning the flagged clauses with their severity and explanation.

**The real difficulty is not the UI.** It is three invariants that must hold under concurrency, slow and failing AI runs, and closed browsers:

- **The quota:** at most 10 *successful* reviews per calendar month for the whole workspace.
- **One review in progress per document**, no matter who requested it.
- **A hard 60-second deadline from the request.** Anything that arrives after it is ignored, and it never consumes the plan.

**Decisions on the three contested points:**

| Point | Decision | In one line |
|---|---|---|
| 1. Previous review while a new one runs | **Keep the previous *completed* review, clearly marked as no longer current** | It stays on screen, labelled *"Previous result · date · by · no longer current"*, and is never mixed with the new one. Failed reviews are skipped: "previous" means the last completed review. |
| 2. Findings before the review finishes | **Show them, clearly marked as partial** | Same principle as point 1. Findings appear as they arrive, marked *"Partial"* with an *"Incomplete"* banner and no totals. They become "final" only on completion. If the review fails, they are removed from the main screen. Only the failure status remains. |
| 3. Requests beyond the plan | **Strict block. No queue** | Once the plan is used up, no new review can be started until the plan resets. The button is disabled with the reason and the exact reset date. |

**One principle covers points 1 and 2:** anything that is not the current, final result is shown, but always explicitly marked as such ("Previous", "Partial"), so it can never be read as final.

**Scope of the main screen:** only completed reviews have a readable result (flow F3: "reads the result of a completed review"). A failed review is shown only as a **status** (failed, reason, not counted, Retry), never with its findings. See [Interpretation](03-decisions.md#interpretation-completed-reviews-vs-failed-reviews).

**The eight traps most likely to be missed:**

1. Counting the quota only on completion lets concurrent reviews overspend it (9 used + 3 running = 12). **The slot must be reserved at request time.**
2. The "slow" path (60–120 s) **always** breaches the 60 s deadline. With the 1-in-5 error rate on top, about 30% of reviews fail. Failure is a normal path, not an exception.
3. Queuing requests beyond the plan would conflict with two rules in the brief (the 60 s deadline, and one review in progress per document), unless we invented a "queued" state the brief never defines. The strict block avoids this.
4. "No findings" can mean four different things. The *Consulting agreement* has **0 findings by design**, so "completed with nothing flagged" must look different from "not reviewed", "running, nothing yet" and "failed".
5. The *Commercial lease* exists **twice** (v2 supersedes v1, same title).
6. 3 findings have **no clause and no excerpt**. Clause numbers are strings ("12", "4.2", "16.1") and need natural sorting.
7. The deadline must be enforced **server-side with conditional writes**, not by a timer in the browser or in the fake AI.
8. A row that is past its deadline but not yet marked failed must not block new requests or hold a quota slot. **Expire stale rows inside the request transaction.**
