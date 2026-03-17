#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROBE_DIR="$ROOT_DIR/tools/openclaw-probe"
ENV_FILE="${OPENCLAW_PROBE_ENV_FILE:-$ROOT_DIR/.env}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_DIR="${OPENCLAW_PROBE_RUN_DIR:-}"
PAGE_SIZE="${OPENCLAW_PROBE_PAGE_SIZE:-10000}"
MAX_RECORDS="${OPENCLAW_PROBE_MAX_RECORDS:-all}"
FOFA_TIMEOUT="${OPENCLAW_PROBE_FOFA_TIMEOUT:-60}"
FOFA_RETRIES="${OPENCLAW_PROBE_FOFA_RETRIES:-3}"
PROBE_CONCURRENCY="${OPENCLAW_PROBE_CONCURRENCY:-48}"
PROBE_TIMEOUT="${OPENCLAW_PROBE_TIMEOUT:-5}"
FETCH_ONLY="${OPENCLAW_PROBE_FETCH_ONLY:-0}"
CACHE_ONLY="${OPENCLAW_PROBE_CACHE_ONLY:-0}"
CACHE_FIRST="${OPENCLAW_PROBE_CACHE_FIRST:-0}"
DAILY_ONLY="${OPENCLAW_PROBE_DAILY_ONLY:-1}"
AFTER_DATE="${OPENCLAW_PROBE_AFTER_DATE:-}"
WRITE_LIVE="${OPENCLAW_PROBE_WRITE_LIVE:-1}"
REFRESH_DB="${OPENCLAW_PROBE_REFRESH_DB:-1}"
FOFA_CACHE_PATH="${OPENCLAW_PROBE_FOFA_CACHE:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

CMD=(
  "$PYTHON_BIN"
  "$PROBE_DIR/fofa_incremental_updater.py"
  --fofa-no-proxy
  --max-records "$MAX_RECORDS"
  --page-size "$PAGE_SIZE"
  --fofa-timeout "$FOFA_TIMEOUT"
  --fofa-retries "$FOFA_RETRIES"
  --probe-concurrency "$PROBE_CONCURRENCY"
  --probe-timeout "$PROBE_TIMEOUT"
)

if [[ -n "${FOFA_KEY:-}" ]]; then
  CMD+=(--fofa-key "$FOFA_KEY")
fi

if [[ -n "$RUN_DIR" ]]; then
  CMD+=(--run-dir "$RUN_DIR")
fi

if [[ -n "$FOFA_CACHE_PATH" ]]; then
  CMD+=(--fofa-cache "$FOFA_CACHE_PATH")
fi

if [[ "$DAILY_ONLY" == "1" ]]; then
  CMD+=(--fofa-daily-only)
fi

if [[ -n "$AFTER_DATE" ]]; then
  CMD+=(--fofa-after-date "$AFTER_DATE")
fi

if [[ "$FETCH_ONLY" == "1" ]]; then
  CMD+=(--fofa-fetch-only)
fi

if [[ "$CACHE_ONLY" == "1" ]]; then
  CMD+=(--fofa-cache-only)
elif [[ "$CACHE_FIRST" == "1" ]]; then
  CMD+=(--fofa-cache-first)
fi

if [[ "$WRITE_LIVE" == "1" ]]; then
  CMD+=(--write-live)
fi

if [[ "$REFRESH_DB" == "1" ]]; then
  CMD+=(--refresh-db)
fi

echo "[openclaw-probe] mode: fetch_only=$FETCH_ONLY cache_only=$CACHE_ONLY cache_first=$CACHE_FIRST daily_only=$DAILY_ONLY after_date=${AFTER_DATE:-auto} write_live=$WRITE_LIVE refresh_db=$REFRESH_DB"
echo "[openclaw-probe] command: ${CMD[*]}"

"${CMD[@]}"
