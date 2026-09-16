# Sand Control Failure Database

A shared database for collecting sand-control-failure records from multiple
operators/service companies, built around a single Excel data dictionary
(`MASTER.xlsx`) that drives everything downstream: a standalone HTML intake
form, the PostgreSQL schema, and the FastAPI backend's validation rules.

```
web form  -->  FastAPI backend  -->  PostgreSQL
```

This repository is the durable source of truth for the whole system --
schema, migrations, backend, form, tests, and configuration. It does **not**
contain the production database itself, any real well data, or any real
credentials. See "What never belongs in this repo" below.

## Repo layout

```
MASTER.xlsx            the data dictionary -- shared input to both form/ and db/
dictionary/             shared parser for MASTER.xlsx (used by form/ and db/)
form/                   generates the standalone HTML intake form
db/                     SQLAlchemy schema, dictionary-driven codegen, Alembic migrations
backend/                FastAPI app (org-token auth, submit/fetch records)
tests/                  pytest suite (dictionary, db, migrations, api)
docker-compose.yml      local Postgres + backend, from zero on any machine
.github/workflows/      CI: codegen drift check, lint, migrations, tests
```

See [CLAUDE.md](CLAUDE.md) for the full data model and architecture.

## Quickstart (Docker)

Requires Docker Desktop (or an equivalent Docker Engine + Compose).

```
cp .env.example .env
docker compose up --build
```

This starts Postgres (not exposed to the host -- reachable only from the
`backend` container) and the API (exposed at `http://localhost:8000`). The
backend container runs `alembic upgrade head` on startup, then seeds two
dev-only organizations with known API tokens (printed to the backend
container's logs) since `SEED_DEV_DATA=true` by default in `.env.example`.

```
curl http://localhost:8000/health
curl http://localhost:8000/docs          # interactive OpenAPI docs
```

Submit a record (replace `<token>` with a token from the backend logs):

```
curl -X POST http://localhost:8000/records \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{
        "well": {"Well Specific": {"Well & Field Identification": {
          "Well name": "TEST-1", "Well identification number": 1
        }}},
        "completion_intervals": [{"fields": {}, "sand_bodies": [{}]}]
      }'
```

## Local development without Docker

Requires Python 3.12+ and a Postgres instance you control.

```
pip install -e ".[dev]"
cp .env.example .env      # then point DATABASE_URL at your own Postgres
cd db && alembic upgrade head && cd ..
uvicorn backend.app.main:app --reload
```

## Regenerating the form / schema after editing MASTER.xlsx

`MASTER.xlsx` is the single source of truth. After changing it:

```
python -m db.codegen              # regenerates db/generated/*.py + field_registry.json
python form/generate_form.py      # regenerates form/sand_control_form.html
cd db && alembic revision --autogenerate -m "describe the change"
# review the generated migration by hand, then:
alembic upgrade head
```

Commit the `MASTER.xlsx` diff, the regenerated `db/generated/*` files, the
regenerated `form/sand_control_form.html`, and the new migration file
together. CI re-runs the two regeneration commands and fails the build if
the committed output doesn't match (the "codegen drift check") -- so a
dictionary edit that wasn't followed by regenerating fails in CI even if
it's forgotten locally.

The generated form self-locks after a baked-in expiration date (client-side
check, since the form has no backend to call) -- currently `2026-11-01`
(`DEFAULT_EXPIRES_ON` in `form/generate_form.py`). To reissue the form with a
later cutoff, regenerate with `--expires-on YYYY-MM-DD` (or update the
`DEFAULT_EXPIRES_ON` constant and commit the regenerated
`sand_control_form.html`); pass `--expires-on ""` for a build with no
expiration.

Note: Alembic's `--autogenerate` cannot detect a column *rename* -- it will
show it as a drop + an add. If a dictionary edit is truly a rename, hand-edit
the generated migration to use `op.alter_column(...)` instead, or it will
silently drop data in any environment that already has rows.

## Tests

```
pip install -e ".[dev]"
export TEST_DATABASE_URL=postgresql+psycopg://sand_control:sand_control@localhost:5432/sand_control_test
pytest
```

Tests that don't need a database (dictionary parsing, codegen, schema
construction) run with no setup. Tests that do (migrations, the API) skip
cleanly if `TEST_DATABASE_URL` (or `DATABASE_URL`) isn't set. Point it at:

- a Postgres started via `docker compose up db` (add a temporary `ports:
  ["5432:5432"]` mapping to the `db` service locally to reach it from the
  host -- never do this in a shared environment), or
- any Postgres you control locally.

CI runs the full suite (including migrations and API tests) against a real
Postgres service container automatically -- see `.github/workflows/ci.yml`.

## What never belongs in this repo

- Real well/company data. `MASTER.xlsx` defines the *schema* only (Category /
  Subcategory / Parameter / validation rules) -- it has never contained an
  actual submitted record, and it should stay that way.
- `.env` (already gitignored) or any real database credentials, connection
  strings, or API tokens. `.env.example` documents variable names with
  local-only placeholder values.
- A dump of the production database, or the database itself. The database is
  private by design (see docker-compose.yml -- Postgres has no host port
  mapping); only the API is meant to be reachable from outside.

## Access model

Each participating company (organization) has one shared API token,
attributed to every record it submits (`organizations.api_token_hash` --
only a SHA-256 hash is stored, never the plaintext). There's no individual
per-user login yet; that can be added later as a `users` table without
changing how existing records are owned. See [CLAUDE.md](CLAUDE.md) for more
on the current scope and what's intentionally deferred.
