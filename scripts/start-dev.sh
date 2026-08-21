#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT}/.run"
LOG_DIR="${ROOT}/logs"

mkdir -p \
  "${RUN_DIR}" \
  "${LOG_DIR}/backend" \
  "${LOG_DIR}/frontend"

echo "Starting PostgreSQL..."

sudo docker compose \
  -f "${ROOT}/infra/docker-compose.dev.yml" \
  up -d postgres

echo "Waiting for PostgreSQL health..."

for _ in $(seq 1 30); do
  if sudo docker inspect \
    --format='{{.State.Health.Status}}' \
    bynet-postgres 2>/dev/null | grep -qx healthy; then
    break
  fi

  sleep 1
done

if ! sudo docker inspect \
  --format='{{.State.Health.Status}}' \
  bynet-postgres 2>/dev/null | grep -qx healthy; then
  echo "PostgreSQL did not become healthy."
  exit 1
fi

if ! kill -0 "$(cat "${RUN_DIR}/backend.pid" 2>/dev/null)" 2>/dev/null; then
  rm -f "${RUN_DIR}/backend.pid"

  echo "Starting FastAPI..."

  setsid bash -c "
    cd '${ROOT}/backend'
    source .venv/bin/activate

    exec uvicorn app.main:app \
      --host 127.0.0.1 \
      --port 8000 \
      --no-access-log \
      --no-server-header
  " >>"${LOG_DIR}/backend/backend.log" 2>&1 &

  echo $! > "${RUN_DIR}/backend.pid"
fi

for _ in $(seq 1 30); do
  if curl --fail --silent \
    http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    break
  fi

  sleep 1
done

if ! curl --fail --silent \
  http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
  echo "Backend did not become ready."
  exit 1
fi

if ! kill -0 "$(cat "${RUN_DIR}/frontend.pid" 2>/dev/null)" 2>/dev/null; then
  rm -f "${RUN_DIR}/frontend.pid"

  echo "Starting Next.js..."

  setsid bash -c "
    cd '${ROOT}/frontend'

    exec ./node_modules/.bin/next dev \
      --hostname 127.0.0.1 \
      --port 3000
  " >>"${LOG_DIR}/frontend/frontend.log" 2>&1 &

  echo $! > "${RUN_DIR}/frontend.pid"
fi

for _ in $(seq 1 30); do
  if curl --fail --silent \
    http://127.0.0.1:3000 >/dev/null 2>&1; then
    break
  fi

  sleep 1
done

if ! curl --fail --silent \
  http://127.0.0.1:3000 >/dev/null 2>&1; then
  echo "Frontend did not become ready."
  exit 1
fi

echo
echo "ByNET development services started."
echo "Backend internal:  http://127.0.0.1:8000"
echo "Frontend internal: http://127.0.0.1:3000"
echo
echo "Logs:"
echo "  ${LOG_DIR}/backend/backend.log"
echo "  ${LOG_DIR}/frontend/frontend.log"
