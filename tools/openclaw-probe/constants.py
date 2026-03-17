from __future__ import annotations

import datetime as dt
import os
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPOSURE_INPUT_DIR = DATA_DIR / "explosure"
EXPOSURE_DB_PATH = DATA_DIR / "exposure.db"
DEDUPED_CSV_PATH = EXPOSURE_INPUT_DIR / "openclaw_instances_deduped.csv"
ALIVE_CSV_PATH = EXPOSURE_INPUT_DIR / "endpoint_alive.csv"
CONFIGS_JSON_PATH = EXPOSURE_INPUT_DIR / "endpoint_alive_configs.json"
CN_CSV_PATH = EXPOSURE_INPUT_DIR / "openclaw_instances_cn.csv"
RUNS_DIR = EXPOSURE_INPUT_DIR / "runs"
FOFA_CACHE_DIR = EXPOSURE_INPUT_DIR / "fofa_cache"
FOFA_API_BASE_URL = os.getenv("FOFA_API_BASE_URL", "https://fofoapi.com")
FOFA_SEARCH_ALL_API_URL = f"{FOFA_API_BASE_URL}/api/v1/search/all"
FOFA_SEARCH_NEXT_API_URL = f"{FOFA_API_BASE_URL}/api/v1/search/next"
TODAY = dt.date.today().isoformat()

FOFA_FIELDS = [
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

DEDUPED_FIELDS = [
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

ALIVE_FIELDS = [
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

CN_FIELDS = DEDUPED_FIELDS + ["physical_country", "region", "city"]
