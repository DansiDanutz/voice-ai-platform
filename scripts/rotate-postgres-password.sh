#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T db sh -eu -c '
  test -n "$POSTGRES_PASSWORD"
  exec psql \
    --set=ON_ERROR_STOP=1 \
    --set=new_password="$POSTGRES_PASSWORD" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB"
' <<'SQL'
ALTER ROLE voice_ai WITH PASSWORD :'new_password';
SQL

echo "PostgreSQL role password updated. The app service can now be restarted."
