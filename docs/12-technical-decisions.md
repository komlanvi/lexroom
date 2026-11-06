# Technical decisions

[← Back to the index](README.md)

Guiding principle, from the brief's evaluation points: **"Solution architecture, proportionate to the problem."** Favour the simplest solution that enforces the rules correctly, and keep the code modular enough to evolve (e.g. switch to PostgreSQL) without rewriting it. No speculative infrastructure.

## Summary

| ID | Decision | In one line |
|---|---|---|
| TD-1 | Stack | Next.js + TypeScript (frontend), Python + Django + Django Ninja (backend), the evaluators' own stack. |
| TD-2 | Database | SQLite, configured through `DATABASE_URL` so PostgreSQL can be plugged in later. |
| TD-3 | Concurrency | SQLite `IMMEDIATE` transactions serialize writers. The request transaction lives in one function. |
| TD-4 | Background work | The fake AI and the expiry sweeper run as threads inside the backend process. |
| TD-5 | Time and randomness | An injectable clock and random number generator, used everywhere. |
| TD-6 | Real-time updates | Client polling. |
| TD-7 | Identity | `X-Lawyer-Id` header, validated server-side. Not a security mechanism. |
| TD-8 | Containerization | Docker Compose with two services: `backend` and `frontend`. |
| TD-9 | Frontend → API | Next.js proxies `/api/*` to the backend (same origin, no CORS). |
| TD-10 | Startup | Migrations and seeding run automatically and are idempotent. |
| TD-11 | Versions and tooling | Latest stable versions, resolved at scaffold time and pinned in lockfiles. `uv` for Python, `pnpm` for Node. |
| TD-12 | Testing | Backend rule tests first (pytest), a thin layer of frontend tests on display logic. |
| TD-13 | Code organization | One Django app per bounded area, with the business rules in a service layer separate from the HTTP layer. |

---

## TD-1 · Stack

- **Frontend:** Next.js (App Router) with TypeScript.
- **Backend:** Python, Django, Django Ninja for the HTTP API.
- **Why:** it is the stack Lexroom uses, so evaluators can review the code in a familiar setting. The brief says it earns no extra points; it was chosen for readability, not for points.

## TD-2 · Database: SQLite, switchable to PostgreSQL

- SQLite file stored in a Docker named volume.
- The connection is read from a `DATABASE_URL` environment variable, defaulting to SQLite.
- Only Django ORM features that work on both SQLite and PostgreSQL are used (e.g. `UniqueConstraint` with a `condition` for "one running review per document").
- **Not done:** no PostgreSQL service, no PostgreSQL tests, no database-specific code paths, no repository abstraction on top of the ORM.
- **To switch later:** set `DATABASE_URL`, and add a row lock in the request transaction (TD-3). This is documented in the README.

## TD-3 · Concurrency

- **Need:** two lawyers taking the last plan slot, or requesting the same document at the same time, must not break BR-3 or BR-6. This is rule correctness, not optimization.
- **Solution:** SQLite `"transaction_mode": "IMMEDIATE"` (Django database option), so the read-check-insert of a request runs with the write lock held from the start. WAL mode and a busy timeout avoid spurious "database is locked" errors under light concurrency.
- **Seam:** the request transaction (expire stale reviews → check running review → check plan → insert) is a single service function. Switching to PostgreSQL means adding a `select_for_update()` on a workspace row inside that function, and nothing else.
- The unique conditional constraint on `(document_id) WHERE status = 'running'` is the final safety net.

## TD-4 · Background work: threads in the backend process

- **Fake AI:** each accepted review starts a thread **after the transaction commits**. The thread emits findings, then completes or fails, through conditional writes (BR-9).
- **Sweeper:** one background thread expires running reviews past their deadline every few seconds. Lazy expiry on reads and in the request transaction (BR-8) guarantees correctness even if the sweeper is late.
- **Process model:** the backend runs with a **single worker process and multiple threads**, so there is exactly one sweeper.
- **Why not Celery/Redis or a separate worker:** correctness does not depend on the job runner. If the process dies, running reviews expire at their deadline and release their slot. A queue system would add two services for no rule-related benefit.

## TD-5 · Time and randomness

- One `Clock` interface (`now()`), with a system implementation and a fake for tests that can be advanced manually.
- The fake AI receives its random number generator and its sleep function as dependencies.
- **Time is always taken from the application clock, never from the database (`NOW()`).** Behaviour is identical on any database, and boundary tests (59.999 s vs 60 s, month end in Europe/Rome) are deterministic.
- Django `USE_TZ = True`. Timestamps are stored in UTC. Plan months are computed in `Europe/Rome` with `zoneinfo`.

## TD-6 · Real-time updates: polling

