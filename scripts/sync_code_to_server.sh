#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REMOTE_HOST="${REMOTE_HOST:-${1:-}}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/var/www/openclaw-watchboard}"
REMOTE_TMP_DIR="${REMOTE_TMP_DIR:-/tmp/openclaw-deploy}"
PM2_APP_NAME="${PM2_APP_NAME:-openclaw-backend}"
REMOTE_BUILD_CMD="${REMOTE_BUILD_CMD:-npm run build:shared && npm run build:backend && npm run build:frontend}"
ARCHIVE_BASENAME="openclaw-watchboard-code-$(date +%Y%m%d%H%M%S).tgz"
LOCAL_ARCHIVE_PATH="/tmp/${ARCHIVE_BASENAME}"
REMOTE_ARCHIVE_PATH="${REMOTE_TMP_DIR}/${ARCHIVE_BASENAME}"

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "Usage: REMOTE_HOST=<ssh-host> $0" >&2
  echo "   or: $0 <ssh-host>" >&2
  exit 1
fi

echo "Packaging code archive: ${LOCAL_ARCHIVE_PATH}"
tar \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='frontend/node_modules' \
  --exclude='backend/node_modules' \
  --exclude='shared/node_modules' \
  --exclude='data' \
  --exclude='*.db' \
  --exclude='.DS_Store' \
  -czf "${LOCAL_ARCHIVE_PATH}" \
  -C "${ROOT_DIR}" .

echo "Uploading code archive to ${REMOTE_HOST}:${REMOTE_ARCHIVE_PATH}"
ssh "${REMOTE_HOST}" "mkdir -p '${REMOTE_TMP_DIR}' '${REMOTE_APP_DIR}'"
scp "${LOCAL_ARCHIVE_PATH}" "${REMOTE_HOST}:${REMOTE_ARCHIVE_PATH}"

echo "Extracting archive on ${REMOTE_HOST}"
ssh "${REMOTE_HOST}" "tar -xzf '${REMOTE_ARCHIVE_PATH}' -C '${REMOTE_APP_DIR}'"

echo "Running remote build without reinstalling dependencies"
ssh "${REMOTE_HOST}" "cd '${REMOTE_APP_DIR}' && ${REMOTE_BUILD_CMD}"

echo "Restarting PM2 app ${PM2_APP_NAME}"
ssh "${REMOTE_HOST}" "pm2 restart '${PM2_APP_NAME}'"

echo "Cleaning up uploaded archive"
ssh "${REMOTE_HOST}" "rm -f '${REMOTE_ARCHIVE_PATH}'"
rm -f "${LOCAL_ARCHIVE_PATH}"

echo "Code sync complete for ${REMOTE_HOST}."
