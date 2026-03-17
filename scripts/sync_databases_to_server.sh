#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOCAL_DATA_DIR="${ROOT_DIR}/data"
REMOTE_HOST="${REMOTE_HOST:-${1:-}}"
REMOTE_DIR="${REMOTE_DIR:-/var/www/openclaw-watchboard/data}"
PM2_APP_NAME="${PM2_APP_NAME:-openclaw-backend}"

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "Usage: REMOTE_HOST=<ssh-host> $0" >&2
  echo "   or: $0 <ssh-host>" >&2
  exit 1
fi

if [[ ! -d "${LOCAL_DATA_DIR}" ]]; then
  echo "Local data directory not found: ${LOCAL_DATA_DIR}" >&2
  exit 1
fi

LOCAL_DBS=()
while IFS= read -r local_db; do
  [[ -z "${local_db}" ]] && continue
  LOCAL_DBS+=("${local_db}")
done < <(find "${LOCAL_DATA_DIR}" -maxdepth 1 -type f -name '*.db' | sort)

if [[ "${#LOCAL_DBS[@]}" -eq 0 ]]; then
  echo "No local .db files found in: ${LOCAL_DATA_DIR}" >&2
  exit 1
fi

timestamp="$(date +%Y%m%d%H%M%S)"
db_count="${#LOCAL_DBS[@]}"

echo "Syncing ${db_count} database file(s) from ${LOCAL_DATA_DIR} to ${REMOTE_HOST}:${REMOTE_DIR}"
ssh "${REMOTE_HOST}" "mkdir -p '${REMOTE_DIR}'"

for local_db in "${LOCAL_DBS[@]}"; do
  db_name="$(basename "${local_db}")"
  remote_db="${REMOTE_DIR}/${db_name}"
  echo "Uploading ${db_name}"
  ssh "${REMOTE_HOST}" "if [[ -f '${remote_db}' ]]; then cp '${remote_db}' '${remote_db}.${timestamp}.bak'; fi"
  scp "${local_db}" "${REMOTE_HOST}:${remote_db}" < /dev/null
done

ssh "${REMOTE_HOST}" "pm2 restart '${PM2_APP_NAME}'"

echo "Database sync complete for ${REMOTE_HOST}."
