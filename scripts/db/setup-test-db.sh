#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT}/infra/docker-compose.dev.yml"
ENV_FILE="${ROOT}/backend/.env.test"

CONTAINER="bynet-postgres"
ADMIN_USER="bynet"

TEST_ROLE="bynet_test"
TEST_DB="bynet_test"

umask 077

command -v openssl >/dev/null 2>&1 || {
    printf 'ERROR: openssl is required.\n' >&2
    exit 1
}

printf 'Starting PostgreSQL if needed...\n'

sudo docker compose \
    -f "${COMPOSE_FILE}" \
    up -d postgres >/dev/null

printf 'Waiting for PostgreSQL...\n'

for _ in $(seq 1 30); do
    if sudo docker exec "${CONTAINER}" \
        pg_isready \
        -U "${ADMIN_USER}" \
        -d postgres >/dev/null 2>&1; then
        break
    fi

    sleep 1
done

if ! sudo docker exec "${CONTAINER}" \
    pg_isready \
    -U "${ADMIN_USER}" \
    -d postgres >/dev/null 2>&1; then
    printf 'ERROR: PostgreSQL did not become ready.\n' >&2
    exit 1
fi

TEST_DB_PASSWORD="$(openssl rand -hex 32)"

printf 'Creating/updating isolated test role and database...\n'

sudo docker exec \
    -i \
    "${CONTAINER}" \
    psql \
    -v ON_ERROR_STOP=1 \
    -U "${ADMIN_USER}" \
    -d postgres \
    -v "test_password=${TEST_DB_PASSWORD}" <<'SQL'
SELECT
    'CREATE ROLE bynet_test
        LOGIN
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        NOREPLICATION
        NOBYPASSRLS'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'bynet_test'
)
\gexec

ALTER ROLE bynet_test
    WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    PASSWORD :'test_password';

SELECT
    'CREATE DATABASE bynet_test OWNER bynet_test'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'bynet_test'
)
\gexec

ALTER DATABASE bynet_test OWNER TO bynet_test;

REVOKE CONNECT ON DATABASE bynet_test FROM PUBLIC;
GRANT CONNECT ON DATABASE bynet_test TO bynet_test;
SQL

sudo docker exec \
    -i \
    "${CONTAINER}" \
    psql \
    -v ON_ERROR_STOP=1 \
    -U "${ADMIN_USER}" \
    -d "${TEST_DB}" <<'SQL'
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO bynet_test;
SQL

cat > "${ENV_FILE}" <<EOF
TEST_DATABASE_URL=postgresql+psycopg://bynet_test:${TEST_DB_PASSWORD}@127.0.0.1:5433/bynet_test
EOF

chmod 600 "${ENV_FILE}"

unset TEST_DB_PASSWORD

printf '\nTest database ready.\n'
printf 'Database: %s\n' "${TEST_DB}"
printf 'Role:     %s\n' "${TEST_ROLE}"
printf 'Env file: %s (mode 600)\n' "${ENV_FILE}"
