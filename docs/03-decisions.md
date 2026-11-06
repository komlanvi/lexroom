# The three contested points: decisions

[← Back to the index](README.md)

## Interpretation: completed reviews vs failed reviews

Neither the PM ("keep the previous one on screen") nor the senior partner ("never mistake an old or partial result for the final one") says whether failed reviews are included. We resolve it from the rest of the brief:

| Evidence in the brief | Consequence |
|---|---|
| Flow F3: a lawyer *"reads the result of a **completed** review"*. | Only completed reviews have a readable result. |
| Flows F1/F2: the list shows *"the **state** of its latest review"*, and the lawyer follows a review *"until it completes or fails"*. | A failed review appears as a **state**, not as a result. |
| *"Has failed permanently"*, *"don't count against the plan"*, *"a retry is a new review"*. | The brief treats a failed review as a non-result. |
| PM: *"never wait in front of nothing"*. | A failed review gives nothing to read, so the "previous one" that serves this goal is the **previous completed** review. |
| Senior partner: *"old or partial result"*. | This constrains whatever we display. Partial findings exist while a review runs (shown, marked "Partial", point 2) and in failed reviews (not shown at all). |

**Assumption (to be recorded in the README):**

- The main screen shows the **current completed review** and, while a new review runs, the **previous completed review** marked "no longer current". Failed reviews are skipped when determining "previous".
- A failed review is displayed only as a **status**: failed, reason, time, requester, not counted, Retry. Its partial findings stay stored but are not shown in the UI.
- Completed reviews remain viewable for **every** document, including superseded ones. A lawyer may need the review of an earlier version, or of a contract already negotiated or executed, for the full history and context of the matter.
- If the customer later wants access to failed reviews, the answer is a dedicated, less prominent **Review History** section ([Future improvements](11-future-improvements.md)). It is not part of this build.

## Point 1 — The previous review while a new one runs

| | |
|---|---|
| **PM** | "Never wait in front of nothing: keep the previous one on screen." |
| **Customer** | "Never mistake an old result for the final one." |
| **Real conflict?** | Only if the old result is shown *as if it were current*. Showing it is not the problem; mislabelling it is. |
| **Decision** | **Keep the previous completed review, clearly marked as no longer current.** Failed reviews in between are skipped ([Interpretation](03-decisions.md#interpretation-completed-reviews-vs-failed-reviews)). While a new review runs, the live review takes the top of the panel. The previous result stays visible below it, under a header: *"Previous result · 2 Nov 2026, 14:03 · requested by Chiara · no longer current: a new review is in progress."* Every card carries a **"Previous"** tag and a muted style. The two lists are never merged. |
| **If the new review completes** | It becomes the current result. The previous one is no longer displayed (it stays stored). |
| **If the new review fails** | The previous completed review is the current result again, and its "no longer current" marking is removed. A status line above it reads *"Latest attempt failed (time limit) at 14:10 · not counted · [Retry]. The result below is from 2 Nov."* |
| **If there is no previous completed review** | Nothing is shown below the live review. If that review fails, the panel shows the failure status and "No completed review yet". |
| **Refused** | Showing the previous findings without a label, or merged with the new ones. |
| **Why** | The PM gets "never wait in front of nothing", and the explicit marking gives the customer "impossible to read as final". |

## Point 2 — Findings before the review has finished

| | |
|---|---|
| **PM** | "Show each finding as soon as the AI returns it." |
| **Customer** | "Whatever isn't final must be impossible to read as final." |
| **Decision** | **Show them, clearly marked as partial** (same principle as point 1). Findings appear one by one in arrival order. The container carries a persistent banner: *"Review in progress — 3 findings received so far. This list is incomplete: more may arrive, and the review may still fail."* Cards use a **draft style** (dashed border, "Partial" tag, muted severity). **No totals or severity summary** while running. An elapsed timer shows progress against the 60 s limit. |
| **On completion** | The "Partial" tags disappear, the list is re-sorted by severity, and a "Final · completed at 14:03:22" badge is shown. This visual change is the signal of finality. |
| **On failure** | The partial findings are removed from the main screen ([Interpretation](03-decisions.md#interpretation-completed-reviews-vs-failed-reviews)). Only the status remains: *"Review failed after 14 s (AI error). It did not count against the plan. [Retry]"*. Below it is the last completed review, if there is one. The partial findings stay stored in the DB. |
| **Refused** | Presenting a running review's findings without the "Partial" marking. Showing totals before completion. Showing a failed review's findings on the main screen. |
| **Why** | Early findings give the PM's "show each finding as soon as the AI returns it", and the explicit marking gives the customer "whatever isn't final must be impossible to read as final". |

## Point 3 — Requests beyond the plan

| | |
|---|---|
| **PM** | "Take the request anyway and run it when the plan resets." |
| **Customer** | "Nobody spends a review without knowing it. Nobody should believe a review is on its way when it won't start for three weeks." |
| **Decision** | **Strict block. There is no queue.** Once the plan is used up, nobody can start a new review. The request button is disabled and explains why: *"The workspace has used its 10 reviews for November. Reviews are available again on 1 Dec 2026, 00:00 (Rome time) — in 24 days."* If the counter is at 0 only because reviews are still in progress, a dedicated message explains it ([Wireframes](06-screens-and-ui-states.md#wireframes-low-fidelity)). **Every** request goes through a confirmation that states its cost ([Wireframes](06-screens-and-ui-states.md#wireframes-low-fidelity)). |
| **User flow** | Out of reviews → wait for the reset. Nothing else is offered (see [Future improvements](11-future-improvements.md) for ideas outside this scope). |
| **Why** | It is the simplest behaviour, and it avoids the tensions a queue would create with R4 and R2 (F1, F2). It also never spends a review without someone deciding to, and never suggests that a review is on its way when it isn't. |
