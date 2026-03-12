#!/usr/bin/env python3
"""Fetch paginated skill listings from Gen Digital and store locally."""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "skills"
BASE_URL = "https://ai.gendigital.com/api/skills/{classification}"


def fetch_json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "openclaw-watchboard/1.0 (+https://clawsec.com.cn)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", default="safe", choices=["safe", "suspicious", "malicious"])
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / f"gendigital_{args.classification}.json"

    offset = 0
    all_skills = []
    total = None

    while True:
        query = urllib.parse.urlencode({"offset": offset, "limit": args.limit})
        payload = fetch_json(f"{BASE_URL.format(classification=args.classification)}?{query}")
        skills = payload.get("skills", [])
        all_skills.extend(skills)

        if total is None:
            total = payload.get("total")

        print(f"✅ GenDigital {args.classification}: offset={offset}, count={len(skills)}")

        if not payload.get("hasMore") or not skills:
            break

        offset += len(skills)
        time.sleep(0.2)

    output = {
        "source": "gendigital",
        "classification": args.classification,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": total if total is not None else len(all_skills),
        "count": len(all_skills),
        "skills": all_skills,
    }

    output_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🎉 GenDigital 数据已保存: {output_file}")
    print(f"   共抓取 {len(all_skills)} 条")


if __name__ == "__main__":
    main()
