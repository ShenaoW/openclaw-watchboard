#!/usr/bin/env python3
"""Fetch paginated audit data from skills.sh and store locally."""

import json
import time
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "skills"
OUTPUT_FILE = DATA_DIR / "skills_sh_audits.json"
BASE_URL = "https://skills.sh/api/audits/{page}"


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
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    page = 0
    all_skills = []
    total = None

    while True:
      payload = fetch_json(BASE_URL.format(page=page))
      skills = payload.get("skills", [])
      all_skills.extend(skills)

      if total is None:
          total = payload.get("total")

      print(f"✅ skills.sh page {page}: {len(skills)} skills")

      if not payload.get("hasMore") or not skills:
          break

      page += 1
      time.sleep(0.2)

    output = {
        "source": "skills.sh",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": total if total is not None else len(all_skills),
        "count": len(all_skills),
        "skills": all_skills,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🎉 skills.sh 数据已保存: {OUTPUT_FILE}")
    print(f"   共抓取 {len(all_skills)} 条")


if __name__ == "__main__":
    main()
