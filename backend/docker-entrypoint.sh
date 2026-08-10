#!/bin/sh
set -e

alembic -c db/alembic.ini upgrade head

if [ "${SEED_DEV_DATA:-false}" = "true" ]; then
  python -m db.seed.dev_organizations
fi

exec "$@"
