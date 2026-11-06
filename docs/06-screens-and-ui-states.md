# Screens and UI states

[← Back to the index](README.md)

Low-fidelity wireframes of every screen state, and the matrices that drive badges, panels and the request button.

## Wireframes (low fidelity)

**S0 · Identity picker (first visit, blocking)**

```
+-----------------------------------------------------------+
|  Who is using Lexroom?                                    |
|  (No login in this demo. Your choice is remembered        |
|   in this browser and can be changed at any time.)        |
|                                                           |
|  ( ) Chiara Belotti    Partner                            |
|  ( ) Riccardo Fanti    Senior associate                   |
|  ( ) Sofia Greco       Trainee lawyer                     |
|                                              [Continue]   |
+-----------------------------------------------------------+
```

**S1 · Document list**

```
Lexroom · Workspace           Plan · November: 6 of 10 available · 1 running  [Chiara Belotti v]
                              Resets 1 Dec, 00:00 Rome time
---------------------------------------------------------------------------------------------------
Document                                          Uploaded              Latest review
---------------------------------------------------------------------------------------------------
Franchise agreement — Kappa Coffee S.r.l.         21 Sep · Riccardo     (o) In progress · 0:12 · by Sofia
Commercial lease — Via Tortona 12, Milan         24 Sep · Riccardo     [✓] Completed 2 Nov · 2 findings
Commercial lease — Via Tortona 12, Milan          03 Sep · Riccardo     [ – ] Not reviewed
   [PREVIOUS VERSION] superseded by the version of 24 Sep
Consulting agreement — Delta Advisory S.r.l.      10 Sep · Sofia        [✓] Completed 3 Nov · no clauses flagged
Non-disclosure agreement — Alfa Robotics S.r.l.   01 Sep · Sofia        [✕] Last attempt failed (time limit) 5 Nov
                                                                            · result from 1 Nov available
Loan agreement — Epsilon Capital S.p.A.           11 Sep · Chiara       [✕] Failed (AI error) 5 Nov · no result yet
Supply agreement — Beta Components S.p.A.         08 Sep · Riccardo     [ – ] Not reviewed
...
```

**S2 · Detail, running, with a previous review**

```
< Back   Commercial lease — Via Tortona 12, Milan   uploaded 24 Sep · 19 pages · lease

+-- REVIEW IN PROGRESS --------------------------------------------------------------+
| Requested by Riccardo at 14:10:05 · 0:14 elapsed · stopped automatically at 1:00   |
| 1 finding received so far. This list is INCOMPLETE: more may arrive, and the       |
| review may still fail.                                                             |
|  .- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -.   |
|  : PARTIAL   Clause 4.2 · Medium                                               :   |
|  : Rent indexed at 100% of inflation                                           :   |
|  '- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -'   |
+------------------------------------------------------------------------------------+
+-- PREVIOUS RESULT · NO LONGER CURRENT --------------------------------------------+
| 2 Nov 2026, 14:03 · by Chiara · a new review is in progress (above)                |
|  PREVIOUS  ▲ High · Clause 8.3 · Tenant pays for structural repairs               |
|  PREVIOUS  ■ Medium · Clause 4.2 · Rent indexed at 100% of inflation              |
+------------------------------------------------------------------------------------+
```

**S2 · Detail, completed (final)**

```
+-- FINAL REVIEW · completed 5 Nov 2026, 14:10:23 · requested by Riccardo ----------+
| 2 findings, sorted by severity                                                     |
|                                                                                    |
|  ▲ HIGH · Clause 12.1 · Break option for the landlord only                         |
|  “The Landlord may withdraw from this Agreement at any time by giving six…”        |
|  Once the tenant has fitted out the premises, a one-sided break option…            |
|                                                                                    |
|  ■ MEDIUM · Clause 4.2 · Rent indexed at 100% of inflation                         |
|  “The rent shall be updated every year by 100% of the change in the…”              |
|  For this type of lease, indexation above 75% of the ISTAT index may not…          |
+------------------------------------------------------------------------------------+
[Request a new review]          AI findings support, not replace, a lawyer's review.
```

**S2 · Detail, completed with a "missing clause" finding**

```
|  ● LOW · General (no specific clause) · No governing law or jurisdiction          |
|  No excerpt: this finding is about something missing from the contract.          |
|  The agreement does not say which law applies or which court decides…            |
```

