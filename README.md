# Lexroom · Contract review flow

A law-firm workspace where lawyers request an AI review of a contract, follow it live, and read the flagged clauses. The AI is faked.

- `api/`: backend, Django + Django Ninja, SQLite.
- `web/`: frontend, Next.js + TypeScript. It forwards `/api/*` to the backend, so the browser only talks to the frontend.
- `samples/`: the brief's sample lawyers and documents, loaded at startup.
- `docs/`: the product and technical analysis ([index](docs/README.md)).

Choose **one** of the two ways below. Docker is the shortest. The local setup needs no Docker.

## Run and test with Docker

**Prerequisite:** [Docker](https://docs.docker.com/get-docker/) with Compose.

1. Start the application:

   ```sh
   docker compose up --build
   ```

2. Open <http://localhost:3000>.
3. Run the backend tests:

   ```sh
   docker compose run --rm api pytest
   ```

4. Run the frontend tests:

   ```sh
   docker compose run --rm web-test
   ```

Stop with `Ctrl+C`. `docker compose down -v` also deletes the database.

## Run and test without Docker

**Prerequisites:**

| Tool | Version | Install |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | 0.13 or later | `brew install uv`, or the official installer. uv downloads Python 3.15 itself. |
| [Node.js](https://nodejs.org/) | 26 LTS | `brew install node`, or the official installer |
| [pnpm](https://pnpm.io/installation) | 12 | `brew install pnpm`, or `npm install -g pnpm@12` |

Use two terminals, one for each service.

**Terminal 1, backend** (on <http://localhost:8000>):

```sh
cd api
uv sync                              # install Python and the dependencies
uv run python manage.py migrate      # create the SQLite database
uv run python manage.py seed         # load samples/ (safe to run again)
uv run gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 1 --threads 8
```

**Terminal 2, frontend** (on <http://localhost:3000>):

```sh
cd web
pnpm install
pnpm dev
```

Open <http://localhost:3000>.

**Tests:**

```sh
cd api && uv run pytest     # backend
cd web && pnpm test         # frontend
```

## Decisions on the three contested points

Each point opposes the PM and the senior partner (the customer). The full reasoning is in [docs/03-decisions.md](docs/03-decisions.md).

**First, a reading of the brief.** Only a *completed* review has a result to read. A failed review is a *state* ("it completes or fails"), not a result. So the "previous" review in point 1 is the last **completed** one, and a failed review shows only its status.

**1. The previous review while a new one runs: keep it, clearly marked as no longer current.**
The live review takes the top of the panel. The last completed review stays below it, headed "Previous result · no longer current", with every finding tagged "Previous" and a muted style. The two lists are never merged. If the new review completes, it replaces the old one. If it fails, the old one is shown again as the current result, under a "Latest attempt failed · not counted" status.
*Why:* the PM gets "never wait in front of nothing". Showing an old result was never the risk; showing it *as if it were current* was, and the explicit marking rules that out for the customer.
*Refused:* showing the previous findings unlabelled, or merged with the new ones.

**2. Findings before the review has finished: show them, clearly marked as partial.**
Findings appear one by one in arrival order. Each is tagged "Partial" with a dashed draft style, under a banner: "n findings received so far. This list is incomplete: more may arrive, and the review may still fail." No totals are shown while it runs. On completion the tags disappear, the list is re-sorted by severity and a **Final** badge appears: that change is the signal of finality. If the review fails, its partial findings are removed from the screen and only the failure status remains (they stay stored).
*Why:* the PM's "show each finding as soon as the AI returns it", and the customer's "whatever isn't final must be impossible to read as final".
*Refused:* unmarked partial findings, totals before completion, and showing a failed review's findings.

**3. Requests beyond the plan: strict block, no queue.**
When the plan is used up, nobody can start a review. The button is disabled and says when reviews are available again (e.g. "1 Dec 2026, 00:00 Rome time, in 24 days"). When the plan is at 0 only because reviews are still running, a dedicated message explains it: those reviews hold the remaining slots, a failing one frees its slot within 60 s, and nothing has been saved. **Every** request goes through a confirmation that states its cost and the plan before and after.
*Why:* the PM's queue clashes with the brief's own rules. A queued request would be "still in progress 60 s after it was requested", so it would time out before it could run. It would also either lock its document for weeks or let several queued requests on one document start together at the reset. The strict block is the simplest behaviour, never spends a review without someone deciding to, and never suggests a review is coming when it isn't.
*Refused:* the queue, and any deferred execution.

## Assumptions

- **Plan month:** the calendar month in **Europe/Rome**. A review belongs to the month of its **request**: that is when the plan was checked and the cost confirmed. A review requested on 30 Nov that completes on 1 Dec counts in November.
- **Reserving a slot:** a request reserves a slot when it starts, otherwise three parallel requests at "9 used" could end at 12. `available = 10 − completed this month − running`. The slot is used if the review completes and released if it fails or times out.
- **Deadline:** a completion counts only if it is processed strictly before 60 s after the request. At exactly 60.000 s the review has failed (time limit).
- **Fake AI:** one random draw per run, three exclusive outcomes: about 20% AI error, 10% slow (always ends as a timeout), 70% completed.
- **Identity:** the three lawyers have the same rights (no roles or approvals in the brief). The chosen lawyer is remembered in the browser and recorded as the requester of each review.
- **Not offered** because the brief doesn't mention them: cancelling a running review, per-lawyer limits, a warning before re-reviewing an already reviewed document.
- **Superseded documents (open question Q6):** the older lease is labelled "Previous version · superseded by the version of 24 Sep" and its reviews stay readable. Until the question is answered, it can still be reviewed like any other document.

All assumptions and open questions: [docs/02-issues-and-assumptions.md](docs/02-issues-and-assumptions.md) and [docs/10-scope-and-questions.md](docs/10-scope-and-questions.md).

## Limitations

- **SQLite only.** The database is read from `DATABASE_URL`, and only ORM features that also work on PostgreSQL are used. To switch: set `DATABASE_URL`, add a PostgreSQL driver, and add a `select_for_update()` on a workspace row inside `request_review` (`api/reviews/services/request.py`), which replaces SQLite's `IMMEDIATE` transactions. Not tested on PostgreSQL.
- **Background work runs as threads in the backend process**, so it runs as one worker process. If the process stops mid-review, the review fails at its deadline and its slot is released; nothing is lost, but the review is not resumed. Scaling out would need a job queue.
- **No authentication.** The `X-Lawyer-Id` header identifies the lawyer; it does not prove who they are (authentication is out of the brief's scope).
- **Polling, not push:** updates arrive within 1 s on a followed review, 2 s while any review runs, 10 s otherwise.
- **No browser end-to-end tests.** The frontend has unit tests on its display logic (badges, button states, panel sections, sort order, messages). The flows were checked by hand in the browser, as recorded in the [implementation plan](docs/13-implementation-plan.md) checkpoints. The "last slot just taken by a colleague" message is covered by unit tests only.
- **Small display gaps:** dates are absolute only (no "3 days ago"); the detail page of the older lease says "Previous version" without the newer version's date (the list shows it); the elapsed time in the list uses the browser clock (the review page uses the server's).
- **Not production-ready as is:** the default `SECRET_KEY`, no HTTPS, no rate limiting, no monitoring.
- **Timebox:** see "Time spent" below.

## Time spent

**About 4 h 35 min**, from the first message of the AI session (11:36) to the final commit (about 16:12) on 6 Nov 2026, analysis included:

| Part | Time (UTC+1) | Duration |
|---|---|---|
| Analysis of the brief, product decisions, technical decisions and plan | 11:36 – 14:35 | about 3 h |
| Implementation, phases 0 to 6 (backend, frontend, Docker) | 14:35 – 16:06 | about 1 h 30 |
| Documentation and delivery | 16:06 – 16:12 | about 5 min |

This is about 35 minutes over the 4 h timebox. The extra time went into the analysis: settling the three contested points and the open questions first made the implementation short and kept its scope tight. Nothing from the planned scope was cut.

## AI tools used

- **Cursor** in agent mode, with **Claude Opus 5.5**, in a single session. The full exported log is in [`ai-log/`](ai-log/).
- **Analysis (with the AI as a sparring partner):** the AI read the brief and listed pitfalls, ambiguities and edge cases. I challenged its reasoning (for example, where it saw a contradiction between the PM's queue and the brief's rules, there was only a conflict that depends on the decision) and made each product decision. The result is the analysis in [`docs/`](docs/README.md).
- **Technical decisions and plan:** proposed by the AI, chosen and trimmed by me ([docs/12](docs/12-technical-decisions.md), [docs/13](docs/13-implementation-plan.md)), with a standing rule: stay within the documented scope and keep the code simple.
- **Implementation:** the AI wrote the code and tests phase by phase, one commit per phase. I reviewed each phase before the next. Tests were checked by deliberately breaking the code (boundary and race mutations), and each phase checkpoint was verified by running the application, including in the browser through Cursor's built-in browser.
