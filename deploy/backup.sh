#!/bin/sh
# Daily consistent SQLite backup; keeps 14 days in /home/debian/backups
set -eu
cd /opt/farmapp
mkdir -p /home/debian/backups
out="/home/debian/backups/db-$(date +%F).sqlite3"

# SQLite's online backup API, safe while the app is running
docker compose exec -T backend python -c "import sqlite3; s=sqlite3.connect('/data/db.sqlite3'); d=sqlite3.connect('/tmp/backup.sqlite3'); s.backup(d); d.close(); s.close()"
docker compose cp backend:/tmp/backup.sqlite3 "$out"
docker compose exec -T backend rm -f /tmp/backup.sqlite3
find /home/debian/backups -name 'db-*.sqlite3' -mtime +14 -delete