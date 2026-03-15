from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
import math
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import ensure_parent, log, read_csv_rows
from constants import FOFA_CACHE_DIR, FOFA_FIELDS, FOFA_SEARCH_ALL_API_URL


def fetch_fofa_page(opener: urllib.request.OpenerDirector, request: urllib.request.Request, timeout: int, retries: int) -> dict:
    last_error: Exception | None = None
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            with opener.open(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt == attempts:
                raise
            time.sleep(min(attempt, 3))

    if last_error is not None:
        raise last_error
    raise RuntimeError("FOFA request failed without a captured exception")


def normalize_fofa_result(item: dict) -> list[str]:
    location = item.get("location") or {}
    os_value = item.get("os")
    if isinstance(os_value, list):
        os_text = ", ".join(str(part) for part in os_value if part not in (None, ""))
    else:
        os_text = str(os_value or "")

    normalized = {
        "ip": str(item.get("ip") or ""),
        "port": str(item.get("port") or ""),
        "country_name": str(location.get("country_name") or item.get("country_name") or ""),
        "region": str(location.get("region") or item.get("region") or ""),
        "city": str(location.get("city") or item.get("city") or ""),
        "longitude": str(location.get("longitude") or item.get("longitude") or ""),
        "latitude": str(location.get("latitude") or item.get("latitude") or ""),
        "asn": str(item.get("asn") or ""),
        "org": str(item.get("org") or ""),
        "host": str(item.get("host") or ""),
        "domain": str(item.get("domain") or ""),
        "os": os_text,
        "server": str(item.get("server") or ""),
        "title": str(item.get("title") or ""),
        "jarm": str(item.get("jarm") or ""),
        "link": str(item.get("link") or ""),
    }
    return [normalized[field] for field in FOFA_FIELDS]


def build_fofa_opener(args: argparse.Namespace) -> urllib.request.OpenerDirector:
    return (
        urllib.request.build_opener(urllib.request.ProxyHandler({}))
        if getattr(args, "fofa_no_proxy", False)
        else urllib.request.build_opener()
    )


def write_fofa_results(writer: csv.writer, results: list) -> int:
    for item in results:
        if isinstance(item, dict):
            writer.writerow(normalize_fofa_result(item))
            continue
        row = list(item[: len(FOFA_FIELDS)])
        if len(row) < len(FOFA_FIELDS):
            row.extend([""] * (len(FOFA_FIELDS) - len(row)))
        writer.writerow(row)
    return len(results)


def parse_total_available(data: dict, fallback_count: int) -> int:
    value = data.get("size")
    if isinstance(value, int):
        return max(value, fallback_count)
    if isinstance(value, str) and value.isdigit():
        return max(int(value), fallback_count)
    return fallback_count


def fetch_fofa_all_mode(args: argparse.Namespace, writer: csv.writer, opener: urllib.request.OpenerDirector, qbase64: str) -> int:
    requested_page_size = max(1, min(args.page_size, args.max_records, 10000))
    params = {
        "key": args.fofa_key,
        "qbase64": qbase64,
        "fields": ",".join(FOFA_FIELDS),
        "size": requested_page_size,
        "page": 1,
        "full": "true",
        "r_type": "json",
    }
    request = urllib.request.Request(
        f"{FOFA_SEARCH_ALL_API_URL}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "openclaw-probe/1.0"},
    )
    first_page = fetch_fofa_page(opener, request, args.fofa_timeout, args.fofa_retries)
    if first_page.get("error"):
        raise RuntimeError(f"FOFA API error: {str(first_page.get('errmsg') or first_page)}")

    first_results = first_page.get("results") or []
    if not first_results:
        log("FOFA search/all returned no results")
        return 0

    total_available = parse_total_available(first_page, len(first_results))
    total_target = min(args.max_records, total_available)
    per_page = max(1, min(requested_page_size, total_target))
    total_pages = max(1, math.ceil(total_target / per_page))

    log(
        f"FOFA search/all plan: available={total_available}, target={total_target}, "
        f"page_size={per_page}, pages={total_pages}"
    )

    total_written = write_fofa_results(writer, first_results[:total_target])
    if total_pages == 1 or total_written >= total_target:
        return total_written

    for page in range(2, total_pages + 1):
        remaining = total_target - total_written
        if remaining <= 0:
            break
        page_size = min(per_page, remaining)
        params = {
            "key": args.fofa_key,
            "qbase64": qbase64,
            "fields": ",".join(FOFA_FIELDS),
            "size": page_size,
            "page": page,
            "full": "true",
            "r_type": "json",
        }
        url = f"{FOFA_SEARCH_ALL_API_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"User-Agent": "openclaw-probe/1.0"})
        data = fetch_fofa_page(opener, request, args.fofa_timeout, args.fofa_retries)
        if data.get("error"):
            raise RuntimeError(f"FOFA API error: {str(data.get('errmsg') or data)}")

        results = data.get("results") or []
        if not results:
            log(f"FOFA search/all stopped early at page={page} with empty results")
            break

        total_written += write_fofa_results(writer, results[:remaining])
        if len(results) < page_size:
            log(f"FOFA search/all returned a short page at page={page}, stopping early")
            break
        if args.sleep > 0 and page < total_pages:
            time.sleep(args.sleep)

    return total_written


def build_cache_snapshot_path(args: argparse.Namespace, cache_path: Path) -> Path:
    query_slug = re.sub(r"[^a-z0-9]+", "_", (args.query or "openclaw").lower()).strip("_") or "openclaw"
    date_prefix = dt.date.today().strftime("%Y%m%d")
    filename = f"{date_prefix}_{query_slug}_{args.max_records}.csv"
    return cache_path.parent / "history" / filename


def copy_into_run_dir(source_path: Path, out_path: Path) -> Path:
    if source_path.resolve() == out_path.resolve():
        return source_path
    ensure_parent(out_path)
    shutil.copy2(source_path, out_path)
    return out_path


def load_from_cache(cache_path: Path, out_path: Path) -> Path:
    if not cache_path.exists():
        raise FileNotFoundError(f"FOFA cache not found: {cache_path}")
    log(f"using local FOFA cache: {cache_path}")
    return copy_into_run_dir(cache_path, out_path)


def save_cache_copy(source_path: Path, cache_path: Path, args: argparse.Namespace) -> None:
    ensure_parent(cache_path)
    shutil.copy2(source_path, cache_path)
    snapshot_path = build_cache_snapshot_path(args, cache_path)
    ensure_parent(snapshot_path)
    shutil.copy2(source_path, snapshot_path)
    log(f"updated FOFA cache: {cache_path}")
    log(f"saved FOFA cache snapshot: {snapshot_path}")


def fetch_fofa_csv(args: argparse.Namespace, out_path: Path) -> Path:
    if args.fofa_input:
        fofa_input = Path(args.fofa_input)
        if not fofa_input.exists():
            raise FileNotFoundError(f"FOFA input not found: {fofa_input}")
        return copy_into_run_dir(fofa_input, out_path)

    cache_path = Path(args.fofa_cache) if getattr(args, "fofa_cache", "") else (FOFA_CACHE_DIR / "openclaw_latest.csv")
    if getattr(args, "fofa_cache_first", False) and cache_path.exists():
        return load_from_cache(cache_path, out_path)
    if getattr(args, "fofa_cache_only", False):
        return load_from_cache(cache_path, out_path)

    if not args.fofa_key:
        raise RuntimeError("Missing FOFA key. Pass --fofa-key or use --fofa-input.")

    qbase64 = base64.b64encode(args.query.encode("utf-8")).decode("ascii")
    ensure_parent(out_path)

    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FOFA_FIELDS)
        opener = build_fofa_opener(args)

        total_written = fetch_fofa_all_mode(args, writer, opener, qbase64)
        log(f"FOFA search/all fetched rows: {total_written}")

    save_cache_copy(out_path, cache_path, args)
    return out_path


def load_fofa_rows(fofa_csv: Path) -> list[dict[str, str]]:
    _, rows = read_csv_rows(fofa_csv)
    return rows
