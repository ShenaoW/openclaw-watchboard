from __future__ import annotations

import argparse
import sys

from constants import (
    ALIVE_CSV_PATH,
    CN_CSV_PATH,
    CONFIGS_JSON_PATH,
    DEDUPED_CSV_PATH,
    EXPOSURE_DB_PATH,
    FOFA_CACHE_DIR,
)
from pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch FOFA full data, probe incremental OpenClaw instances, refresh runtime state, and update exposure inputs."
    )
    parser.add_argument("--fofa-input", type=str, help="Use an existing FOFA CSV instead of fetching from FOFA.")
    parser.add_argument("--fofa-key", default="", help="FOFA key.")
    parser.add_argument("--query", default='app="openclaw"', help="FOFA query.")
    parser.add_argument(
        "--fofa-fetch-mode",
        choices=("all",),
        default="all",
        help="FOFA fetch strategy. The current implementation uses search/all paging only.",
    )
    parser.add_argument(
        "--fofa-cache",
        type=str,
        default=str(FOFA_CACHE_DIR / "openclaw_latest.csv"),
        help="Local FOFA cache CSV path. Fresh fetches will update this file.",
    )
    parser.add_argument(
        "--fofa-cache-first",
        action="store_true",
        help="Prefer reading the local FOFA cache. If it does not exist, fetch from FOFA and refresh the cache.",
    )
    parser.add_argument(
        "--fofa-cache-only",
        action="store_true",
        help="Only read the local FOFA cache and do not fetch FOFA remotely.",
    )
    parser.add_argument("--max-records", type=int, default=10000, help="Maximum FOFA records to fetch.")
    parser.add_argument("--page-size", type=int, default=10000, help="FOFA page size. Default uses the maximum allowed page size.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between FOFA requests.")
    parser.add_argument("--fofa-timeout", type=int, default=60, help="Per-request FOFA timeout in seconds.")
    parser.add_argument("--fofa-retries", type=int, default=3, help="Retry count for FOFA request failures.")
    parser.add_argument("--run-dir", type=str, help="Directory for run artifacts.")
    parser.add_argument("--db-path", type=str, default=str(EXPOSURE_DB_PATH), help="SQLite path for probe instance tables.")
    parser.add_argument("--deduped-csv", type=str, default=str(DEDUPED_CSV_PATH), help="Deduped exposure CSV path.")
    parser.add_argument("--alive-csv", type=str, default=str(ALIVE_CSV_PATH), help="Alive probe CSV path.")
    parser.add_argument("--configs-json", type=str, default=str(CONFIGS_JSON_PATH), help="Config payload JSON path.")
    parser.add_argument("--cn-csv", type=str, default=str(CN_CSV_PATH), help="China CSV path.")
    parser.add_argument("--fofa-no-proxy", action="store_true", help="Bypass shell proxy env vars when fetching FOFA data.")
    parser.add_argument("--probe-concurrency", type=int, default=48, help="Concurrency for HTTP probing.")
    parser.add_argument("--probe-timeout", type=int, default=5, help="Per-request timeout in seconds.")
    parser.add_argument(
        "--fofa-fetch-only",
        action="store_true",
        help="Only fetch FOFA data and refresh the local cache/run artifacts. Skip probing and database updates.",
    )
    parser.add_argument("--write-live", action="store_true", help="Write updated CSV inputs and SQLite probe tables.")
    parser.add_argument("--refresh-db", action="store_true", help="Run npm run refresh:exposure-db after updates.")
    args = parser.parse_args()
    if args.fofa_cache_only:
        args.fofa_cache_first = True
    return args


def main() -> int:
    return run_pipeline(parse_args())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f"[openclaw-probe] error: {error}", file=sys.stderr)
        raise SystemExit(1)
