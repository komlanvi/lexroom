# Scope and questions

[← Back to the index](README.md)

What is built within the 4-hour timebox, and the questions raised with their status.

## Scope for the 4-hour timebox

| Priority | Item |
|---|---|
| **Must** | Seed from JSON. Identity picker + header switch. Document list with latest-review badge and plan counter. Request with confirmation. Server transaction with stale expiry, R2 and quota reservation. Fake AI with injectable RNG and clock. Conditional writes + lazy expiry + sweeper. Live panel with findings marked Partial. Previous result marked "no longer current". "Previous version" label on superseded documents. Final view sorted. Failure view + retry. Strict block when the plan is used up. Tests on rules: quota, reservation, deadline boundary, late events, concurrency on the same document, failure not counted. README with decisions. |
| **Should** | "Completed · no clauses flagged" copy. Natural clause sort. Connection-lost banner. E2E test of a full run with a fast fake. |
| **Won't** | Anything the PDF does not specify. Queue beyond the plan (refused). Any partial or previous result without its marking (refused). Cancellation. Per-lawyer quotas or role permissions. Authentication, upload, parsing, billing, real AI (excluded by the brief). Every item in [Future improvements](11-future-improvements.md). |

---

## Questions and decisions

| # | Question | Status | Answer |
|---|---|---|---|
| Q1 | Which timezone defines the calendar month? | **Decided** | Europe/Rome. |
| Q2 | Does a review straddling month end count in the month of the request or of the result? | **Decided** | Month of the request (`requested_at`). See A3 and BR-4. |
| Q4 | Do trainees need approval to spend the shared plan? | **Decided** | No. The brief mentions no approval and no roles, so all three lawyers have the same rights. |
| Q5 | Can a running review be cancelled? | **Decided** | No. The brief doesn't mention cancellation, so it is not built (listed in [Future improvements](11-future-improvements.md)). |
| Q6 | Can a superseded document be reviewed again? | **Open** (not addressed by the brief) | **Decided:** the superseded document is clearly labelled **"Previous version"** (with the newer version's date), and its completed reviews stay readable. **Current assumption, pending an answer:** it can still be reviewed like any other document, since the brief doesn't forbid it. |
| Q7 | What are the possible outcomes of a fake AI run? | **Decided** | Exactly one of three, mutually exclusive: **error** (~1 in 5), **slow** (~1 in 10, always ends as a timeout), or **completed** (the rest). |

Q3 (access to failed reviews) was dropped: the brief doesn't mention it. [Interpretation](03-decisions.md#interpretation-completed-reviews-vs-failed-reviews) covers what is displayed.
