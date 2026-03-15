from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path

from common import build_ip_port, log
from constants import ROOT_DIR, RUNS_DIR
from exporters import export_alive_files, export_cn_csv, export_deduped_csv, save_run_artifacts
from fofa import fetch_fofa_csv, load_fofa_rows
from prober import probe_many
from repository import (
    bootstrap_instances,
    ensure_probe_tables,
    insert_new_instances,
    load_probe_instances,
    open_db,
    update_runtime_state,
    upsert_daily_snapshots,
)
from status import RunStatusTracker


def unique_fofa_rows_by_ip_port(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        ip_port = build_ip_port(row)
        if not ip_port or ip_port in seen:
            continue
        seen.add(ip_port)
        unique_rows.append(row)
    return unique_rows


def run_pipeline(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir) if args.run_dir else (RUNS_DIR / dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    tracker = RunStatusTracker(run_dir)

    try:
        tracker.set_stage("fetch_fofa", {"query": args.query, "max_records": args.max_records})
        fofa_csv = fetch_fofa_csv(args, run_dir / "fofa_openclaw_raw.csv")
        tracker.set_metric("fofa_source_path", str(fofa_csv))
        fofa_rows = load_fofa_rows(fofa_csv)
        unique_fofa_rows = unique_fofa_rows_by_ip_port(fofa_rows)
        tracker.set_metric("fofa_fetched_rows", len(fofa_rows))
        tracker.set_metric("fofa_unique_rows", len(unique_fofa_rows))

        if getattr(args, "fofa_fetch_only", False):
            tracker.set_stage("save_run_artifacts")
            save_run_artifacts(run_dir, unique_fofa_rows, [])
            tracker.complete()
            return 0

        conn = open_db(Path(args.db_path))
        tracker.set_stage("prepare_database", {"db_path": str(args.db_path)})
    except Exception as error:
        tracker.fail(error)
        raise

    try:
        ensure_probe_tables(conn)
        inserted = bootstrap_instances(
            conn,
            Path(args.deduped_csv),
            Path(args.alive_csv),
            Path(args.configs_json),
            Path(args.cn_csv),
        )
        tracker.set_metric("bootstrapped_legacy_rows", inserted)
        if inserted > 0:
            log(f"bootstrapped {inserted} legacy instances into probe_instances")

        existing_keys = {row["ip_port"] for row in load_probe_instances(conn)}
        new_candidate_rows = [row for row in unique_fofa_rows if build_ip_port(row) and build_ip_port(row) not in existing_keys]
        new_candidate_keys = [build_ip_port(row) for row in new_candidate_rows]
        tracker.set_stage("probe_new_candidates", {"candidate_count": len(new_candidate_keys)})
        tracker.set_metric("new_candidate_rows", len(new_candidate_keys))
        log(f"new candidate count: {len(new_candidate_keys)}")

        new_probe_results = probe_many(new_candidate_keys, args.probe_concurrency, args.probe_timeout)
        confirmed = insert_new_instances(conn, new_candidate_rows, new_probe_results)
        tracker.set_metric("confirmed_new_instances", confirmed)
        log(f"confirmed new instances inserted: {confirmed}")

        all_instance_keys = [row["ip_port"] for row in load_probe_instances(conn)]
        tracker.set_stage("refresh_runtime_state", {"instance_count": len(all_instance_keys)})
        daily_probe_results = probe_many(all_instance_keys, args.probe_concurrency, args.probe_timeout)
        update_runtime_state(conn, daily_probe_results)
        snapshot_count = upsert_daily_snapshots(conn)
        tracker.set_metric("snapshot_rows", snapshot_count)
        log(f"daily snapshots upserted: {snapshot_count}")

        if args.write_live:
            tracker.set_stage("export_compatibility_files")
            deduped_total = export_deduped_csv(conn, Path(args.deduped_csv))
            alive_total, config_total = export_alive_files(
                conn,
                daily_probe_results,
                Path(args.alive_csv),
                Path(args.configs_json),
            )
            cn_total = export_cn_csv(conn, Path(args.cn_csv))
            tracker.set_metric("deduped_csv_rows", deduped_total)
            tracker.set_metric("alive_csv_rows", alive_total)
            tracker.set_metric("config_payload_rows", config_total)
            tracker.set_metric("cn_csv_rows", cn_total)
            log(f"deduped csv rows: {deduped_total}")
            log(f"alive csv rows: {alive_total}")
            log(f"config payload rows: {config_total}")
            log(f"cn csv rows: {cn_total}")

        tracker.set_stage("save_run_artifacts")
        save_run_artifacts(run_dir, unique_fofa_rows, new_candidate_keys)

        if args.refresh_db:
            tracker.set_stage("refresh_exposure_db")
            subprocess.run(["npm", "run", "refresh:exposure-db"], cwd=ROOT_DIR, check=True)
            tracker.set_metric("refresh_exposure_db", "ok")
    except Exception as error:
        tracker.fail(error)
        raise
    finally:
        conn.close()

    tracker.complete()
    return 0
