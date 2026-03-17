#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
LOG_DIR="${OPENCLAW_NIGHTLY_LOG_DIR:-${ROOT_DIR}/logs/nightly-refresh}"
LOCK_FILE="${OPENCLAW_NIGHTLY_LOCK_FILE:-/tmp/openclaw-watchboard-nightly.lock}"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
LOG_FILE="${LOG_DIR}/${TIMESTAMP}.log"

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

mkdir -p "${LOG_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[nightly-refresh] started at $(date '+%F %T')"
echo "[nightly-refresh] root_dir=${ROOT_DIR}"
echo "[nightly-refresh] log_file=${LOG_FILE}"

if command -v flock >/dev/null 2>&1; then
  exec 9>"${LOCK_FILE}"
  if ! flock -n 9; then
    echo "[nightly-refresh] another refresh job is already running, exiting"
    exit 1
  fi
else
  LOCK_DIR="${LOCK_FILE}.d"
  if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
    echo "[nightly-refresh] another refresh job is already running, exiting"
    exit 1
  fi
  trap 'rmdir "${LOCK_DIR}"' EXIT
fi

cd "${ROOT_DIR}"

echo "[nightly-refresh] refreshing risks database"
npm run refresh:risks-db

echo "[nightly-refresh] refreshing exposure probe"
npm run refresh:exposure-probe

echo "[nightly-refresh] completed at $(date '+%F %T')"
