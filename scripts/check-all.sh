#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="${ROOT}/backend"
FRONTEND="${ROOT}/frontend"

CHECK_LOG_DIR="${ROOT}/logs/checks"
RUN_ID="$(date '+%Y%m%d-%H%M%S')"
FULL_LOG="${CHECK_LOG_DIR}/check-all-${RUN_ID}.log"

mkdir -p "${CHECK_LOG_DIR}"

# ---------------------------------------------------------------------------
# Terminal
# ---------------------------------------------------------------------------

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    RESET=$'\033[0m'
    BOLD=$'\033[1m'
    DIM=$'\033[2m'

    RED=$'\033[31m'
    GREEN=$'\033[32m'
    YELLOW=$'\033[33m'
    BLUE=$'\033[34m'
    CYAN=$'\033[36m'
    GRAY=$'\033[90m'
else
    RESET=""
    BOLD=""
    DIM=""

    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    CYAN=""
    GRAY=""
fi

CHECK_MARK="✓"
FAIL_MARK="✗"
RUN_MARK="◆"

TOTAL=0
PASSED=0
FAILED=0

START_TIME="$(date +%s%N)"

declare -a RESULTS=()

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

elapsed_seconds() {
    local start_ns="$1"
    local end_ns="$2"

    awk -v start="${start_ns}" -v end="${end_ns}" \
        'BEGIN { printf "%.2f", (end - start) / 1000000000 }'
}

terminal_width() {
    local cols

    cols="$(tput cols 2>/dev/null || printf '80')"

    if (( cols > 100 )); then
        cols=100
    elif (( cols < 60 )); then
        cols=60
    fi

    printf '%s' "${cols}"
}

horizontal_rule() {
    local width
    local line

    width="$(terminal_width)"

    printf -v line '%*s' "${width}" ''
    line="${line// /─}"

    printf '%s\n' "${line}"
}

print_header() {
    printf '\n'
    printf '%s%s╭────────────────────────────────────────────────────╮%s\n' \
        "${BOLD}" "${CYAN}" "${RESET}"
    printf '%s%s│                 ByNET Quality Gate                 │%s\n' \
        "${BOLD}" "${CYAN}" "${RESET}"
    printf '%s%s│        Security · Tests · Build · Database         │%s\n' \
        "${BOLD}" "${CYAN}" "${RESET}"
    printf '%s%s╰────────────────────────────────────────────────────╯%s\n' \
        "${BOLD}" "${CYAN}" "${RESET}"
    printf '\n'

    printf '%sRun:%s %s\n' \
        "${GRAY}" "${RESET}" "${RUN_ID}"

    printf '%sFull log:%s %s\n' \
        "${GRAY}" "${RESET}" "${FULL_LOG}"

    printf '\n'
}

section() {
    printf '\n%s%s%s%s\n' \
        "${BOLD}" "${BLUE}" "$1" "${RESET}"
}

print_running() {
    local label="$1"

    printf '  %s%s%s %-38s' \
        "${CYAN}" "${RUN_MARK}" "${RESET}" "${label}"
}

print_success() {
    local label="$1"
    local duration="$2"
    local detail="${3:-}"

    printf '\r\033[K'

    printf '  %s%s%s %-38s %s%7ss%s' \
        "${GREEN}" "${CHECK_MARK}" "${RESET}" \
        "${label}" "${GRAY}" "${duration}" "${RESET}"

    if [[ -n "${detail}" ]]; then
        printf '  %s%s%s' \
            "${DIM}" "${detail}" "${RESET}"
    fi

    printf '\n'
}

print_failure() {
    local label="$1"
    local duration="$2"

    printf '\r\033[K'

    printf '  %s%s%s %-38s %s%7ss%s\n' \
        "${RED}" "${FAIL_MARK}" "${RESET}" \
        "${label}" "${GRAY}" "${duration}" "${RESET}"
}

