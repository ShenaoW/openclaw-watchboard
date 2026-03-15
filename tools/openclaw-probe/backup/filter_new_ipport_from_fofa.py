#!/usr/bin/env python3
"""Filter IP:port values that exist in a FOFA CSV but not in a deduped CSV.

Default behavior writes full original FOFA rows for new-only keys.
For compatibility with old workflows, an optional single-column ip_port output
can also be generated.

This script is resilient to malformed CSV rows (for example, rows with unescaped commas)
by only reading the first field in each data row as the IP:port key.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def iter_first_column(path: Path, encoding: str = "utf-8-sig"):
    """Yield first-column values from a text file line by line, skipping the header."""
    with path.open("r", encoding=encoding, errors="replace", newline="") as f:
        for i, line in enumerate(f):
            line = line.rstrip("\r\n")
            if not line:
                continue
            if i == 0:
                # Skip header
                continue
            first = line.split(",", 1)[0].strip()
            if first:
                yield first


def load_set_from_first_column(path: Path) -> set[str]:
    return set(iter_first_column(path))


def write_single_column_csv(path: Path, values: list[str], header: str = "ip_port") -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([header])
        for v in values:
            writer.writerow([v])


def write_full_rows_from_fofa(
    fofa_path: Path,
    output_path: Path,
    keep_keys: set[str],
    encoding: str = "utf-8-sig",
) -> int:
    """Write FOFA header and original raw rows whose first column is in keep_keys.

    To keep robustness with malformed CSV rows, this function works line-by-line
    and treats the first comma-separated token as the key.
    """
    written = 0
    seen: set[str] = set()

    with fofa_path.open("r", encoding=encoding, errors="replace", newline="") as src, output_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as dst:
        for i, line in enumerate(src):
            if i == 0:
                # Preserve original header line.
                dst.write(line)
                continue

            line = line.rstrip("\r\n")
            if not line:
                continue

            key = line.split(",", 1)[0].strip()
            if key and key in keep_keys and key not in seen:
                dst.write(line + "\n")
                seen.add(key)
                written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find IP:port values in FOFA file but missing in deduped file."
    )
    parser.add_argument(
        "--fofa",
        type=Path,
        required=True,
        help="Path to FOFA CSV file (first column must be IP:port).",
    )
    parser.add_argument(
        "--deduped",
        type=Path,
        required=True,
        help="Path to deduped CSV file (first column should be ip_port).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output CSV path for full original FOFA rows (new-only keys).",
    )
    parser.add_argument(
        "--ip-only-out",
        type=Path,
        help="Optional output CSV path for ip_port single-column format.",
    )
    args = parser.parse_args()

    if not args.fofa.exists():
        raise FileNotFoundError(f"FOFA file not found: {args.fofa}")
    if not args.deduped.exists():
        raise FileNotFoundError(f"Deduped file not found: {args.deduped}")

    fofa_values = load_set_from_first_column(args.fofa)
    deduped_values = load_set_from_first_column(args.deduped)

    new_only = sorted(fofa_values - deduped_values)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    full_rows_written = write_full_rows_from_fofa(
        fofa_path=args.fofa,
        output_path=args.out,
        keep_keys=set(new_only),
    )

    if args.ip_only_out:
        args.ip_only_out.parent.mkdir(parents=True, exist_ok=True)
        write_single_column_csv(args.ip_only_out, new_only, header="ip_port")

    print(f"fofa count: {len(fofa_values)}")
    print(f"deduped count: {len(deduped_values)}")
    print(f"new only count: {len(new_only)}")
    print(f"full rows written: {full_rows_written}")
    print(f"full rows file: {args.out}")
    if args.ip_only_out:
        print(f"ip-only file: {args.ip_only_out}")


if __name__ == "__main__":
    main()
