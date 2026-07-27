#!/usr/bin/env bash
set -euo pipefail

database_ready=false
for _attempt in {1..30}; do
  if docker compose exec -T db sh -eu -c '
    exec pg_isready --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"
  ' >/dev/null 2>&1; then
    database_ready=true
    break
  fi
  sleep 2
done

if [[ "$database_ready" != true ]]; then
  echo "PostgreSQL did not become ready within 60 seconds." >&2
  exit 1
fi

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