**S2 · Detail, latest attempt failed, with an earlier completed review**

```
+-- LATEST ATTEMPT FAILED ----------------------------------------------------------+
| ✕ The AI returned an error after 14 s (requested by Sofia at 14:22:10).           |
|   It did NOT count against the plan.                             [Retry review]   |
+-----------------------------------------------------------------------------------+
+-- FINAL REVIEW · completed 1 Nov 2026 · requested by Chiara ----------------------+
|   (this is the current result)                                                    |
|   ...findings of the 1 Nov review, sorted by severity...                          |
+-----------------------------------------------------------------------------------+
```

**S2 · Detail, failed, no completed review yet**

```
+-- REVIEW FAILED ------------------------------------------------------------------+
| ✕ No result within 60 seconds (requested by Sofia at 14:22:10).                   |
|   It did NOT count against the plan.                             [Retry review]   |
+-----------------------------------------------------------------------------------+
No completed review for this document yet.
```

**S3 · Confirmation dialog**

```
+-------------------------------------------------------------------------+
| Request an AI review?                                                   |
| Commercial lease — Via Tortona 12, Milan (24 Sep)                       |
|                                                                         |
| • If it completes, it uses 1 of the workspace's 10 November reviews:    |
|   6 available now → 5 after this one.                                   |
| • If it fails or takes longer than 60 seconds, it is free.              |
|                                                                         |
|                                    [Cancel]   [Use 1 review]            |
+-------------------------------------------------------------------------+
When only 1 review is available, the cost line reads:
  "This is the LAST review available this month for the whole workspace."
```

**Plan exhausted (button area)**

```
[ Request review ]  (disabled)
The workspace has used its 10 reviews for November.
Reviews are available again on 1 Dec 2026, 00:00 Rome time (in 24 days).
No new review can be started until then.
```

**No review available right now, because reviews in progress hold the remaining slots (button area)**

Example: 8 reviews completed and 2 in progress in November, so 0 available.

```
[ Request review ]  (disabled)
No review can be started right now.
This month: 8 reviews completed + 2 in progress = all 10 reviews in use.

Each review in progress holds one of the 10 reviews until it finishes:
  • if it completes, that review is used;
  • if it fails or takes longer than 60 seconds, it is not counted and
    becomes available again (within 60 seconds at most).

This request has NOT been saved and will not start on its own.
This button becomes active again automatically if a review becomes available.
```

If both reviews in progress complete, the message switches to the "Plan exhausted" one above.

## UI state matrices

**Document badge (list) and panel header**

| Latest review | Earlier completed exists? | Badge in list | Panel |
|---|---|---|---|
| none | — | `– Not reviewed` (grey) | Empty state + Request review |
| running | no | `(o) In progress · m:ss · by X` (blue, animated) | Live panel, findings marked Partial |
| running | yes | `(o) In progress · …` + "previous result from {date}" | Live panel + previous result marked "no longer current" |
| completed, n > 0 | — | `✓ Completed {date} · n findings` | Final view |
| completed, n = 0 | — | `✓ Completed {date} · no clauses flagged` | Final empty view + disclaimer |
| failed (ai_error / timed_out) | no | `✕ Failed ({reason}) {date} · no result yet` (red) | Failure status + Retry + "No completed review yet" |
| failed | yes | `✕ Last attempt failed · result from {date} available` | Failure status + Retry, then the last completed review as the current result |

**Request button**

| Condition (in priority order) | State | Label / helper text |
|---|---|---|
| A running review on this document | disabled | "Review in progress (by X, m:ss)". The panel follows it. |
| `available = 0` and `running > 0` | disabled | Explicit message ([Wireframes](06-screens-and-ui-states.md#wireframes-low-fidelity)): "No review can be started right now. {completed} completed + {running} in progress = all 10 in use. A review in progress that fails becomes available again within 60 s. This request has not been saved." |
| `available = 0` and `running = 0` | disabled | "Plan used up for {Month}. Available again {date} 00:00 Rome time." |
| POST in flight | disabled | "Requesting…" |
| Last review failed | enabled | "Retry review" |
| A completed review exists | enabled | "Request a new review" |
| Otherwise | enabled | "Request review" |

**Plan counter (header)**: `{available} of 10 available · {running} running · resets {date}`. It turns red at 0.
