#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
DEMO_DIR="$ROOT_DIR/tools/openclaw-probe/demo"
UPDATER="$ROOT_DIR/tools/openclaw-probe/fofa_incremental_updater.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${OPENCLAW_PROBE_DEMO_HOST:-127.0.0.1}"
PORT="${OPENCLAW_PROBE_DEMO_PORT:-}"
WORK_DIR="${OPENCLAW_PROBE_DEMO_DIR:-$(mktemp -d /tmp/openclaw-probe-demo.XXXXXX)}"
SERVER_LOG="$WORK_DIR/demo-server.log"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

mkdir -p "$WORK_DIR"

if [[ -z "$PORT" ]]; then
  PORT="$("$PYTHON_BIN" - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
fi

"$PYTHON_BIN" "$DEMO_DIR/demo_openclaw_server.py" --host "$HOST" --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
for _ in {1..20}; do
  if grep -q "demo openclaw server listening" "$SERVER_LOG" 2>/dev/null; then
    break
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "demo server failed to start" >&2
    cat "$SERVER_LOG" >&2
    exit 1
  fi
  sleep 0.2
done

if ! grep -q "demo openclaw server listening" "$SERVER_LOG" 2>/dev/null; then
  echo "demo server failed to start" >&2
  cat "$SERVER_LOG" >&2
  exit 1
fi

"$PYTHON_BIN" - "$WORK_DIR" "$HOST" "$PORT" <<'PY'
import csv
import json
import sqlite3
import sys
from pathlib import Path

work_dir = Path(sys.argv[1])
host = sys.argv[2]
port = sys.argv[3]

deduped_fields = [
    "ip_port",
    "assistant_name",
    "country",
    "auth_required",
    "is_active",
    "has_leaked_creds",
    "asn",
    "asn_name",
    "org",
    "first_seen",
    "last_seen",
    "asi_has_breach",
    "asi_has_threat_actor",
    "asi_threat_actors",
    "asi_cves",
    "asi_enriched_at",
    "asi_domains",
]
alive_fields = [
    "ip_port",
    "any_200",
    "config_ok",
    "root",
    "health",
    "healthz",
    "ready",
    "readyz",
    "avatar_main_meta_1",
    "__openclaw_control-ui-config.json",
]
cn_fields = deduped_fields + ["physical_country", "region", "city"]
fofa_fields = [
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

with (work_dir / "openclaw_instances_deduped.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=deduped_fields)
    writer.writeheader()

with (work_dir / "endpoint_alive.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=alive_fields)
    writer.writeheader()

(work_dir / "endpoint_alive_configs.json").write_text("{}", encoding="utf-8")

with (work_dir / "openclaw_instances_cn.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=cn_fields)
    writer.writeheader()

with (work_dir / "fofa.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fofa_fields)
    writer.writeheader()
    writer.writerow(
        {
            "ip": host,
            "port": port,
            "country_name": "China",
            "region": "Beijing",
            "city": "Beijing",
            "longitude": "",
            "latitude": "",
            "asn": "64500",
            "org": "Demo Org",
            "host": "demo.local",
            "domain": "demo.local",
            "os": "",
            "server": "",
            "title": "",
            "jarm": "",
            "link": f"http://{host}:{port}",
        }
    )

sqlite3.connect(work_dir / "exposure.db").close()
PY

"$PYTHON_BIN" "$UPDATER" \
  --fofa-input "$WORK_DIR/fofa.csv" \
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
instances = cur.execute(
    "SELECT ip_port, first_seen_at, last_active_at, is_active, source, country_name, region, city, server_version "
    "FROM probe_instances ORDER BY ip_port"
).fetchall()
snapshots = cur.execute(
    "SELECT snapshot_date, ip_port, is_active, server_version FROM probe_daily_snapshots ORDER BY ip_port"
).fetchall()
conn.close()

with (work_dir / "openclaw_instances_deduped.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    deduped_rows = list(csv.DictReader(handle))

with (work_dir / "endpoint_alive.csv").open("r", encoding="utf-8-sig", newline="") as handle:
    alive_rows = list(csv.DictReader(handle))

config_map = json.loads((work_dir / "endpoint_alive_configs.json").read_text(encoding="utf-8"))

print("Demo work dir:", work_dir)
print("probe_instances rows:", len(instances))
for row in instances:
    print("  instance:", row)
print("probe_daily_snapshots rows:", len(snapshots))
for row in snapshots:
    print("  snapshot:", row)
print("deduped csv rows:", len(deduped_rows))
print("alive csv rows:", len(alive_rows))
print("config payload keys:", sorted(config_map.keys()))
print("run artifacts:", sorted(p.name for p in (work_dir / "run").iterdir()))
PY