- 1 s on a review being followed, 2 s on the document list while any review runs, 10 s otherwise.
- Proportionate for three users. Server-Sent Events are listed in [Future improvements](11-future-improvements.md).
- The server returns `server_now` with every review, so the countdown is computed from server time (no client clock skew).

## TD-7 · Identity

- The selected lawyer is stored in the browser (`localStorage`) and sent as `X-Lawyer-Id` on every mutating call.
- The backend validates it against the seeded lawyers (`400 UNKNOWN_LAWYER`).
- Documented as a limitation: it identifies, it does not authenticate (the brief excludes authentication).

## TD-8 · Containerization: Docker Compose, two services

- `backend`: Django + Ninja served by a production-grade WSGI server (single worker, multiple threads, see TD-4). SQLite in a named volume.
- `frontend`: Next.js production build (multi-stage image).
- One command to run: `docker compose up --build`. One command to test the backend: `docker compose run --rm backend pytest`.
- The README also gives the local commands (without Docker) for faster development.
- **Why:** simple setup for the evaluator. It also gives a starting point for a production deployment, which would still need PostgreSQL and the other production concerns listed in the README limitations.

## TD-9 · Frontend → API: same-origin proxy

- The browser only calls the frontend's origin. Next.js forwards `/api/*` to the backend over the Docker network.
- **Why:** no CORS configuration, the backend is not exposed to the browser, less configuration overall.
- **Watch-out:** `rewrites` in `next.config` are resolved at build time. The backend URL is passed as a build argument, or the proxy is a small route handler reading it at runtime. The choice is made in phase 4 of the [implementation plan](13-implementation-plan.md), whichever is simpler.

## TD-10 · Startup: migrations and seeding

- The backend container entrypoint runs `migrate`, then a `seed` command, then starts the server.
- `seed` loads `samples/lawyers.json` and `samples/documents.json`. It is **idempotent** (upsert by id), so restarts never duplicate data.
- The sample findings are stored as the fake AI's "script" per document (`SAMPLE_FINDING` in the [domain model](04-domain-model-and-business-rules.md)).

## TD-11 · Versions and tooling

- Latest **stable** versions of Python, Django, Django Ninja, Node.js, Next.js and the other dependencies, checked on the official registries at scaffold time, then pinned (`uv.lock`, `pnpm-lock.yaml`, image tags).
- `uv` for Python dependency management, `pnpm` for Node. Inside Docker the evaluator never needs either.

## TD-12 · Testing strategy

- **Backend (priority):** pytest + pytest-django. Every rule in the [acceptance criteria](09-acceptance-criteria.md) for plan, concurrency and deadline is a test, using the fake clock and a deterministic fake AI. Includes one concurrency test on the request transaction.
- **API:** a few tests through the Ninja test client for status codes and error bodies (`400`, `404`, `409 REVIEW_IN_PROGRESS`, `409 PLAN_EXHAUSTED`).
- **Frontend (thin):** unit tests on the pure display logic (badge and button state, finding sort order, labels for "Partial", "Previous", "Previous version").
- **Not done:** browser end-to-end tests, unless time remains ("Should" in the [scope](10-scope-and-questions.md#scope-for-the-4-hour-timebox)).

## TD-13 · Code organization

```
.
├── docker-compose.yml
├── README.md                     # run, test, decisions, assumptions, limitations, time, AI usage
├── samples/                      # brief's sample data (seed source)
├── docs/                         # this analysis
├── backend/
│   ├── pyproject.toml, uv.lock, Dockerfile, manage.py
│   ├── config/                   # settings (env-driven), urls, wsgi
│   ├── workspace/                # lawyers, documents, sample findings, seed command
│   └── reviews/
│       ├── models.py             # Review, Finding + constraints
│       ├── services/             # business rules: plan, request, lifecycle, expiry
│       ├── fake_ai.py            # fake reviewer (injected clock, RNG, sleep)
│       ├── clock.py
│       ├── api.py, schemas.py    # Ninja router: HTTP only, no business rules
│       └── tests/
└── frontend/
    ├── package.json, pnpm-lock.yaml, Dockerfile, next.config.ts
    └── src/
        ├── app/                  # pages: document list, document detail
        ├── components/           # identity picker, plan counter, review panel, dialogs
        └── lib/                  # API client, polling hook, pure display logic (+ tests)
```

- **Rule:** business rules live only in `reviews/services/`. The API layer translates HTTP to service calls and service errors to HTTP codes.
- `workspace` and `reviews` are separate Django apps because they change for different reasons (seed data vs review rules). No further layering.

## Not done (deliberately)

PostgreSQL service or tests · Celery, Redis or any queue · Server-Sent Events or WebSockets · Authentication · Generated TypeScript client from OpenAPI · Browser end-to-end tests (unless time remains). Each can be added without restructuring the code.
