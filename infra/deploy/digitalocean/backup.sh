#!/bin/sh
# Nightly PostgreSQL backup: compressed dump into /var/backups/yondo, keeps the last 14 days.
# Run from this folder (cron example in README.md). A copy that lives only on this server is NOT a backup:
# also copy /var/backups/yondo to another place (your computer, object storage) regularly.
set -eu
cd "$(dirname "$0")"
mkdir -p /var/backups/yondo
file="/var/backups/yondo/yondo-$(date +%F).sql.gz"
docker compose exec -T postgres pg_dump -U yondo --no-owner yondo | gzip > "$file"
test -s "$file" || { echo "backup is empty: $file" >&2; rm -f "$file"; exit 1; }
find /var/backups/yondo -name 'yondo-*.sql.gz' -mtime +14 -delete
echo "backup ok: $file"
