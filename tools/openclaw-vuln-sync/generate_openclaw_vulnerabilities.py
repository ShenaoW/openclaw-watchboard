#!/usr/bin/env python3
"""Fetch OpenClaw GitHub security advisories and export them to CSV."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from openai import OpenAI
from tqdm import tqdm

API_VERSION = "2022-11-28"
USER_AGENT = "openclaw-vulnerability-export/4.0"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
CONCURRENCY = 4
MAX_RETRIES = 4
RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}
DEFAULT_LLM_BASE_URL = "https://www.packyapi.com/v1"
DEFAULT_LLM_MODEL = "gpt-5.3-codex-medium"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "vuls" / "openclaw_vuls.csv"
DEFAULT_ANNOTATED_PATH = REPO_ROOT / "data" / "vuls" / "openclaw_vuls_annotated.csv"
CSV_COLUMNS = [
    "No.",
    "Vulnerability Title",
    "Stage",
    "Reason",
    "Vulnerability ID",
    "Github Severity",
    "Affected Versions",
    "CVE",
    "CWE",
    "Vulnerability Link",
]
VALID_STAGES = {
    "Input Ingress Stage",
    "Gateway Authorization & Routing Stage",
    "Execution Stage",
    "Resource Access Stage",
    "Persistence & Output Presentation Stage",
}
PHASE_DESC = """
你需要判断一个安全漏洞主要发生在哪一个阶段，只能从下面五个阶段中选择一个：

1. Input Ingress Stage
含义：外部输入进入系统并被解析、路由、规范化的阶段。
典型现象：参数注入、路径解析错误、URL/请求体/文件内容解析问题、编码绕过、输入校验缺失。

2. Gateway Authorization & Routing Stage
含义：系统对“你是谁、你能做什么”进行判定的阶段。
典型现象：身份校验缺失、越权、权限判断错误、owner/admin-only 检查缺失、认证绕过。

3. Execution Stage
含义：系统开始执行命令、脚本、工具调用、模板渲染、解释器执行的阶段。
典型现象：RCE、命令注入、代码执行、sandbox escape、危险函数执行。

4. Resource Access Stage
含义：系统访问文件、数据库、网络、设备、进程、内部服务等资源的阶段。
典型现象：任意文件读写、路径穿越、SSRF、越界访问、跨租户访问、错误资源绑定。

5. Persistence & Output Presentation Stage
含义：数据被保存、展示、返回、渲染、下发给用户或其他系统的阶段。
典型现象：存储型问题、敏感信息泄露、输出展示不当、日志/页面/API 返回造成暴露。

