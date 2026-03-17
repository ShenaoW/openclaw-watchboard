#!/usr/bin/env python3
"""Refresh website vulnerability data from GitHub advisories into risks.db."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
GENERATOR_SCRIPT = BASE_DIR / "tools" / "openclaw-vuln-sync" / "generate_openclaw_vulnerabilities.py"
SETUP_SCRIPT = BASE_DIR / "scripts" / "setup_database.py"
ANALYZE_SCRIPT = BASE_DIR / "scripts" / "analyze_vulnerabilities.py"
IMPORT_SCRIPT = BASE_DIR / "scripts" / "import_vulnerabilities_to_db.py"
DEFAULT_RAW_CSV_PATH = BASE_DIR / "data" / "vuls" / "openclaw_vuls.csv"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--github-token",
        default=os.getenv("OPENCLAW_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN"),
        help="GitHub token used to pull security advisories",
    )
    parser.add_argument(
        "--llm-api-key",
        default=os.getenv("PACKY_API_KEY") or os.getenv("OPENCLAW_LLM_API_KEY"),
        help="Third-party OpenAI-compatible API key used to classify vulnerabilities",
    )
    parser.add_argument(
        "--llm-base-url",
        default=os.getenv("OPENCLAW_LLM_BASE_URL") or "https://www.packyapi.com/v1",
        help="OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("OPENCLAW_LLM_MODEL") or "gpt-5.4",
        help="Model used for stage classification",
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="Skip LLM stage classification and only refresh raw vulnerability CSV",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Force the generator to rebuild all raw vulnerability rows",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_RAW_CSV_PATH),
        help="Raw vulnerability CSV path",
    )
    return parser.parse_args()


def run_step(description: str, command: list[str]) -> None:
    print(f"\n{'=' * 60}")
    print(f"🚀 {description}")
    print(f"{'=' * 60}")
    start_time = time.time()

    result = subprocess.run(command, cwd=BASE_DIR, text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    duration = time.time() - start_time
    print(f"✅ {description} 完成 (耗时: {duration:.2f}秒)")


def main() -> int:
    load_env_file(ENV_FILE)
    args = parse_args()
    if not args.github_token:
        print("❌ 缺少 GitHub Token，请通过 --github-token 或 OPENCLAW_GITHUB_TOKEN 提供。", file=sys.stderr)
        return 1
    if not args.skip_classify and not args.llm_api_key:
        print(
            "❌ 缺少 LLM API Key，请通过 --llm-api-key 或 PACKY_API_KEY 提供，"
            "或者使用 --skip-classify。",
            file=sys.stderr,
        )
        return 1

    generator_command = [
        sys.executable,
        str(GENERATOR_SCRIPT),
        "--github-token",
        args.github_token,
        "--output",
        args.output,
        "--llm-base-url",
        args.llm_base_url,
        "--llm-model",
        args.llm_model,
    ]
    if args.llm_api_key:
        generator_command.extend(["--llm-api-key", args.llm_api_key])
    if args.skip_classify:
        generator_command.append("--skip-classify")
    if args.full_refresh:
        generator_command.append("--full-refresh")

    print("🎯 OpenClaw 漏洞数据自动更新开始...")
    print("📅 开始时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    run_step("数据库初始化", [sys.executable, str(SETUP_SCRIPT)])
    run_step("同步 GitHub 漏洞数据", generator_command)
    run_step("漏洞标注分析", [sys.executable, str(ANALYZE_SCRIPT)])
    run_step("漏洞数据入库", [sys.executable, str(IMPORT_SCRIPT)])

    print(f"\n{'=' * 60}")
    print("🎉 网站漏洞数据已更新完成")
    print(f"📄 原始漏洞 CSV: {Path(args.output).expanduser().resolve()}")
    print(f"🗄️ 风险数据库: {BASE_DIR / 'data' / 'risks.db'}")
    print("💡 同步到线上可继续执行: npm run sync:databases")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