extract_detail() {
    local id="$1"
    local logfile="$2"

    case "${id}" in
        pytest)
            grep -Eo \
                '[0-9]+ passed(, [0-9]+ (warning|warnings))?' \
                "${logfile}" \
                | tail -n 1 \
                || true
            ;;

        pip-audit)
            if grep -Fq \
                'No known vulnerabilities found' \
                "${logfile}"; then
                printf '0 vulnerabilities'
            fi
            ;;

        npm-audit)
            grep -E \
                'found [0-9]+ vulnerabilities' \
                "${logfile}" \
                | tail -n 1 \
                || true
            ;;

        npm-audit-prod)
            grep -E \
                'found [0-9]+ vulnerabilities' \
                "${logfile}" \
                | tail -n 1 \
                || true
            ;;

        alembic)
            if grep -Fq \
                'No new upgrade operations detected.' \
                "${logfile}"; then
                printf 'schema clean'
            fi
            ;;

        next-build)
            if grep -Fq \
                'Compiled successfully' \
                "${logfile}"; then
                printf 'production build'
            fi
            ;;

        *)
            ;;
    esac
}

show_failure_details() {
    local label="$1"
    local command="$2"
    local logfile="$3"

    printf '\n'

    printf '%s%s' "${RED}" "${BOLD}"
    horizontal_rule
    printf '%s' "${RESET}"

    printf '%s%sFAILURE: %s%s\n\n' \
        "${BOLD}" "${RED}" "${label}" "${RESET}"

    printf '%sCommand%s\n' \
        "${BOLD}" "${RESET}"

    printf '%s$ %s%s\n\n' \
        "${GRAY}" "${command}" "${RESET}"

    printf '%sRaw output%s\n' \
        "${BOLD}" "${RESET}"

    printf '%s' "${YELLOW}"

    if [[ -s "${logfile}" ]]; then
        cat "${logfile}"
    else
        printf '(command produced no output)\n'
    fi

    printf '%s\n' "${RESET}"

    printf '%s%s' "${RED}" "${BOLD}"
    horizontal_rule
    printf '%s\n' "${RESET}"
}

run_check() {
    local id="$1"
    local label="$2"
    local cwd="$3"
    local command="$4"

    local logfile
    local start_ns
    local end_ns
    local duration
    local detail
    local exit_code

    TOTAL=$((TOTAL + 1))

    logfile="${CHECK_LOG_DIR}/.${RUN_ID}-${id}.log"

    print_running "${label}"

    start_ns="$(date +%s%N)"

    (
        cd "${cwd}" || exit 127

        printf '================================================================\n'
        printf 'CHECK: %s\n' "${label}"
        printf 'TIME:  %s\n' "$(date --iso-8601=seconds)"
        printf 'DIR:   %s\n' "${cwd}"
        printf 'CMD:   %s\n' "${command}"
        printf '================================================================\n\n'

        bash -o pipefail -c "${command}"
    ) >"${logfile}" 2>&1 &

    local pid=$!

    if wait "${pid}"; then
        exit_code=0
    else
        exit_code=$?
    fi

    end_ns="$(date +%s%N)"
    duration="$(elapsed_seconds "${start_ns}" "${end_ns}")"

    cat "${logfile}" >>"${FULL_LOG}"

    printf '\n' >>"${FULL_LOG}"

    if (( exit_code == 0 )); then
        PASSED=$((PASSED + 1))

        detail="$(extract_detail "${id}" "${logfile}")"

        print_success \
            "${label}" \
            "${duration}" \
            "${detail}"

        RESULTS+=(
            "PASS|${label}|${duration}"
        )

        rm -f "${logfile}"

        return 0
    fi

    FAILED=$((FAILED + 1))

    print_failure "${label}" "${duration}"

    RESULTS+=(
        "FAIL|${label}|${duration}"
    )

    show_failure_details \
        "${label}" \
        "${command}" \
        "${logfile}"

    rm -f "${logfile}"

    return "${exit_code}"
}

