#!/bin/bash
set -euo pipefail

# =============================================================================
# RBT Health Check
# =============================================================================
# Used by the Dockerfile HEALTHCHECK and by manual operational checks. Resolves
# configuration via scripts/lib/config.sh so it respects DATABASE_* + legacy PG_*.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${PROJECT_ROOT}/scripts/lib/config.sh" ]]; then
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/scripts/lib/config.sh"
    rbt_config_load >/dev/null 2>&1 || true
fi

DATABASE_HOST="${DATABASE_HOST:-${PG_HOST:-localhost}}"
DATABASE_PORT="${DATABASE_PORT:-${PG_PORT:-5432}}"
DATABASE_NAME="${DATABASE_NAME:-${PG_DATABASE:-rbt}}"
DATABASE_USER="${DATABASE_USER:-${PG_USR:-postgres}}"
DATABASE_PASSWORD="${DATABASE_PASSWORD:-${PG_PASS:-}}"

CONN="host=${DATABASE_HOST} port=${DATABASE_PORT} dbname=${DATABASE_NAME} user=${DATABASE_USER}"
if [[ -n "${DATABASE_PASSWORD}" ]]; then
    CONN="${CONN} password=${DATABASE_PASSWORD}"
fi

status=0

if ! psql "${CONN}" -c "SELECT 1" >/dev/null 2>&1; then
    echo "ERROR: database round-trip failed (${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME})"
    status=1
else
    echo "OK: database reachable"
fi

if ! command -v tippecanoe >/dev/null 2>&1; then
    echo "WARN: tippecanoe not on PATH"
fi

if ! command -v imposm >/dev/null 2>&1; then
    echo "WARN: imposm not on PATH"
fi

exit "${status}"
