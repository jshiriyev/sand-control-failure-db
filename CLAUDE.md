# Sand Control Failure DB

## Objective

Collect sand-control-failure records from multiple operators/service companies into a
shared database, with a standardized web intake form for participating companies to
submit data with. The end-to-end architecture is:

```
web form  -->  FastAPI backend  -->  PostgreSQL
```

A single Excel workbook (`MASTER.xlsx`) is the durable source of truth for the data
model. Everything else -- the HTML intake form, the PostgreSQL schema, and the
backend's validation rules -- is either generated from it or driven by it at runtime,
so the form and the database can never silently drift apart from each other. The
database itself is never public; only the API is exposed (see "Database & API
architecture" below).

## File inventory

- `MASTER.xlsx` -- **the source of truth**. Sheet `MasterView`, one row per Parameter
  (138 currently). Shared input to both `form/generate_form.py` and `db/codegen.py` via
  the `dictionary` package -- nothing else reads it directly.
- `dictionary/` -- the shared parser for `MASTER.xlsx`. Owns the data model (`ParamRow`,
  `FieldSpec`), the cell-DSL parsers, and `classify_field()`. Both `form/` and `db/`
  import from here rather than each maintaining their own interpretation of what a
  dictionary cell means.
- `form/generate_form.py` -- reads `MASTER.xlsx` (via `dictionary`) and writes a
  standalone, no-backend, client-side HTML intake form.
- `form/sand_control_form.html` -- generated output (regenerate after any dictionary
  edit; do not hand-edit).
- `db/` -- SQLAlchemy schema, the dictionary-driven codegen pipeline, and Alembic
  migrations. See "Database & API architecture" below.
- `backend/` -- the FastAPI app: org-token auth, submit/fetch endpoints.
- `tests/` -- pytest suite covering `dictionary/`, `db/`, migrations, and the API.
- `docker-compose.yml`, `.env.example`, `pyproject.toml` -- local reproducibility and
  packaging.
- `.github/workflows/ci.yml` -- CI: codegen drift check, lint, migrations, full test
  suite against a real Postgres service container.
- `Changes to Excel sheet.docx` -- historical notes from the dictionary redesign, kept
  for reference only.

## Input table schema (`MASTER.xlsx`, sheet `MasterView`)

Columns, in order:

| Column | Meaning |
|---|---|
| `Scope` | `Well`, `Completion Interval {id}`, or `Sand Body {id}` -- see "Scope hierarchy" below |
| `Category` | Top-level grouping (varies per scope -- e.g. `General Information`, `Well Specific`, `Drilling`, `Completion`, `Reservoir Characterization`) |
| `Subcategory` | Second-level grouping within a Category |
| `Parameter` | Field name, shown as the row label |
| `Input Type` | `Dropdown Menu`, `Text`, `Number`, `Short Date`, or `Boolean` |
| `Unit` | Display unit (e.g. `ft`, `psi`, `stb/d`), blank if not applicable |
| `Affected Subcategory` | Conditional-visibility rule targeting a Subcategory (see below) |
| `Affected Parameter` | Conditional-visibility rule targeting a single Parameter (see below) |
| `Data Validation` | Constraint/options -- format depends on Input Type, see below |
| `Tooltip` | Plain-language guidance shown as a "?" icon next to the field in the generated form. Optional -- a row with a blank cell simply renders with no "?" icon. |
| `User comment` | SME/reviewer feedback on the dictionary itself, collected during schema review. Not rendered into the form or stored anywhere -- purely a scratch column for iterating on the dictionary with subject matter experts. A per-field "comments" feature of the *form itself* may be built later; that would be a distinct, not-yet-built feature from this column. |

### Scope hierarchy

```
Well  (rendered once per record)
 └── Completion Interval {id}  (repeatable -- a well has 1+)
      └── Sand Body {id}  (repeatable -- a completion interval has 1+ sand bodies)
```

Current row distribution: `Well`=62, `Completion Interval {id}`=47, `Sand Body {id}`=29.
Drilling, Completion (incl. Sand Control equipment: Completion Type, Screen Type, Gravel
Pack details, etc.) live at Completion Interval scope, meaning multiple Sand Bodies
within one Completion Interval share a single drilling/completion/sand-control design
record (one gravel pack can span multiple sand bodies) -- a deliberate consolidation
decision, not an oversight. Pre-production/cleanup and Reservoir Characterization
(rock/fluid properties) live at Sand Body scope, since those genuinely vary per sand
body even when the equipment above them doesn't.

Two Parameters are pure UI/record-keeping counters (`Number of Completion Intervals` at
Well scope, `Number of sand bodies` at Completion Interval scope). They are **not** used
to drive the form's repeaters or to enforce referential integrity anywhere downstream --
the real count is always however many child blocks/rows actually exist. The form does
offer an "Apply" button next to each that grows the corresponding repeater to match a
typed number (see "Form behavior" below), but shrinking or mismatches are never
auto-corrected or rejected.

### `Data Validation` / `Affected Subcategory` / `Affected Parameter` parsing

Cells in these three columns are written as **Python-literal-safe text** (parsed with
`ast.literal_eval`, tolerant of JSON's lowercase `true`/`false`/`null` too, since cells
aren't strictly JSON), see `dictionary/parsing.py`. `Data Validation` and the two
`Affected` columns use two unrelated DSLs within that shared parsing style:

**`Data Validation`** -- modeled after Excel's own Data Validation dialog: a type name
plus optional modifiers (`parse_validation_cell`):

- Bare, unconstrained: `{"Decimal"}`, `{"Whole number"}`, `{"Short Date"}`.
- Type + modifiers: `{"Decimal": {"min": 0}}`, `{"Whole number": {"min": 1, "max": 10,
  "required": True}}` -- a constraint-type mapped to modifiers (`min`/`max`/`required`).
  `Whole number` maps to a DB `Integer` column (step=1); `Decimal` to `Numeric`.
- Dropdown/Boolean options: `{"List": ["Operator", "Service Company", "Report"]}` -- a
  genuine list literal, so option order is preserved directly by `ast.literal_eval` (no
  order-preserving-regex workaround needed, unlike a set).
- Text, unconstrained: `{"Any Value": {}}`.
- Multi-number Text fields (sub-values in one cell), e.g. `Mud PSD`: one spec per
  sub-value, each shaped like a normal Data Validation cell -- so sub-values can carry
  independent types/constraints. The two multi-number cells on the current sheet write
  this as `{["Decimal": {"min": 0}, "Decimal": {"min": 0}, "Decimal": {"min": 0}]}`,
  which is not valid literal syntax on its own; `parse_validation_cell` recovers it
  segment-by-segment. A cleanly-written `[{"Decimal": {"min": 0}}, ...]` list-of-specs
  parses directly and is the preferred shape for any *new* multi-number cell. Either
  way, sub-field labels come from the `Unit` column if it's slash-delimited and the
  count matches (`D10 / D50 / D90`); otherwise from a trailing slash-delimited run in
  the Parameter name itself (`Particle Size Distribution D10/D25/D40/D50/D75/D90`);
  otherwise generic `Value 1`, `Value 2`, ... -- see "Known open items" for the two
  current cells that fall back to the generic labels.

**`Affected Subcategory` / `Affected Parameter`** -- an older, unchanged trigger ->
target DSL, placed on the **triggering** row: `{"TriggerValue": {"Target1", "Target2"}}`
-- a target listed as a plain set member means **show on match** (the target starts
hidden; the original convention). `{"TriggerValue": {"Target": False}}` -- a target
mapped to `False` means **hide on match** (the target starts visible; the newer
"exclude" convention, e.g. `Operating environment = Onshore` hiding `Water
depth`/`Tree type`). Both can apply to the same target from different rules. Targets are
generally scoped to the triggering row's own `Category`, though a rule can deliberately
cross category boundaries within the same repeatable block (e.g. `Completion Type`
revealing a Parameter in a different Category after the `Sand Control` -> `Completion`
consolidation, see "Known open items").

The parser is fully consistent on the current sheet -- every `Affected Subcategory` /
`Affected Parameter` cell, and 136 of 138 `Data Validation` cells, parse cleanly via
plain `ast.literal_eval`; the remaining 2 (both multi-number Text cells) parse via the
segment-recovery fallback described above. Zero cells fail outright.

## Form behavior (`form/generate_form.py` output)

- `General Information`, `Well Specific`, and any other Well-scope Category render once
  at the top, each as a bordered "zone" with a colored header.
- Completion Intervals render as an independently repeatable block (default cap: 10,
  `--max-completion-intervals`). Each Completion Interval block contains its own nested,
  independently repeatable Sand Body blocks (default cap: 10 per parent,
  `--max-sand-bodies`) -- a genuine two-level nested repeater, each level
  numbering and coloring independently.
- A "+ Apply" button next to each of the two counter fields (`Number of Completion
  Intervals`, `Number of sand bodies`) grows the corresponding repeater to
  match a typed number; it only ever adds blocks, never removes them.
- At least one Completion Interval and, within it, at least one Sand Body are
  always present -- their "Remove" buttons refuse to delete the last remaining one
  and show an alert instead.
- Every field gets a "?" tooltip icon (hover/focus) sourced from the `Tooltip` column,
  and a red `*` marker for fields the dictionary marks `required`.
- Category names are never shown as headings inside Completion Interval/Sand Body
  blocks (only Subcategory headings) -- matches the original Main Sheet convention.
- Conditional visibility (`data-show-if`/`data-hide-if`) is evaluated per block
  instance, scoped to that instance's own DOM subtree, so cloned blocks behave
  independently.
- **Export as JSON**: `{ generated_at, well: {Category: {Subcategory: {Parameter:
  value}}}, completion_intervals: [ { fields: {...}, sand_bodies: [{...}, ...]
  }, ... ] }`. This exact shape is also the backend's `POST /records` ingest payload
  shape (see below) -- wiring the form's export buttons to actually POST to a live API
  instead of downloading a file is a deliberate next step, not yet built.
- **Export as CSV**: long format `Category, Subcategory, Parameter, Completion
  Interval, Sand Body, Value, Unit` (interval-index columns blank for
  well-scope rows).
- No backend calls from the static form today -- both exports are client-side (`Blob` +
  download link).

## Color system

| Zone | Header/banner bg | Row bg |
|---|---|---|
| Table column headers | `#203864` (white bold text) | -- |
| `General Information` | `#FFD966` | `#FFF2CC` |
| `Well Specific` | `#9DC3E6` | `#DEEBF7` |
| Completion Interval, odd instance | `#A9D18E` | `#E2F0D9` |
| Completion Interval, even instance | `#F4B183` | `#FBE5D6` |
| Sand Body, odd instance | `#B4A7D6` | `#EDE7F6` |
| Sand Body, even instance | `#EA9999` | `#FBE4E4` |

Numbering/coloring for Sand Body blocks resets within each Completion
Interval parent (local, not global, odd/even). Banner/heading text is `#002060`
(navy), bold. These values live in the `CSS` constant in `form/generate_form.py`.

## Database & API architecture

### Schema

Four tables, generated to mirror the dictionary's own hierarchy plus company
ownership:

- `organizations` -- one row per company. `api_token_hash` (SHA-256 hex digest) is the
  only credential stored; the plaintext token is shown once, at creation time.
- `well` -- structural/audit columns (`id`, `organization_id`, `created_at`,
  `updated_at`, `submitted_at`, `raw_payload` JSONB) + one column per Well-scope
  Parameter (62 currently).
- `completion_interval` -- `id`, `well_id` (FK, `ON DELETE CASCADE`), `ordinal`
  (1-based submission order, **not** used for referential integrity), timestamps + the
  ~49 Completion-Interval-scope columns (47 rows; 1 multi-number row expands into 3
  columns). `UNIQUE(well_id, ordinal)`.
- `sand_body` -- same pattern, FK to `completion_interval.id`, + the ~33 Sand-Body-scope
  columns (29 rows; 1 multi-number row expands into 5 columns). `UNIQUE(completion_interval_id,
  ordinal)`.

Design decisions worth knowing before touching this:

- **Dictionary-driven columns are all nullable**, even ones marked `required` in the
  dictionary. Required-ness, dropdown allow-lists, and numeric min/max are all enforced
  at the API layer (`db/mapping.py`, driven by `db/generated/field_registry.json`), not
  by DB constraints -- keeps the dictionary as the single source of truth for
  validation rules and avoids a migration every time a constraint changes.
- **Boolean-type Parameters become real Postgres `BOOLEAN`** columns (not `TEXT` like
  dropdowns) -- a small, stable Yes/No domain, worth the better queryability. The
  ingest layer normalizes `"Yes"`/`"No"` strings to Python `True`/`False` and back.
  Dropdown/Text Parameters stay plain `TEXT`; no per-dropdown lookup tables (~40+
  dropdown fields would be excessive schema surface for centrally-curated value lists).
- Integer primary keys (not UUID) -- the database is private, not exposing enumeration
  outside org-token-gated access.
- `GET /records/{id}` is scoped to the requesting org's own records; a record that
  exists but belongs to another org returns 404 (not 403) -- no existence leak.

### Codegen pipeline (`db/codegen.py`)

Reuses `dictionary.load_dictionary()` + `dictionary.classify_field()` directly. For
each of the 3 scopes it slugifies each Parameter name into a column name
(`db/naming.py`; multi-number rows expand into N names from their sub-labels), maps the
Input Type to a SQLAlchemy type (`db/type_mapping.py`), and emits two kinds of
committed, generated-not-hand-edited output:

- `db/generated/{well,completion_interval,sand_body}_columns.py` -- plain
  lists of `Column(...)` definitions, combined with a handful of structural columns in
  `db/models/*.py` via SQLAlchemy's imperative-`Table` + declarative-class pattern.
- `db/generated/field_registry.json` -- one entry per dictionary row (keyed
  `"scope::category::subcategory::parameter"`), recording its DB column(s), kind,
  options, min/max/step, and required flag. This is what `db/mapping.py` reads at
  runtime to validate and flatten/unflatten API payloads (`flatten_bucket` /
  `build_record_out`) -- the same function both the Pydantic validators and the
  persistence service call, so there's exactly one place that knows what a submitted
  "bucket" means.

**Workflow after editing `MASTER.xlsx`**: `python -m db.codegen` -->
`python form/generate_form.py` --> `cd db && alembic revision --autogenerate -m "..."`
(hand-review; autogenerate can't detect a rename, only a drop+add) --> `alembic upgrade
head` --> run tests --> commit the `MASTER.xlsx` diff + regenerated files + migration
together. CI re-runs the two regeneration commands and fails the build on any diff in
the committed generated files (the "codegen drift check").

The initial migration (`db/migrations/versions/..._initial_schema.py`) and the second
migration (`..._restructure_completion_interval_sand_body.py`, which replaced
`production_interval`/`completion_interval` with `completion_interval`/`sand_body` when
the scope hierarchy was renamed) are both exceptions to "always use `--autogenerate`":
both were authored without a live Postgres available to diff against, and the second is
also a genuine restructuring -- both parent/child relationships and column sets
changed -- not something `--autogenerate` could express as a rename even with a live
database, so it explicitly drops the old-shape tables and creates the new-shape ones
rather than attempting an in-place data migration (there's no production data yet to
preserve -- see "Path to production"). Every migration after these two should go back
to the normal `--autogenerate` workflow.

Both migrations use explicit `op.create_table()`/`op.drop_table()`/`op.add_column()`
calls with literal column lists, **not** `Base.metadata.create_all()`/`drop_all()`
against the live `db.models`. The initial migration originally did use
`create_all()`/`drop_all()` (justified the same way -- no live Postgres to hand-transcribe
~150 columns against), but that turned out to be a real bug once a second migration
changed the schema: `Base.metadata` is a shared, mutable registry reflecting whatever
`db.models` *currently* says, not a frozen snapshot of what the initial migration
originally created, so once `db.models` moved to the new shape, `create_all()` started
silently building the *new* shape in the initial migration too -- skipping the old shape
entirely and making the second migration's `DROP TABLE` calls fail against dependents
(e.g. `sand_body`) that shouldn't have existed yet at that point in the chain. Lesson:
migrations must be frozen historical records independent of current code, so
`create_all()`/`drop_all()`-against-live-metadata is only safe for a migration that will
never be followed by another one that changes the models -- never assume that in
advance.

### Backend API (`backend/`)

FastAPI, sync SQLAlchemy `Session` (not async -- simpler, more mature Alembic
support). `Authorization: Bearer <token>` org auth (`backend/app/deps/auth.py`), hashed
and compared against `organizations.api_token_hash`. Routes: `GET /health` (round-trips
a real query), `POST /records` (submit -- one transaction: well -> its completion
intervals -> their sand bodies), `GET /records/{id}` (fetch, org-scoped). The
ingest payload's shape is the same nested `Category -> Subcategory -> Parameter ->
value` structure the form's own JSON export produces, modeled as generic nested dicts
in `backend/app/schemas/ingest.py` rather than ~145 named fields, validated by
`db/mapping.py`.

### Local reproducibility

`docker compose up --build` starts Postgres (**no host port mapping** -- reachable only
from the `backend` container, never from the host machine or outside) and the backend
(published on `:8000`, the only intended public surface). The backend's entrypoint runs
migrations, then optionally seeds 1-2 dev-only organizations with known API tokens
(`SEED_DEV_DATA=true` by default, printed to logs -- never enable this against anything
resembling production).

### Testing strategy

Real Postgres, not a mock or SQLite stand-in -- both because Postgres-specific types
(`JSONB`) are in play and because a schema this size deserves real integration
coverage. Locally, point `TEST_DATABASE_URL` at any Postgres you control (e.g. the
`docker compose` `db` service with a temporary host port mapping). In CI, a native
GitHub Actions `services:` Postgres container. Tests needing a database skip cleanly
(not fail) when no URL is configured, so the DB-independent majority of the suite
(dictionary parsing, codegen, schema construction) always runs with zero setup.
`tests/conftest.py`'s `db_session` fixture uses SQLAlchemy 2.0's
`join_transaction_mode="create_savepoint"` so that application code calling
`session.commit()` (the ingest service does) still rolls back cleanly at the end of
each test.

### Explicitly deferred (not built yet)

- Per-user accounts/roles (currently: one shared API token per organization). Adding a
  `users` table with an `organization_id` FK later doesn't require changing how
  existing records are owned.
- An admin/data-review dashboard.
- A production hosting/deployment target (the repo is deployment-target-agnostic today
  -- standard Docker images + documented env vars).
- Wiring the static HTML form's Export buttons to actually `POST` to a live API instead
  of downloading a file.

## Path to production

Everything above is built and tested, but the system isn't ready to hold real
company data yet. Remaining work, grouped by when it's needed:

**Before onboarding a real company**
- Admin/CLI path to create a real organization + API token (today only
  `db/seed/dev_organizations.py`, which is dev-only).
- Token revocation/rotation mechanism.
- CORS configuration in `backend/app/main.py` (needed once the form is served
  from a different origin than the API).
- Decide and document a data-retention / confidentiality policy for shared,
  multi-company well data.

**Before deploying anywhere real**
- Choose a production hosting target (currently undecided -- repo is
  deployment-agnostic, see "Explicitly deferred" above).
- TLS/HTTPS termination (reverse proxy or platform load balancer).
- Secrets management beyond `.env` (e.g. a secrets manager, not plaintext env
  vars).
- Automated Postgres backups/snapshots + a documented restore procedure.
- Structured logging / error tracking (e.g. Sentry) -- right now an
  unhandled exception just vanishes into container stdout.
- Uptime monitoring/alerting wired to `GET /health`.
- Rate limiting on `POST /records`.
- Tune SQLAlchemy connection pool sizing for concurrent load (`db/session.py`
  currently uses defaults plus `pool_pre_ping`).

**API maturity**
- API versioning scheme (`/v1/...`).
- Pagination/listing endpoint -- companies can currently only fetch a record
  by id, not list their own.
- Update/delete/correction path for submitted records (currently
  append-only).

## Regenerating the form / schema

```
pip install -e ".[dev]"                    # one-time
python -m db.codegen                        # reads MASTER.xlsx, writes db/generated/*
python form/generate_form.py                # reads MASTER.xlsx, writes form/sand_control_form.html
cd db && alembic revision --autogenerate -m "describe the change" && alembic upgrade head
```

See the README for the full local-dev and Docker workflows.

## Known open items / suggested improvements

- **`Chemical Sand Consolidation`**: present as a Subcategory under `Sand Control` in
  the old long-format Data Dictionary (resin/chemical consolidation treatments), absent
  from the current `MasterView`. Confirm whether that was intentional.
- **`Mud PSD` lost its D10/D50/D90 sub-labels**: its `Unit` cell is now blank (it used to
  be the slash-delimited `D10 / D50 / D90` that drove sub-field labels) and its
  Parameter name has no trailing slash-delimited suffix either, so its 3 sub-values now
  render/store as generic `Value 1`/`Value 2`/`Value 3` (DB columns `mud_psd_value_1`,
  `_value_2`, `_value_3`) instead of `mud_psd_d10`/`_d50`/`_d90`. Confirm whether the
  blank `Unit` was intentional; if not, restoring `D10 / D50 / D90` in that cell will
  restore the specific labels/column names next time the pipeline is regenerated.
- **`Particle Size Distribution D10/D25/D40/D50/D75/D90`'s `Data Validation` cell has only
  5 `"Decimal"` entries, not 6**: the Parameter name implies 6 sub-values, but the cell
  (`{["Decimal": {"min": 0}, ...]}`, 5 repeats) only defines 5, so the count-must-match
  guard falls back to generic `Value 1`..`Value 5` labels rather than guessing which of
  the 6 D-labels to drop. Likely a missing 6th `"Decimal": {"min": 0}` entry -- confirm
  and add it if so.
- **Counter-field/repeater relationship**: `Number of Completion Intervals` and `Number
  of sand bodies` are informational only (see "Scope hierarchy" above) -- if a
  stronger guarantee is ever wanted (e.g. rejecting a mismatch between the stated count
  and the actual submitted count), that would need explicit product/API design, not
  just a schema change.

Resolved since the last major dictionary revision (kept here briefly for continuity,
remove once stale): the `Completion Details` Category/Subcategory name collision was
resolved by consolidating `Sand Control` into `Completion`; `Data Validation` bracing
inconsistency was resolved by moving to the Python-literal-safe DSL described above
(100% parseable); every row now has a `Tooltip`; trailing whitespace in Parameter names
was cleaned up; the `Max Sand Rate`/`Average Sand Rate` casing mismatch in `Sand rate
quantification`'s `Affected Parameter` rule was fixed; `Production Interval Length` was
renamed to `Completion Interval Length` to match its actual scope. Most recently: the
scope hierarchy was renamed from `Well -> Production Interval {id} -> Completion
Interval {id}` to `Well -> Completion Interval {id} -> Sand Body {id}` (which also
resolved the previous "Modeling granularity" naming-vs-reality mismatch noted here --
the level holding equipment/design fields is now actually called "Completion Interval",
and the level holding per-sand-body reservoir/cleanup fields is now actually called
"Sand Body"), and `Data Validation` was redone from the `{"Positive Integer": {"min":
1}}`-style DSL to the Excel-Data-Validation-flavored `{"Whole number": {"min": 1}}`
style described above.
