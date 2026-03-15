#!/usr/bin/env python3
"""Merge OpenClaw probe CSVs and dedupe by ip_port."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge one or more OpenClaw probe CSV files and dedupe by first column ip_port."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input CSV files.")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output deduped CSV path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    rows_by_key: dict[str, dict[str, str]] = {}
    header: list[str] | None = None

    for input_path in args.inputs:
        if not input_path.exists():
            raise FileNotFoundError(f"Input not found: {input_path}")

        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            current_header = reader.fieldnames or []
            if not current_header:
                continue

            if header is None:
                header = current_header

            first_column = current_header[0]
            for row in reader:
                key = (row.get(first_column) or "").strip()
                if not key:
                    continue
                rows_by_key[key] = row

    if not header:
        raise ValueError("No valid CSV header found in input files.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for key in sorted(rows_by_key):
            writer.writerow(rows_by_key[key])

    print(f"merged rows: {len(rows_by_key)}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
