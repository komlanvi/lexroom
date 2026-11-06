# User flows and sequence diagrams

[← Back to the index](README.md)

How the application works end to end: actors, screen map, user flows, server logic and sequence diagrams.

## Actors and system context

```mermaid
flowchart LR
  subgraph WS["Workspace: one law firm, one shared plan of 10 reviews per month"]
    P["Chiara Belotti · Partner"]
    R["Riccardo Fanti · Senior associate"]
    S["Sofia Greco · Trainee lawyer"]
  end
  P & R & S -->|"choose identity, no auth"| FE["Web frontend"]
  FE -->|"REST + polling"| API["Backend API"]
  API --> DB[("Relational DB")]
  API -->|"start job after commit"| AI["Fake AI reviewer"]
  AI -.->|"findings one by one, then completion or error"| API
  SW["Deadline sweeper"] -->|"expire running reviews past deadline"| DB
  SEED["samples/documents.json and samples/lawyers.json"] -->|"seed at startup"| DB
```

## Screen map

```mermaid
flowchart TD
  START(["Open app"]) --> HAS{"Identity stored in browser?"}
  HAS -- No --> PICK["S0 · Identity picker (blocking modal)"]
  HAS -- Yes --> LIST
  PICK --> LIST["S1 · Document list + plan counter in header"]
  LIST -->|"open a document"| DETAIL["S2 · Document detail + review panel"]
  DETAIL -->|"Request review / Retry"| CONFIRM["S3 · Confirmation dialog"]
  CONFIRM -->|"Use 1 review"| DETAIL
  CONFIRM -->|"Cancel"| DETAIL
  DETAIL -->|"Back"| LIST
  LIST -->|"switch lawyer in header"| PICK
  DETAIL -->|"switch lawyer in header"| PICK
```

## End-to-end user flow (all three flows, with decision points)

```mermaid
flowchart TD
  A(["Lawyer opens the app"]) --> B{"Identity stored?"}
  B -- No --> B1["Pick one of the 3 lawyers"] --> C
  B -- Yes --> C["S1 · List of 13 documents with latest review state and plan counter"]
  C --> D["Open a document"]
  D --> E{"Latest review of this document?"}
  E -- "None" --> E0["Not reviewed yet"]
  E -- "Running" --> RUN
  E -- "Completed" --> E2["Final result"]
  E -- "Failed" --> E3["Failure status only + last completed result if any"]
  E0 --> F{"Wants a review?"}
  E2 --> F
  E3 --> F
  F -- No --> READ["Read findings"]
  F -- Yes --> G{"Button state, from the latest data"}
  G -- "Running on this document" --> RUN
  G -- "available = 0" --> G2["Disabled: plan used up, resets 1st of next month 00:00 Rome. No queue."]
  G -- "available ≥ 1" --> H["S3 · Confirm: cost, remaining before and after"]
  H -- Cancel --> D
  H -- "Use 1 review" --> I{"Server re-check in one transaction"}
  I -- "Lost race: document now running" --> RUN
  I -- "Lost race: plan exhausted" --> G2
  I -- "Accepted: running, slot reserved, deadline set" --> RUN
  RUN["Follow live: findings marked Partial, timer vs 60 s, previous result marked no longer current"] --> J{"Outcome"}
  J -- "Completed before deadline" --> K["Final result: sorted, totals, 1 review consumed"]
  J -- "AI error" --> L["Failed, AI error: status only, partial findings removed from screen, slot released"]
  J -- "Deadline reached" --> M["Failed, time limit: late events ignored, slot released"]
  L --> N{"Retry?"}
  M --> N
  N -- Yes --> G
  N -- No --> READ
  K --> READ
```

## Request a review: server-side decision flow

```mermaid
flowchart TD
  R0["POST /api/documents/:id/reviews with header X-Lawyer-Id"] --> R1{"Lawyer id valid?"}
  R1 -- No --> X1["400 UNKNOWN_LAWYER"]
  R1 -- Yes --> R2{"Document exists?"}
  R2 -- No --> X2["404 DOCUMENT_NOT_FOUND"]
  R2 -- Yes --> T["BEGIN IMMEDIATE: serialize writers"]
  T --> R3["Expire running reviews whose deadline has passed"]
  R3 --> R4{"Running review on this document?"}
  R4 -- Yes --> X3["ROLLBACK, 409 REVIEW_IN_PROGRESS with that review: who and since when"]
  R4 -- No --> R5["available = 10 - completed this month - running"]
  R5 --> R6{"available ≥ 1?"}
  R6 -- No --> X4["ROLLBACK, 409 PLAN_EXHAUSTED with resets_at and running count"]
  R6 -- Yes --> R7["INSERT review: running, requested_at = now, deadline_at = now + 60 s"]
  R7 --> R8["COMMIT"]
  R8 --> R9["Start fake AI job for this review id"]
  R9 --> OK["201 Created with review, deadline_at, server_now"]
```

## Fake AI job and event handling

