#!/usr/bin/env python3
"""Compatibility wrapper. Use enrich_cn_locations.py instead."""

from enrich_cn_locations import main


if __name__ == "__main__":
    raise SystemExit(main())
