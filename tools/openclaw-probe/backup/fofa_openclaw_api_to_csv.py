#!/usr/bin/env python3
"""Fetch OpenClaw records from FOFA API and export to CSV with continuous pagination.

Usage example:
    python fofa_openclaw_api_to_csv.py

Security note:
    Fill FOFA_KEY below or use environment variable FOFA_KEY.
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests
from concurrent.futures import ThreadPoolExecutor, Future


API_URL = "http://107.173.248.139:18999/api/v1/search/next"

# Preferred way: keep this empty and provide credential via environment variable.
FOFA_KEY = "rqe9oojwqys9kkgim3vnqglta2eqs6jv"

FIELDS = [
    "ip",
    "port",
    "country_name",
    "region",
    "city",
    "longitude",
    "latitude",
    "asn",
    "org",
    "host",
    "domain",
    "os",
    "server",
    "title",
    "jarm",
    "link",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch app=openclaw records from FOFA and export selected fields to CSV."
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=10000,
        help="Maximum number of records to fetch (default: 10000).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Records per page (default: 1000). FOFA may apply tighter limits for some fields.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path. Default: fofa_openclaw_YYYYMMDD_HHMMSS.csv",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Sleep seconds between page requests (default: 0.2).",
    )
    parser.add_argument(
        "--start-next",
        type=str,
        default="",
        help="Optional next token to resume continuous pagination.",
    )
    return parser.parse_args()


def get_credentials() -> str:
    key = (os.getenv("FOFA_KEY") or FOFA_KEY).strip()
    if not key:
        raise RuntimeError(
            "Missing FOFA credential. Set FOFA_KEY env var or fill FOFA_KEY in script."
        )
    return key


def build_query() -> str:
    # Query required by user: app=openclaw
    return 'app="openclaw"'


def b64_query(query: str) -> str:
    return base64.b64encode(query.encode("utf-8")).decode("ascii")


def fetch_page(
    session: requests.Session,
    key: str,
    query_b64: str,
    fields: list[str],
    next_token: str,
    size: int,
    pre_sleep: float = 0.0,
) -> dict:
    if pre_sleep > 0:
        time.sleep(pre_sleep)
    params = {
        "key": key,
        "qbase64": query_b64,
        "fields": ",".join(fields),
        "size": size,
        "full": "true",
        "r_type": "json",
    }
    if next_token:
        params["next"] = next_token
    resp = session.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        errmsg = data.get("errmsg") or str(data)
        if "40070" in errmsg:
            raise RuntimeError(
                "FOFA API error: [40070] 游标无效或过期。"
                "请检查是否使用官方 search/next 接口、是否沿用同一组 qbase64/fields/size/full 参数、"
                "以及 start-next 是否来自同一查询且未过期。"
            )
        raise RuntimeError(f"FOFA API error: {errmsg}")
    return data


def _to_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def to_row(raw, fields: list[str]) -> list[str]:
    # Some FOFA responses return list rows, while others return dict rows.
    if isinstance(raw, list):
        row = [_to_cell(v) for v in raw]
        if len(row) < len(fields):
            row.extend([""] * (len(fields) - len(row)))
        elif len(row) > len(fields):
            row = row[: len(fields)]
        return row

    if isinstance(raw, dict):
        loc = raw.get("location") if isinstance(raw.get("location"), dict) else {}
        mapped: list[str] = []
        for field in fields:
            if field in raw:
                mapped.append(_to_cell(raw.get(field)))
                continue
            if field in ("country_name", "region", "city", "longitude", "latitude"):
                mapped.append(_to_cell(loc.get(field)))
                continue
            mapped.append("")
        return mapped

    return [""] * len(fields)


def main() -> int:
    args = parse_args()

    if args.max_records <= 0:
        raise ValueError("--max-records must be > 0")
    if args.page_size <= 0:
        raise ValueError("--page-size must be > 0")

    key = get_credentials()

    query = build_query()
    query_b64 = b64_query(query)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.out or Path(f"fofa_openclaw_{ts}.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total_written = 0
    print(f"[INFO] Query: {query}")
    print(f"[INFO] Fields: {','.join(FIELDS)}")
    print(f"[INFO] Max records: {args.max_records}")
    print(f"[INFO] Page size: {args.page_size}")

    if args.start_next.strip():
        next_token = args.start_next.strip()
        print("[INFO] Start next token source: --start-next")
    else:
        next_token = ""
        print("[INFO] Start next token source: <empty>")

    with requests.Session() as session, out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)

        round_no = 0
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Prefetch first page.
            future: Future | None = executor.submit(
                fetch_page,
                session,
                key,
                query_b64,
                FIELDS,
                next_token,
                args.page_size,
                0.0,
            )

            while total_written < args.max_records and future is not None:
                round_no += 1
                remaining = args.max_records - total_written
                request_size = args.page_size

                data = future.result()
                results = data.get("results") or []
                if not results:
                    print("[INFO] No more results.")
                    break

                next_token = (data.get("next") or "").strip()
                to_write = min(len(results), remaining)
                reported_total = data.get("size")

                # Start fetching next page while writing current page.
                if (
                    next_token
                    and len(results) >= request_size
                    and total_written + to_write < args.max_records
                ):
                    future = executor.submit(
                        fetch_page,
                        session,
                        key,
                        query_b64,
                        FIELDS,
                        next_token,
                        request_size,
                        args.sleep,
                    )
                else:
                    future = None

                for item in results[:to_write]:
                    writer.writerow(to_row(item, FIELDS))

                total_written += to_write
                print(
                    f"[INFO] Round {round_no}: got {len(results)} rows, wrote {to_write}, total written {total_written}"
                    + (f", query total {reported_total}" if reported_total is not None else "")
                )

                if not next_token:
                    print("[INFO] No next token returned, reached end of continuous pagination.")
                    break

                if len(results) < request_size:
                    print("[INFO] Reached last page from current query scope.")
                    break

    print(f"[DONE] Wrote {total_written} rows to: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