判定规则：
- 选择“漏洞真正发生的主阶段”，不是修复阶段。
- 如果一个漏洞跨多个阶段，选最核心、最直接导致安全后果的那个阶段。
- 只输出一个阶段名，必须与上面五个名称完全一致。
""".strip()
SYSTEM_PROMPT = (
    "你是安全漏洞分类助手。"
    "请根据漏洞标题、CWE、严重程度、受影响版本等信息，判断该漏洞主要属于哪个阶段。"
    '输出必须是 JSON，格式为：{"stage":"五选一阶段名","reason":"一句简短中文理由"}。'
)


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def unique_join(values: list[str], sep: str) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return sep.join(result)


def first_cve(advisory: dict) -> str:
    if text(advisory.get("cve_id")):
        return text(advisory.get("cve_id"))
    for identifier in advisory.get("identifiers") or []:
        if text(identifier.get("type")).upper() == "CVE" and text(identifier.get("value")):
            return text(identifier.get("value"))
    return ""


def openclaw_vulnerabilities(advisory: dict, repo_name: str) -> list[dict]:
    first: dict | None = None
    for item in advisory.get("vulnerabilities") or []:
        if not isinstance(item, dict):
            continue
        if first is None:
            first = item
        package_name = text((item.get("package") or {}).get("name")).lower()
        if repo_name.lower() in package_name:
            return [item]
    return [first] if first else []


def retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    reset_at = response.headers.get("X-RateLimit-Reset")
    if reset_at and response.status_code in {403, 429}:
        try:
            return max(float(reset_at) - time.time(), 0) + 1
        except ValueError:
            pass
    return min(2 ** (attempt - 1), 30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="openclaw", help="GitHub repository owner")
    parser.add_argument("--repo", default="openclaw", help="GitHub repository name")
    parser.add_argument(
        "--github-token",
        default=os.getenv("OPENCLAW_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN"),
        help="GitHub token. Supports OPENCLAW_GITHUB_TOKEN or GITHUB_TOKEN.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output CSV path",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Re-fetch and reclassify all advisories instead of incrementally merging with the existing CSV",
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="Skip LLM stage classification and reuse existing Stage/Reason if available",
    )
    parser.add_argument(
        "--llm-api-key",
        default=os.getenv("PACKY_API_KEY") or os.getenv("OPENCLAW_LLM_API_KEY"),
        help="Third-party OpenAI-compatible API key. Supports PACKY_API_KEY or OPENCLAW_LLM_API_KEY.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=os.getenv("OPENCLAW_LLM_BASE_URL") or DEFAULT_LLM_BASE_URL,
        help="OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("OPENCLAW_LLM_MODEL") or DEFAULT_LLM_MODEL,
        help="Model used for stage classification",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.github_token:
        raise SystemExit(
            "Missing GitHub token. Provide --github-token or set OPENCLAW_GITHUB_TOKEN/GITHUB_TOKEN."
        )
    if not args.skip_classify and not args.llm_api_key:
        raise SystemExit(
            "Missing LLM API key. Provide --llm-api-key, set PACKY_API_KEY/OPENCLAW_LLM_API_KEY, "
            "or use --skip-classify."
        )


def api_headers(github_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": API_VERSION,
    }


def classifier(args: argparse.Namespace) -> OpenAI | None:
    if args.skip_classify:
        return None
    return OpenAI(api_key=args.llm_api_key, base_url=args.llm_base_url)


async def request(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, object] | None = None,
) -> httpx.Response:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.get(url, params=params)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError):
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(min(2 ** (attempt - 1), 30))
            continue

        if response.is_success:
            return response
        if response.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_RETRIES:
            response.raise_for_status()
        await asyncio.sleep(retry_delay(response, attempt))

    raise RuntimeError(f"Failed to fetch {url}")


def load_existing_rows(output_path: Path) -> dict[str, dict[str, str]]:
    source_path = output_path if output_path.exists() else DEFAULT_ANNOTATED_PATH
    if not source_path.exists():
        return {}
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            row["Vulnerability ID"].upper(): {column: row.get(column, "") for column in CSV_COLUMNS}
            for row in csv.DictReader(handle)
            if row.get("Vulnerability ID")
        }


async def discover_ids(client: httpx.AsyncClient, list_url: str) -> list[str]:
    ghsa_ids: list[str] = []
    seen_ids: set[str] = set()
    next_url = list_url
    params: dict[str, object] | None = {
        "state": "published",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100,
    }

    progress = tqdm(desc="Discovering advisories", unit="page")
    try:
        page = 1
        while next_url:
            response = await request(client, next_url, params=params)
            payload = response.json()
            items = payload if isinstance(payload, list) else []
            progress.update(1)
            progress.set_postfix(page=page, total=len(seen_ids))

            if not items:
                break

            page_ids = [text(item.get("ghsa_id")).upper() for item in items if text(item.get("ghsa_id"))]
            for ghsa_id in page_ids:
                if ghsa_id in seen_ids:
                    continue
                seen_ids.add(ghsa_id)
                ghsa_ids.append(ghsa_id)

            next_url = response.links.get("next", {}).get("url", "")
            params = None
            page += 1
    finally:
        progress.close()

    return ghsa_ids


async def fetch_advisories(client: httpx.AsyncClient, detail_url_template: str, ghsa_ids: list[str]) -> list[dict]:
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def fetch_one(ghsa_id: str) -> dict:
        async with semaphore:
            payload = (await request(client, detail_url_template.format(ghsa_id=ghsa_id.lower()))).json()
            if not isinstance(payload, dict):
                raise TypeError(f"Unexpected payload for {ghsa_id}")
            return payload

    tasks = [fetch_one(ghsa_id) for ghsa_id in ghsa_ids]
    advisories: list[dict] = []
    for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching advisories"):
        advisories.append(await task)
    return advisories


def classify_row(client: OpenAI, model: str, row: dict[str, str]) -> tuple[str, str]:
    prompt = (
        f"{PHASE_DESC}\n\n"
        f"下面是一个漏洞条目：\n\n"
        f"标题: {row['Vulnerability Title']}\n"
        f"漏洞ID: {row['Vulnerability ID']}\n"
        f"严重程度: {row['Github Severity']}\n"
        f"受影响版本: {row['Affected Versions']}\n"
        f"CVE: {row['CVE']}\n"
        f"CWE: {row['CWE']}\n\n"
        "请严格输出 JSON，不要输出 Markdown，不要输出额外解释。"
    )
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    content = text(response.choices[0].message.content)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()

    payload = None
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", content):
        start = match.start()
        try:
            candidate, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "stage" in candidate:
            payload = candidate

    if payload is None:
        payload = json.loads(content)

    stage = text(payload.get("stage"))
    reason = text(payload.get("reason"))
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid stage: {stage}")
    return stage, reason


def advisory_to_row(
    advisory: dict,
    previous: dict[str, str] | None,
    client: OpenAI | None,
    *,
    repo_name: str,
    full_refresh: bool,
    llm_model: str,
) -> dict[str, str]:
    vulnerabilities = openclaw_vulnerabilities(advisory, repo_name)
    row = {
        "No.": "",
        "Vulnerability Title": text(advisory.get("summary")),
        "Stage": "",
        "Reason": "",
        "Vulnerability ID": text(advisory.get("ghsa_id")).upper(),
        "Github Severity": text(advisory.get("severity")).title(),
        "Affected Versions": unique_join(
            [text(item.get("vulnerable_version_range")).replace(", ", " ") for item in vulnerabilities],
            "\n",
        ),
        "CVE": first_cve(advisory),
        "CWE": unique_join(
            [text(item.get("cwe_id")) for item in advisory.get("cwes") or [] if isinstance(item, dict)],
            "; ",
        ),
        "Vulnerability Link": text(advisory.get("html_url") or advisory.get("permalink")),
    }

    has_previous_analysis = previous and previous.get("Stage") in VALID_STAGES
    if has_previous_analysis and not full_refresh:
        row["Stage"] = previous["Stage"]
        row["Reason"] = previous.get("Reason", "")
    elif client:
        try:
            row["Stage"], row["Reason"] = classify_row(client, llm_model, row)
        except Exception as exc:
            row["Reason"] = f"LLM classification failed: {exc.__class__.__name__}"
    elif has_previous_analysis:
        row["Stage"] = previous["Stage"]
        row["Reason"] = previous.get("Reason", "")
    return row


def write_rows(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


async def main() -> None:
    args = parse_args()
    validate_args(args)

    output_path = Path(args.output).expanduser().resolve()
    existing = load_existing_rows(output_path)
    list_url = f"https://api.github.com/repos/{args.owner}/{args.repo}/security-advisories"
    detail_url = f"{list_url}/{{ghsa_id}}"

    async with httpx.AsyncClient(headers=api_headers(args.github_token), timeout=TIMEOUT) as client:
        ghsa_ids = await discover_ids(client, list_url)
        advisories = await fetch_advisories(client, detail_url, ghsa_ids)

    llm = classifier(args)
    merged: dict[str, dict[str, str]] = {}
    for advisory in tqdm(advisories, desc="Building rows"):
        row = advisory_to_row(
            advisory,
            existing.get(text(advisory.get("ghsa_id")).upper()),
            llm,
            repo_name=args.repo,
            full_refresh=args.full_refresh,
            llm_model=args.llm_model,
        )
        merged[row["Vulnerability ID"]] = row

    rows = sorted(merged.values(), key=lambda row: row["Vulnerability ID"])
    for index, row in enumerate(rows, start=1):
        row["No."] = str(index)

    write_rows(rows, output_path)
    classified_count = sum(1 for row in rows if row.get("Stage") in VALID_STAGES)
    failed_count = sum(1 for row in rows if row.get("Reason", "").startswith("LLM classification failed:"))
    print(
        f"Saved {len(rows)} advisories to {output_path} "
        f"using model={args.llm_model if llm else 'disabled'} base_url={args.llm_base_url if llm else 'disabled'}"
    )
    print(f"Classified rows: {classified_count}, failed classifications: {failed_count}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
