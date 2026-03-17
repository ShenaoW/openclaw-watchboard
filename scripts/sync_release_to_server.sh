#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_HOST="${REMOTE_HOST:-${1:-}}"

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "Usage: REMOTE_HOST=<ssh-host> $0" >&2
  echo "   or: $0 <ssh-host>" >&2
  exit 1
fi

/bin/bash "${SCRIPT_DIR}/sync_code_to_server.sh" "${REMOTE_HOST}"
/bin/bash "${SCRIPT_DIR}/sync_databases_to_server.sh" "${REMOTE_HOST}"

echo "Release sync complete for ${REMOTE_HOST}."
