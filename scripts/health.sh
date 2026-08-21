#!/usr/bin/env bash
set -Eeuo pipefail

BACKEND_URL="http://127.0.0.1:8000"

echo "== ByNET health check =="

echo -n "PostgreSQL container: "
if sudo docker inspect \
  --format='{{.State.Health.Status}}' \
  bynet-postgres 2>/dev/null | grep -qx healthy; then
  echo "OK"
else
  echo "FAILED"
  exit 1
fi

echo -n "Backend liveness: "
curl --fail --silent --show-error \
  "${BACKEND_URL}/health/live" >/dev/null
echo "OK"

echo -n "Backend readiness: "
curl --fail --silent --show-error \
  "${BACKEND_URL}/health/ready" >/dev/null
echo "OK"

echo -n "Products API: "
curl --fail --silent --show-error \
  "${BACKEND_URL}/api/v1/products" >/dev/null
echo "OK"

echo
echo "All runtime health checks passed."
