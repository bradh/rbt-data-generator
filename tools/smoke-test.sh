#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

source "${PROJECT_ROOT}/scripts/lib/config.sh"
rbt_config_load

LOG_DIR="${SHARED_LOG_DIR:-${PROJECT_ROOT}/output/logs}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/smoke_test_$(date +%Y%m%d_%H%M%S).log"

source "${PROJECT_ROOT}/scripts/lib/logging.sh"
rbt_log_init "${LOG_FILE}"

log() {
    rbt_log "$@"
}

log "INFO" "=== RBT Smoke Test Starting ==="

log "INFO" "Step 1: Validating environment"
./tools/validate-environment.sh >/dev/null

log "INFO" "Step 2: Ensuring database and extensions exist"
./setup/init-database.sh --setup-database >/dev/null

log "INFO" "Step 3: Running schema processing sanity check"
./setup/init-database.sh --process-schemas --physical >/dev/null

log "INFO" "Step 4: Tile generation dry runs"
./production/generate-tiles.sh --layer-type physical --projection 3857 --water --dry-run >/dev/null
./production/generate-tiles.sh --layer-type cultural --projection 4326 --building --dry-run >/dev/null

log "INFO" "Step 5: Verifying database connectivity"
psql "$(rbt_psql_conn_string)" -c "SELECT NOW();" >/dev/null

log "INFO" "=== RBT Smoke Test Completed Successfully ==="

