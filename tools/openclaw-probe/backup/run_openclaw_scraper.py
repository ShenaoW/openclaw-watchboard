#!/usr/bin/env python3
"""Non-interactive entrypoint for OpenClaw scraper."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from openclaw_scraper import OpenClawScraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenClaw scraper without interactive prompts.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum pages to scrape. 0 means all pages.")
    parser.add_argument("--start-page", type=int, default=1, help="Start page number.")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent worker count.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory for generated CSV/JSON files.",
    )
    parser.add_argument(
        "--base-url",
        default="https://openclaw.allegro.earth",
        help="Base URL for the OpenClaw exposure site.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    original_cwd = Path.cwd()
    os.chdir(args.output_dir)
    try:
        scraper = OpenClawScraper(base_url=args.base_url, max_workers=args.workers)
        scraper.scrape_all(
            max_pages=None if args.max_pages == 0 else args.max_pages,
            start_page=args.start_page,
        )
    finally:
        os.chdir(original_cwd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