```mermaid
flowchart TD
  J0["Job starts for review id"] --> J1{"Draw outcome"}
  J1 -- "70% normal" --> N1["Total duration D in 5 to 30 s, emit all n findings spread over D"]
  J1 -- "20% error" --> E1["Pick k in 0..n and failure time in 5 to 30 s, emit k findings then error"]
  J1 -- "10% slow" --> S1["Total duration D in 60 to 120 s, emit all n findings spread over D"]
  N1 --> EV
  E1 --> EV
  S1 --> EV
  EV["For each event: conditional write WHERE status = running AND now < deadline_at"] --> W{"Rows updated?"}
  W -- "1" --> APPLY["Applied: finding stored, or status completed, or status failed ai_error"]
  W -- "0" --> DROP["Dropped and logged. Review already failed or past deadline."]
  DROP --> STOP["Job stops early"]
```

## Following a review live (client)

```mermaid
flowchart TD
  P0["Review panel shows review id"] --> P1["GET /api/reviews/:id every 1 s"]
  P1 --> P2{"Response"}
  P2 -- "Network error" --> P3["Banner: connection lost, status may be out of date. Keep Partial marking. Retry with backoff."] --> P1
  P2 -- "running" --> P4["Append new findings in arrival order, Partial tag, count so far, elapsed vs 60 s"] --> P1
  P2 -- "completed" --> P5["Stop polling. Final view: sorted by severity, Final badge. Refresh plan counter."]
  P2 -- "failed" --> P6["Stop polling. Remove partial findings. Show status: reason, not counted, Retry. Show last completed result, if any."]
```

## What the review panel shows (reading flow)

```mermaid
flowchart TD
  Q0{"Latest review of the document"}
  Q0 -- "none" --> Q1["Empty state: Not reviewed yet + Request review"]
  Q0 -- "running" --> Q2["Live panel, findings marked Partial"]
  Q2 --> Q2b{"Earlier completed review exists?"}
  Q2b -- Yes --> Q2c["Below: last completed review, marked Previous result, no longer current"]
  Q2b -- No --> Q2d["Nothing below"]
  Q0 -- "completed" --> Q3{"Number of findings"}
  Q3 -- "0" --> Q3a["Completed, no clauses flagged, plus AI disclaimer"]
  Q3 -- "1 or more" --> Q3b["Final badge, cards sorted high to low then clause"]
  Q0 -- "failed" --> Q4["Failure status only: reason, time, requester, not counted, Retry. No findings."]
  Q4 --> Q4b{"Earlier completed review exists?"}
  Q4b -- Yes --> Q4c["Show it as the current result, with its date"]
  Q4b -- No --> Q4d["No result available yet"]
```

## Sequence diagrams

**a) Happy path with streaming**

```mermaid
sequenceDiagram
  autonumber
  actor L as Chiara
  participant FE as Frontend
  participant API as Backend API
  participant DB as Database
  participant AI as Fake AI
  L->>FE: Click Request review
  FE->>L: Confirm dialog - uses 1 of 6 if it completes
  L->>FE: Use 1 review
  FE->>API: POST /api/documents/{id}/reviews
  API->>DB: tx - expire stale, check running, check quota, insert running
  API->>AI: start job after commit
  API-->>FE: 201 running, deadline_at, server_now
  par AI job
    AI->>API: finding 1 at 4 s
    API->>DB: conditional insert, stored
    AI->>API: finding 2 and 3
    API->>DB: conditional inserts, stored
    AI->>API: completed at 18 s
    API->>DB: UPDATE completed WHERE running AND now before deadline
  and Frontend polling every 1 s
    FE->>API: GET /api/reviews/{id}
    API-->>FE: running, partial findings so far
  end
  FE->>API: GET /api/reviews/{id}
  API-->>FE: completed, final findings
  FE->>L: Final view, plan counter now 5 available
```

**b) Slow run: timeout, then late events**

```mermaid
sequenceDiagram
  autonumber
  participant FE as Frontend
  participant API as Backend API
  participant DB as Database
  participant AI as Fake AI - slow path
  Note over API,DB: T0 review requested, deadline T0 + 60 s
  AI->>API: finding 1 at T0 + 25 s
  API->>DB: stored, still running
  FE->>API: GET /api/reviews/{id} at T0 + 61 s
  API->>DB: running and past deadline, persist failed timed_out
  API-->>FE: failed, timed_out, not counted
  AI->>API: finding 2 at T0 + 70 s
  API->>DB: conditional insert, 0 rows
  API-->>AI: ignored and logged
  AI->>API: completed at T0 + 95 s
  API->>DB: conditional update, 0 rows
  Note over API,DB: Stays failed. Plan untouched. The sweeper also expires reviews nobody is watching.
```

**c) Races: same document, then the last slot**

```mermaid
sequenceDiagram
  autonumber
  actor C as Chiara
  actor R as Riccardo
  participant API as Backend API
  participant DB as Database
  Note over C,DB: Plan - 9 completed, 0 running, so 1 available
  C->>API: POST review on Lease v2
  R->>API: POST review on Lease v2
  API->>DB: tx A for Chiara gets the write lock first
  DB-->>API: inserted, available now 0
  API-->>C: 201 running
  API->>DB: tx B for Riccardo runs after A commits
  DB-->>API: a running review exists for this document
  API-->>R: 409 REVIEW_IN_PROGRESS, started by Chiara 0 s ago
  Note over R: UI switches Riccardo to following the review started by Chiara
  R->>API: POST review on NDA
  API->>DB: tx C
  DB-->>API: available = 10 - 9 - 1 = 0
  API-->>R: 409 PLAN_EXHAUSTED, 1 running review may free a slot
```
