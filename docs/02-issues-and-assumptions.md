# Pitfalls, ambiguities and assumptions

[← Back to the index](README.md)

Each item lists the observation, why it matters, and the **decision or assumption** taken. Open questions for stakeholders are in [Questions and decisions](10-scope-and-questions.md#questions-and-decisions).

## A. Plan / quota

| ID | Issue | Why it matters | Decision |
|---|---|---|---|
| A1 | The brief counts a review **when it succeeds**, but the decision to spend is made **at request time**. | With 9 used, three parallel requests on three documents all pass a "used < 10" check. If all three complete, the firm has used 12. **This breaks R1.** | **Reserve a slot at request time.** `available = 10 − completed(month) − running(not expired)`. A request is accepted only if `available ≥ 1`. The slot is **consumed** on completion and **released** on failure or timeout. |
| A2 | Reservations make a slot look unavailable even though the running review may fail (≈30%). | A lawyer might see "0 left" and give up when a slot will free up within a minute. When `available = 0` and `running > 0`, show an explicit message: why no review can start (completed + in progress = 10), that a review in progress frees its slot if it fails (within 60 s at most), and that the request was **not** saved and won't start on its own (wireframe in [Wireframes](06-screens-and-ui-states.md#wireframes-low-fidelity)). |
| A3 | Which month does a review belong to if it is requested at 23:59:40 on the 31st and completes at 00:00:05 on the 1st? | It could be counted twice, or in the wrong month. | **The month of the request (`requested_at`), in Europe/Rome** (decided, Q2). That is when availability was checked, the slot reserved and the cost confirmed, so the lawyer always knows which month's plan is used. `available = 10 − completed requested this month − running requested this month`. A review requested on 30 Nov that completes on 1 Dec counts in November. December starts with 10 available, whatever is still running at midnight. |
| A4 | "Calendar month" in **which timezone**? | UTC and Milan differ by 1–2 h. The counter would reset at 01:00 or 02:00 local time. | **Europe/Rome** (decided, Q1). Store UTC and compute period boundaries in Europe/Rome, with DST handled. Display: *"Resets 1 Dec, 00:00 (Rome time)"*. |
| A5 | The quota is **workspace-wide**. One lawyer can use all 10. | It is a fairness and governance concern, especially with a trainee on the team. | Allowed (the brief sets no per-lawyer limit). Every review shows **who requested it**. |
| A6 | Re-reviewing a document that already has a completed review. | The result is identical (D-11), so the review is wasted. | Allowed, no special handling (the brief has no rule on it). A warning is listed in [Future improvements](11-future-improvements.md). |
| A7 | Reviewing a **superseded** version (Lease v1). | It spends a review on an outdated contract. | Allowed for now (assumption, Q6 still open). The document is clearly labelled "Previous version · superseded by the version of {date}" in the list and on its detail page. A confirmation warning is listed in [Future improvements](11-future-improvements.md). |
| A8 | A review completes **after** its deadline. | The brief says it must not count. | Enforced by a conditional write (BR-9). |
| A9 | The counter shown in the UI can be stale (another lawyer just spent a review). | The confirmation could promise a slot that is gone. | **The server is authoritative.** It re-checks inside the request transaction and returns `409 PLAN_EXHAUSTED` with clear copy. The counter refreshes on every poll. |
| A10 | Plan size and timeout are business parameters. | Tests and future plans need other values. | Make them config: `PLAN_LIMIT=10`, `REVIEW_TIMEOUT_S=60`, `PLAN_TZ=Europe/Rome`. |

## B. Review lifecycle, deadline and late events

| ID | Issue | Why it matters | Decision |
|---|---|---|---|
| B1 | The deadline is "**60 s after it was requested**", not after the AI started. | Any waiting before execution eats into the 60 s. A queue would need its own clock (see F1); the strict block in point 3 avoids this. | `deadline_at = requested_at + 60 s`, stored on the row. |
| B2 | The slow path (60–120 s) is **always** beyond the deadline. | About 10% of reviews are guaranteed to time out. Add ~20% errors and **~30% of reviews fail**. | Failure UX is a first-class path: clear reason, "not counted", one-click retry. |
| B3 | Boundary: what if completion arrives **exactly** at 60 s? | It is an ambiguous edge and must be tested. | "Still in progress 60 s after" means **failed at t ≥ 60 s**. Completion is valid only if committed at `now < deadline_at`. |
| B4 | Who enforces the deadline? | If the browser enforces it, a closed tab breaks the rule. If the fake enforces it, a buggy fake breaks it. | **The server and the DB.** (a) Every write from the AI is conditional: `… WHERE status='running' AND now < deadline_at`. Zero rows updated means the event is dropped and logged. (b) **Lazy expiry**: any read of a running row past its deadline returns and persists `failed/timed_out`. (c) A **sweeper** every few seconds persists expiries that nobody reads. |
| B5 | A server restart or crash mid-review. | It leaves orphaned `running` rows. | They expire at the deadline through B4, so no slot is lost and no document stays locked. |
| B6 | There are two failure causes. | Users need to know whether retrying makes sense. | `failure_reason ∈ {ai_error, timed_out}`. Both are free. The copy differs slightly ([Errors and edge cases](07-errors-and-edge-cases.md)). |
| B7 | "A retry is a new review." | Without this, retries could reuse ids, deadlines or quota state. | A retry runs the **same flow as a new request**: new id, new deadline, new quota check, and a new confirmation (it may cost). The failed review stays stored. |
| B8 | Are "fails 1 in 5" and "slow 1 in 10" exclusive or independent? | It changes the probabilities and the tests. | **One draw per run, three mutually exclusive outcomes** (decided, Q7): ~20% `error`, ~10% `slow` (always ends as a timeout), ~70% `completed`. The RNG is injectable. |
| B9 | When does the error happen? | "After returning some of the findings or none." | In error mode, pick `k ∈ [0, n]` findings to emit, then raise at a random time within the 5–30 s window. |
| B10 | Cancellation is not mentioned. | A lawyer may regret a request. | **Not offered** (refused, documented). If added later, a cancelled review counts as failed: free, and it releases the lock. |
| B11 | What "in progress" means. | It drives R2 and A1. | Only `running`. There is no `queued` state (point 3). |

## C. Concurrency

| ID | Issue | Decision |
|---|---|---|
| C1 | Two lawyers request the **same document** at the same moment. | DB-level guarantee: a **partial unique index** `UNIQUE(document_id) WHERE status='running'`, plus a serialized write transaction. The loser gets `409 REVIEW_IN_PROGRESS` with the existing review, and **the UI switches to following that review** (*"Riccardo started a review 2 s ago"*). |
| C2 | Double-click, or a network retry by the same lawyer. | Same mechanism. The second POST returns 409 with the running review, so the effect is idempotent. The button is also disabled while the request is in flight. |
| C3 | Two lawyers take the **last slot** on different documents. | The quota check and insert happen in **one serialized transaction** (SQLite `BEGIN IMMEDIATE`, or Postgres `SELECT … FOR UPDATE` on a plan/workspace row). The loser gets `409 PLAN_EXHAUSTED`. |
| C4 | A row past its deadline but not yet swept is still `running` in the DB. **It would trip the unique index** and block a legitimate new request. | **The request transaction first expires stale running rows** (at least for this document, and all of them for the quota count). |
| C5 | Reserved count includes stale rows. | Count `running AND deadline_at > now` only (and expire the rest, as in C4). |
| C6 | Other viewers. | Every lawyer sees every review live (list and detail poll), not just the requester. |

## D. Reading results and trust

| ID | Issue | Decision |
|---|---|---|
| D1 | **Four states can show "no findings":** not reviewed, running with nothing yet, failed, and completed with 0 (Consulting). | Each has its own badge, icon and copy ([UI state matrices](06-screens-and-ui-states.md#ui-state-matrices)). "Completed · no clauses flagged" is the only one with a ✓. |
| D2 | "Latest review" versus "current result". | Two concepts. The **latest review** is the most recent request (it may be running or failed). The **current result** is the most recent *completed* review. The list shows both when they differ (*"✕ Last attempt failed · result from 2 Nov available"*). |
| D3 | A failed review with 2 of 3 findings looks like a short, valid list. | **Not displayed.** The main screen shows only the failure status. The findings stay stored in the DB but are not exposed in the UI ([Interpretation](03-decisions.md#interpretation-completed-reviews-vs-failed-reviews)). |
| D4 | Streaming conflicts with sorting by severity: cards would jump around. | **Arrival order while running. Severity → clause order once completed.** The re-sort plus the "Final" badge marks the moment the list becomes final. |
| D5 | Severity shown by colour only. | It fails accessibility and printing. Use **text + icon + colour** (`▲ High`, `■ Medium`, `● Low`). |
| D6 | A null clause or null excerpt. | *"General"* in place of the clause number. The excerpt block is replaced by *"No excerpt: this finding is about something missing from the contract."* |
| D7 | Long lists (16 findings). | The final view is sorted by severity. Partial views show **no totals**, because totals read as final. |
| D8 | Time display. | Absolute plus relative, in Europe/Rome (*"2 Nov 2026, 14:03 · 3 days ago"*). |
| D9 | Zero findings could be read as "the contract is fine". | Copy: *"The AI flagged no clauses. This is not a legal opinion that the contract is risk-free."* |
| D10 | The lawyer navigates away or closes the tab mid-review. | Nothing is lost. The review runs server-side, and coming back shows its current state. |

## E. Identity (no authentication)

| ID | Issue | Decision |
|---|---|---|
| E1 | Identity is a claim, not security. | A picker on first visit, stored in `localStorage`, switchable from the header. Every mutating call sends `X-Lawyer-Id`, and the server validates it against the 3 lawyers (`400 UNKNOWN_LAWYER`). Documented as a known limitation. |
| E2 | Can someone read before choosing an identity? | No. The picker is a blocking modal on first visit. It keeps the model simple: there is always a current lawyer. |
| E3 | Accountability for spending a shared plan. | `requested_by` is stored and shown everywhere a review appears. |
| E4 | The titles Partner, Senior associate and Trainee imply roles. | **All lawyers have equal rights** (the brief defines none). See Q4. |
| E5 | Switching identity while a review runs. | No effect. A review belongs to its requester, and anyone can follow it. |

## F. Tensions between the brief's rules, the stakeholders' requests and its own wording

The brief's rules are consistent with each other. The tensions below come from how the disputed points could be decided.

| ID | Tension | Resolution |
|---|---|---|
| F1 | If requests beyond the plan were queued, R4 would apply to them: a queued request is "in progress 60 s after it was **requested**", so it fails before it can run. Making a queue work would require a new "queued" state with its own rules. | Avoided by the strict block (point 3). |
| F2 | Same for R2: a queued request either counts as "in progress" (the document shows as in progress for weeks) or it doesn't (several lawyers queue the same document, and the requests all start together at the reset). | Avoided by the strict block (point 3). |
| F3 | F1 shows the "latest review", but the PM wants the "previous one on screen". | Two concepts: latest review and current result (D2). |
| F4 | "Follows it" implies real-time, but no transport is specified. | **Polling** (1 s on an active review, 2 s on the list while anything runs, 10 s otherwise) is proportionate for 3 users. |
| F5 | A 4 h timebox vs a long list of edge cases. | Prioritized scope in [Scope](10-scope-and-questions.md#scope-for-the-4-hour-timebox). |
| F6 | `samples/` path. | Resolved (D-13). |

## G. Technical pitfalls

| ID | Pitfall | Recommendation |
|---|---|---|
| G1 | Where the fake AI runs. | A background task in the API process (thread or asyncio) is enough. Correctness does **not** depend on it, thanks to B4. |
| G2 | Randomness and time make tests flaky. | Inject the **clock**, the **RNG** and the **sleep**, and test the fake's outcomes deterministically. Test the rules against a fake clock (e.g. advance to 59.999 s and 60 s). |
| G3 | SQLite and concurrent writes. | WAL mode, short transactions, `BEGIN IMMEDIATE` for the request path. |
| G4 | Clock skew between browser and server. | The server returns `server_now` and `deadline_at`, and the client renders the countdown from that offset. The client never decides an outcome. |
| G5 | Starting the job before the commit means the job may write to a row that doesn't exist yet. | **Start the fake job after the commit.** |
| G6 | Event ordering. | Findings carry a `seq`. Inserts are conditional on `running AND now < deadline_at`. |