final_summary() {
    local end_time
    local total_duration

    end_time="$(date +%s%N)"
    total_duration="$(elapsed_seconds "${START_TIME}" "${end_time}")"

    printf '\n'
    horizontal_rule

    if (( FAILED == 0 )); then
        printf '\n%s%s%s ALL CHECKS PASSED%s\n' \
            "${GREEN}" "${BOLD}" "${CHECK_MARK}" "${RESET}"

        printf '%s%d/%d successful · %ss%s\n' \
            "${GRAY}" "${PASSED}" "${TOTAL}" \
            "${total_duration}" "${RESET}"

        printf '%sLog: %s%s\n' \
            "${GRAY}" "${FULL_LOG}" "${RESET}"
    else
        printf '\n%s%s%s QUALITY GATE FAILED%s\n' \
            "${RED}" "${BOLD}" "${FAIL_MARK}" "${RESET}"

        printf '%s%d passed · %d failed · %ss%s\n' \
            "${GRAY}" "${PASSED}" "${FAILED}" \
            "${total_duration}" "${RESET}"

        printf '%sFull diagnostic log: %s%s\n' \
            "${YELLOW}" "${FULL_LOG}" "${RESET}"
    fi

    printf '\n'
    horizontal_rule
    printf '\n'
}

cleanup_old_logs() {
    find "${CHECK_LOG_DIR}" \
        -type f \
        -name 'check-all-*.log' \
        -mtime +30 \
        -delete 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print_header
cleanup_old_logs

{
    printf 'ByNET Quality Gate\n'
    printf 'Run: %s\n' "${RUN_ID}"
    printf 'Root: %s\n\n' "${ROOT}"
} >"${FULL_LOG}"

section "Backend"

run_check \
    "ruff-lint" \
    "Ruff lint" \
    "${BACKEND}" \
    ".venv/bin/ruff check app scripts ../tests/backend" \
    || {
        final_summary
        exit 1
    }

run_check \
    "ruff-format" \
    "Ruff formatting" \
    "${BACKEND}" \
    ".venv/bin/ruff format --check app scripts ../tests/backend" \
    || {
        final_summary
        exit 1
    }

run_check \
    "bandit" \
    "Bandit security scan" \
    "${BACKEND}" \
    ".venv/bin/bandit -r app -c pyproject.toml" \
    || {
        final_summary
        exit 1
    }

run_check \
    "pytest" \
    "Pytest" \
    "${BACKEND}" \
    ".venv/bin/pytest -q" \
    || {
        final_summary
        exit 1
    }

run_check \
    "pip-audit" \
    "Python dependency audit" \
    "${BACKEND}" \
    ".venv/bin/pip-audit --local" \
    || {
        final_summary
        exit 1
    }

run_check \
    "compile" \
    "Python bytecode compile" \
    "${BACKEND}" \
    ".venv/bin/python -m compileall -q app scripts" \
    || {
        final_summary
        exit 1
    }

run_check \
    "alembic" \
    "Alembic schema check" \
    "${BACKEND}" \
    ".venv/bin/alembic check" \
    || {
        final_summary
        exit 1
    }


section "Frontend"

run_check \
    "eslint" \
    "ESLint" \
    "${FRONTEND}" \
    "npm run lint" \
    || {
        final_summary
        exit 1
    }

run_check \
    "npm-audit" \
    "Dependency audit" \
    "${FRONTEND}" \
    "npm audit --audit-level=high" \
    || {
        final_summary
        exit 1
    }

run_check \
    "npm-audit-prod" \
    "Production dependency audit" \
    "${FRONTEND}" \
    "npm audit --omit=dev --audit-level=moderate" \
    || {
        final_summary
        exit 1
    }

run_check \
    "next-build" \
    "Next.js production build" \
    "${FRONTEND}" \
    "npm run build" \
    || {
        final_summary
        exit 1
    }


final_summary
exit 0
