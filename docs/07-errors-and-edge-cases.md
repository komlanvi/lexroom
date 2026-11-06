# Error and edge-case catalogue

[← Back to the index](README.md)

| # | Scenario | System behaviour | User sees | Plan effect |
|---|---|---|---|---|
| 1 | AI error after k findings | `failed/ai_error`. The k findings stay stored, not displayed. | "The AI returned an error after N s. Not counted. [Retry]" + last completed review, if any | Slot released |
| 2 | No completion by 60 s (slow path, crash, stuck job) | Lazy expiry or sweeper sets `failed/timed_out`. | "No result within 60 seconds. Not counted. [Retry]" | Slot released |
| 3 | Finding or completion after the deadline | Conditional write affects 0 rows. Dropped and logged. | Nothing changes | None |
| 4 | Completion exactly at 60.000 s | Treated as late (BR-7). | Failed (time limit) | None |
| 5 | Two requests on the same document | One 201, one `409 REVIEW_IN_PROGRESS`. | The loser follows the existing review: "Riccardo started a review 2 s ago." | One reservation |
| 6 | Double-click or POST retried after a network glitch | Second call returns 409 with the same running review. | Seamless | One reservation |
| 7 | Last slot taken by a colleague while the dialog was open | `409 PLAN_EXHAUSTED` (with `completed` and `running` counts). | "Another review just took the last available slot. Your request has not been saved." Then the matching explanation: reviews in progress (they may free a slot within 60 s) or plan used up (available again {date}). | None |
| 8 | Plan exhausted | Button disabled. A direct API call returns 409. | Reset date, "no new review until then" | None |
| 9 | Server restarted mid-review | Orphaned running rows expire at their deadline. | Failed (time limit) | Released |
| 10 | Browser closed mid-review | The review continues server-side. | The correct state on return | Normal |
| 11 | Polling fails (offline) | Keep the last known state, show a banner, back off. | "Connection lost, status may be out of date." The Partial marking stays. | None |
| 12 | Unknown or missing `X-Lawyer-Id` | 400 | Identity picker is shown again | None |
| 13 | Unknown document id | 404 | "Document not found" + back to list | None |
| 14 | Review of a superseded version | Allowed | Standard confirmation (the document is already labelled "Previous version") | Normal |
| 15 | Re-review of an already reviewed document | Allowed | Standard confirmation | Normal |
| 16 | Document with 0 findings | Completes after 5–30 s with no findings. | "Completed · no clauses flagged" + disclaimer | Consumed |
| 17 | 16 findings streaming | Appended in arrival order, no reflow, no totals. | Partial list growing | — |
| 18 | Review straddles midnight at month end | It belongs to the month of its request. If it completes, it counts there. | New month's counter unaffected (starts at 10 available) | Month of the request |
| 19 | DST change | Period boundaries computed in Europe/Rome. | Correct reset time | — |
| 20 | Another lawyer starts a review on the document I'm viewing | Polling picks it up. | Panel switches to live, button disabled | — |
| 21 | Server clock ahead of or behind the client | Countdown from `server_now` and `deadline_at`. | Correct timer | — |
| 22 | DB write contention (SQLite) | WAL + short `BEGIN IMMEDIATE` transactions, with busy timeout. | Possibly a few ms more latency | — |
