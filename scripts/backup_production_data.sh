#!/bin/bash
# Pull a fresh copy of all real production database files off Railway's volume into
# a local, timestamped, git-ignored backup directory -- keeps the "adaptable backup"
# current so a future move to a new server never has to scramble for a data export.
#
# Requires: the `railway` CLI, logged in, linked to this project (same as any other
# `railway` command in this repo).
#
# Usage:
#   bash scripts/backup_production_data.sh
#
# Safe to re-run any time -- each run gets its own dated directory, nothing is
# overwritten or deleted from a previous run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE_STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/data/railway-backup-$DATE_STAMP"

cd "$PROJECT_ROOT"

echo "Looking up the production volume ID..."
VOLUME_ID=$(railway volume list --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
volumes = data.get('volumes', [])
if not volumes:
    print('ERROR: no volumes found on this Railway project', file=sys.stderr)
    sys.exit(1)
if len(volumes) > 1:
    print(f'ERROR: {len(volumes)} volumes found, expected exactly 1 -- edit this script to pick the right one', file=sys.stderr)
    for v in volumes:
        print(f\"  - {v['name']} ({v['id']})\", file=sys.stderr)
    sys.exit(1)
print(volumes[0]['id'])
")

if [ -z "$VOLUME_ID" ]; then
    echo "Could not determine the volume ID. Aborting." >&2
    exit 1
fi

echo "Volume: $VOLUME_ID"
echo "Backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

echo "Listing files on the volume..."
FILE_LIST=$(railway volume files --volume "$VOLUME_ID" list / --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for f in data.get('files', []):
    if f.get('type') == 'file' and f['name'].endswith('.db'):
        print(f\"{f['name']}\t{f['size']}\")
")

if [ -z "$FILE_LIST" ]; then
    echo "No .db files found on the volume -- nothing to back up. Aborting." >&2
    rmdir "$BACKUP_DIR" 2>/dev/null || true
    exit 1
fi

echo "Files to back up:"
echo "$FILE_LIST" | awk -F'\t' '{print "  - " $1 " (" $2 " bytes)"}'
echo

# The railway CLI's file download has been observed to silently stall/truncate on
# larger files (~10MB+) in a single invocation -- verify the downloaded size against
# the volume's reported size and retry (up to 3 attempts) rather than trusting a
# clean exit code alone.
MAX_ATTEMPTS=3
while IFS=$'\t' read -r f expected_size; do
    attempt=1
    ok=false
    while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
        echo "Downloading $f (attempt $attempt/$MAX_ATTEMPTS)..."
        railway volume files --volume "$VOLUME_ID" download "/$f" "$BACKUP_DIR/$f" --overwrite --json > /dev/null
        actual_size=$(stat -f%z "$BACKUP_DIR/$f" 2>/dev/null || stat -c%s "$BACKUP_DIR/$f" 2>/dev/null || echo 0)
        if [ "$actual_size" = "$expected_size" ]; then
            echo "  OK: $actual_size bytes (matches)"
            ok=true
            break
        fi
        echo "  Size mismatch: got $actual_size, expected $expected_size -- retrying"
        attempt=$((attempt + 1))
    done
    if [ "$ok" != true ]; then
        echo "FAILED to download $f correctly after $MAX_ATTEMPTS attempts (got $actual_size, expected $expected_size)." >&2
        exit 1
    fi
done <<< "$FILE_LIST"

echo
echo "Done. Backup contents:"
ls -la "$BACKUP_DIR"
echo
echo "Verifying each file opens cleanly as SQLite..."
for f in "$BACKUP_DIR"/*.db; do
    python3 -c "
import sqlite3, sys
path = '$f'
try:
    conn = sqlite3.connect(path)
    n = conn.execute(\"SELECT count(*) FROM sqlite_master WHERE type='table'\").fetchone()[0]
    print(f'  OK  {path}  ({n} tables)')
except Exception as e:
    print(f'  FAIL {path}: {e}', file=sys.stderr)
    sys.exit(1)
"
done

echo
echo "Backup complete: $BACKUP_DIR"
echo "(This directory is git-ignored via data/railway-backup-*/ -- it will never be committed.)"
