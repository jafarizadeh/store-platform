#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT}/.run"

stop_process_group() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: not running"
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"

  if kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping ${name}..."

    kill -- "-${pid}" 2>/dev/null || \
      kill "${pid}" 2>/dev/null || true

    for _ in $(seq 1 10); do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi

      sleep 1
    done

    if kill -0 "${pid}" 2>/dev/null; then
      echo "${name} did not stop gracefully; forcing shutdown."

      kill -KILL -- "-${pid}" 2>/dev/null || \
        kill -KILL "${pid}" 2>/dev/null || true
    fi
  fi

  rm -f "${pid_file}"
}

stop_process_group \
  "Next.js" \
  "${RUN_DIR}/frontend.pid"

stop_process_group \
  "FastAPI" \
  "${RUN_DIR}/backend.pid"

echo
echo "Application processes stopped."
echo "PostgreSQL was intentionally left running."
