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
   docker compose run --rm web pnpm test
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

## Assumptions

## Limitations

## Time spent

## AI tools used
