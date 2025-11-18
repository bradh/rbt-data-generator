#!/bin/bash

# Shared logging utilities for RBT scripts.

if [[ -n "${RBT_LOGGING_LIB_SOURCED:-}" ]]; then
    return 0 2>/dev/null || exit 0
fi
RBT_LOGGING_LIB_SOURCED=1

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script provides helper functions and must be sourced." >&2
    exit 0
fi

if [[ -t 1 ]]; then
    RBT_COLOR_RED='\033[0;31m'
    RBT_COLOR_GREEN='\033[0;32m'
    RBT_COLOR_YELLOW='\033[1;33m'
    RBT_COLOR_BLUE='\033[0;34m'
    RBT_COLOR_PURPLE='\033[0;35m'
    RBT_COLOR_CYAN='\033[0;36m'
    RBT_COLOR_RESET='\033[0m'
else
    RBT_COLOR_RED=''
    RBT_COLOR_GREEN=''
    RBT_COLOR_YELLOW=''
    RBT_COLOR_BLUE=''
    RBT_COLOR_PURPLE=''
    RBT_COLOR_CYAN=''
    RBT_COLOR_RESET=''
fi

rbt_log_init() {
    local log_file="${1:-}"
    if [[ -n "$log_file" ]]; then
        mkdir -p "$(dirname "$log_file")"
        RBT_LOG_FILE="$log_file"
    fi
}

rbt_log() {
    local level="${1:-INFO}"
    shift || true
    local message="$*"
    if [[ -z "$message" ]]; then
        message="(no message)"
    fi

    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local pid=$$
    local log_line="[${timestamp}] [${pid}] [${level}] ${message}"

    if [[ -n "${RBT_LOG_FILE:-}" ]]; then
        echo "${log_line}" >> "${RBT_LOG_FILE}"
    fi

    local color="${RBT_COLOR_RESET}"
    case "${level}" in
        ERROR) color="${RBT_COLOR_RED}" ;;
        WARN) color="${RBT_COLOR_YELLOW}" ;;
        INFO) color="${RBT_COLOR_GREEN}" ;;
        STEP) color="${RBT_COLOR_PURPLE}" ;;
        DEBUG) color="${RBT_COLOR_CYAN}" ;;
        JOB) color="${RBT_COLOR_CYAN}" ;;
        SUCCESS) color="${RBT_COLOR_GREEN}" ;;
        *) color="${RBT_COLOR_BLUE}" ;;
    esac

    local output_fd=1
    if [[ "${level}" == "ERROR" ]]; then
        output_fd=2
    fi

    local use_color=0
    if [[ -t ${output_fd} || -n "${RBT_FORCE_COLOR:-}" ]]; then
        use_color=1
    fi

    if [[ ${use_color} -eq 1 ]]; then
        printf "%b[%s]%b %s\n" "${color}" "${level}" "${RBT_COLOR_RESET}" "${message}" >&${output_fd}
    else
        printf "[%s] %s\n" "${level}" "${message}" >&${output_fd}
    fi
}

rbt_log_progress() {
    local current="${1:-0}"
    local total="${2:-1}"
    local description="${3:-Progress}"

    if (( total <= 0 )); then
        total=1
    fi

    if (( current < 0 )); then
        current=0
    elif (( current > total )); then
        current=$total
    fi

    local percentage=$((current * 100 / total))
    local completed=$((current * 50 / total))
    local remaining=$((50 - completed))

    local completed_bar
    printf -v completed_bar "%*s" "${completed}" ""
    completed_bar=${completed_bar// /=}

    local remaining_bar
    printf -v remaining_bar "%*s" "${remaining}" ""
    remaining_bar=${remaining_bar// /-}

    local use_color=0
    if [[ -t 1 || -n "${RBT_FORCE_COLOR:-}" ]]; then
        use_color=1
    fi

    if [[ ${use_color} -eq 1 ]]; then
        printf "\r%bProgress: [%s%s] %d%% - %s%b" \
            "${RBT_COLOR_CYAN}" \
            "${completed_bar}" \
            "${remaining_bar}" \
            "${percentage}" \
            "${description}" \
            "${RBT_COLOR_RESET}"
    else
        printf "\rProgress: [%s%s] %d%% - %s" \
            "${completed_bar}" \
            "${remaining_bar}" \
            "${percentage}" \
            "${description}"
    fi

    if (( current == total )); then
        echo ""
    fi
}

