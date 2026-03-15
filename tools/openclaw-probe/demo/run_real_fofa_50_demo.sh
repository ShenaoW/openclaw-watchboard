#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
PROBE_DIR="$ROOT_DIR/tools/openclaw-probe"
UPDATER="$PROBE_DIR/fofa_incremental_updater.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WORK_DIR="${OPENCLAW_PROBE_DEMO_DIR:-$(mktemp -d /tmp/openclaw-probe-real-fofa-demo.XXXXXX)}"
FOFA_QUERY="${OPENCLAW_PROBE_QUERY:-app=\"openclaw\"}"

if [[ -z "${FOFA_KEY:-}" ]]; then
  echo "FOFA_KEY is required" >&2
  exit 1
fi

mkdir -p "$WORK_DIR"

"$PYTHON_BIN" - "$ROOT_DIR" "$WORK_DIR" <<'PY'
import csv
import json
import sqlite3
import sys
from pathlib import Path

root_dir = Path(sys.argv[1])
work_dir = Path(sys.argv[2])
source_dir = root_dir / "data" / "explosure"

def copy_first_n_csv(src: Path, dst: Path, limit: int) -> list[dict[str, str]]:
    with src.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rows.append(row)
        fieldnames = reader.fieldnames or []
    with dst.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows

deduped_rows = copy_first_n_csv(
    source_dir / "openclaw_instances_deduped.csv",
    work_dir / "openclaw_instances_deduped.csv",
    50,
)
seed_keys = [(row.get("ip_port") or "").strip() for row in deduped_rows if (row.get("ip_port") or "").strip()]
seed_key_set = set(seed_keys)

with (source_dir / "endpoint_alive.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fieldnames = reader.fieldnames or []
    alive_rows = []
    for row in reader:
        if (row.get("ip_port") or "").strip() in seed_key_set:
            alive_rows.append(row)
with (work_dir / "endpoint_alive.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(alive_rows)

config_src = source_dir / "endpoint_alive_configs.json"
config_data = json.loads(config_src.read_text(encoding="utf-8")) if config_src.exists() else {}
config_subset = {key: value for key, value in config_data.items() if key in seed_key_set}
(work_dir / "endpoint_alive_configs.json").write_text(
    json.dumps(config_subset, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

with (source_dir / "openclaw_instances_cn.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    fieldnames = reader.fieldnames or []
    cn_rows = []
    for row in reader:
        if (row.get("ip_port") or "").strip() in seed_key_set:
            cn_rows.append(row)
with (work_dir / "openclaw_instances_cn.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cn_rows)

sqlite3.connect(work_dir / "exposure.db").close()

print("seed deduped rows:", len(deduped_rows))
print("seed alive rows:", len(alive_rows))
print("seed config rows:", len(config_subset))
print("seed cn rows:", len(cn_rows))
PY

FOFA_KEY="$FOFA_KEY" "$PYTHON_BIN" "$UPDATER" \
  --fofa-key "$FOFA_KEY" \
  --query "$FOFA_QUERY" \
  --max-records 50 \
  --page-size 50 \
  --fofa-no-proxy \
  --db-path "$WORK_DIR/exposure.db" \
  --deduped-csv "$WORK_DIR/openclaw_instances_deduped.csv" \
  --alive-csv "$WORK_DIR/endpoint_alive.csv" \
  --configs-json "$WORK_DIR/endpoint_alive_configs.json" \
  --cn-csv "$WORK_DIR/openclaw_instances_cn.csv" \
  --run-dir "$WORK_DIR/run" \
  --write-live

"$PYTHON_BIN" - "$WORK_DIR" <<'PY'
import csv
import json
import sqlite3
import sys
from pathlib import Path

work_dir = Path(sys.argv[1])
conn = sqlite3.connect(work_dir / "exposure.db")
cur = conn.cursor()

probe_instances = cur.execute("SELECT COUNT(*) FROM probe_instances").fetchone()[0]
active_instances = cur.execute("SELECT COUNT(*) FROM probe_instances WHERE is_active = 1").fetchone()[0]
fofa_seeded = cur.execute("SELECT COUNT(*) FROM probe_instances WHERE source = 'fofa'").fetchone()[0]
legacy_seeded = cur.execute("SELECT COUNT(*) FROM probe_instances WHERE source = 'legacy'").fetchone()[0]
snapshots = cur.execute("SELECT COUNT(*) FROM probe_daily_snapshots").fetchone()[0]
versioned = cur.execute("SELECT COUNT(*) FROM probe_instances WHERE server_version IS NOT NULL AND server_version != ''").fetchone()[0]
sample_rows = cur.execute(
    "SELECT ip_port, source, is_active, country_name, region, city, server_version FROM probe_instances ORDER BY ip_port LIMIT 10"
).fetchall()
conn.close()

with (work_dir / "run" / "fofa_openclaw_raw.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    fofa_rows = list(csv.DictReader(handle))

with (work_dir / "run" / "fofa_new_ip_port.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    new_rows = list(csv.DictReader(handle))

configs = json.loads((work_dir / "endpoint_alive_configs.json").read_text(encoding="utf-8"))

print("Demo work dir:", work_dir)
print("fofa fetched rows:", len(fofa_rows))
print("new candidate rows:", len(new_rows))
print("probe_instances rows:", probe_instances)
print("active probe_instances rows:", active_instances)
print("legacy rows:", legacy_seeded)
print("fofa rows:", fofa_seeded)
print("versioned rows:", versioned)
print("probe_daily_snapshots rows:", snapshots)
print("config payload rows:", len(configs))
print("sample rows:")
for row in sample_rows:
    print("  ", row)
print("run artifacts:", sorted(p.name for p in (work_dir / "run").iterdir()))
PY
