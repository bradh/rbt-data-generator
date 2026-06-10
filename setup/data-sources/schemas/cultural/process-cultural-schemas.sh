#!/bin/bash
set -euo pipefail

# =============================================================================
# Cultural schema dispatcher
# =============================================================================
# Runs one or more cultural PL/pgSQL files via psql. Data-driven by the
# LAYER_FILES map below.
#
# Usage:
#   ./process-cultural-schemas.sh --all
#   ./process-cultural-schemas.sh --highway --railway
#   ./process-cultural-schemas.sh --cultural
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

source "${PROJECT_ROOT}/scripts/lib/logging.sh"
source "${PROJECT_ROOT}/scripts/lib/config.sh"
rbt_config_load

declare -A LAYER_FILES=(
    [cultural]="cultural-core.sql"
    [highway]="transportation.sql"
    [railway]="transportation-railway.sql"
    [aero]="infrastructure.sql"
)

ALL_LAYERS=(cultural highway railway aero)
LOG_DIR="${SHARED_LOG_DIR:-${PROJECT_ROOT}/output/logs}"
mkdir -p "${LOG_DIR}"

rbt_log_init "${LOG_DIR}/cultural_schemas_$(date +%Y%m%d_%H%M%S).log"

show_usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Process cultural layer SQL files.

Options:
  --all        Run all cultural schemas (${ALL_LAYERS[*]})
  --cultural   Run only cultural-core.sql
  --highway    Run only transportation.sql
  --railway    Run only transportation-railway.sql
  --aero       Run only infrastructure.sql
  --help       Show this help
EOF
}

run_layer() {
    local layer="$1"
    local sql_file="${LAYER_FILES[$layer]:-}"
    if [[ -z "${sql_file}" ]]; then
        rbt_log "ERROR" "Unknown layer: ${layer}"
        return 2
    fi

    rbt_log "STEP" "Processing cultural/${layer} (${sql_file})"
    local per_run_log="${LOG_DIR}/${layer}_execution_$(date +%Y%m%d_%H%M%S).log"

    if (cd "${SCRIPT_DIR}" && psql -f "${sql_file}") 2>&1 | tee "${per_run_log}"; then
        rbt_log "SUCCESS" "cultural/${layer} completed"
    else
        rbt_log "ERROR" "cultural/${layer} failed — see ${per_run_log}"
        return 1
    fi
}

main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi

    local selected=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all) selected=("${ALL_LAYERS[@]}") ;;
            --cultural|--highway|--railway|--aero) selected+=("${1#--}") ;;
            --help|-h) show_usage; exit 0 ;;
            *) rbt_log "ERROR" "Unknown option: $1"; show_usage; exit 1 ;;
        esac
        shift
    done

    if [[ ${#selected[@]} -eq 0 ]]; then
        rbt_log "ERROR" "No layers selected"
        show_usage
        exit 1
    fi

    for layer in "${selected[@]}"; do
        run_layer "${layer}"
    done

    rbt_log "SUCCESS" "Cultural schema processing finished"
}

main "$@"
