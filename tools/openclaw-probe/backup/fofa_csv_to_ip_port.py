#!/usr/bin/env python3
"""Convert FOFA CSV to ip_port-first format.

Behavior:
- Merge column1(ip) + column2(port) into column1 as ip:port
- Remove the original column2(port)
- Rename column1 header to ip_port
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert FOFA CSV by merging first two columns into ip_port and dropping the port column."
        )
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="Input CSV path, e.g. fofa_openclaw_20260313_213720.csv",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV path. Default: <input_stem>_ip_port.csv",
    )
    return parser.parse_args()


def build_ip_port(ip: str, port: str) -> str:
    ip = (ip or "").strip()
    port = (port or "").strip()
    if not ip:
        return ""
    if not port:
        return ip
    return f"{ip}:{port}"


def transform(input_csv: Path, output_csv: Path) -> tuple[int, int]:
    rows_in = 0
    rows_out = 0

    with input_csv.open("r", encoding="utf-8-sig", newline="") as src, output_csv.open(
        "w", encoding="utf-8-sig", newline=""
    ) as dst:
        reader = csv.reader(src)
        writer = csv.writer(dst)

        header = next(reader, None)
        if header is None:
            raise ValueError("Input CSV is empty.")
        if len(header) < 2:
            raise ValueError("Input CSV must have at least 2 columns (ip, port).")

        new_header = list(header)
        new_header[0] = "ip_port"
        del new_header[1]
        writer.writerow(new_header)

        for row in reader:
            rows_in += 1
            if not row:
                continue

            # Ensure row has at least two cells to safely merge ip and port.
            if len(row) < 2:
                row = row + [""]

            new_row = list(row)
            new_row[0] = build_ip_port(new_row[0], new_row[1])
            del new_row[1]
            writer.writerow(new_row)
            rows_out += 1

    return rows_in, rows_out


def main() -> int:
    args = parse_args()
    input_csv = args.input_csv
    if not input_csv.exists():
        raise FileNotFoundError(f"Input not found: {input_csv}")

    output_csv = args.output or input_csv.with_name(f"{input_csv.stem}_ip_port.csv")
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows_in, rows_out = transform(input_csv=input_csv, output_csv=output_csv)
    print(f"[DONE] Input rows: {rows_in}")
    print(f"[DONE] Output rows: {rows_out}")
    print(f"[DONE] Output file: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
