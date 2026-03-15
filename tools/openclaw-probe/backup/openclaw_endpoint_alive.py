#!/usr/bin/env python3
"""
OpenClaw 批量端点存活性探测工具
────────────────────────────────────────────────────────────────
对多个 CSV 文件中所有 ip_port（自动去重）并发探测以下端点:

  /health                              -- 只记录状态码
  /healthz                             -- 只记录状态码
  /ready                               -- 只记录状态码
  /readyz                              -- 只记录状态码
  /__openclaw/control-ui-config.json   -- 记录状态码 + 保存响应体
  /avatar/main?meta=1                  -- 只记录状态码

config.json 端点：若返回 200，响应体保存到单独的 JSON 文件中：
  <输出目录>/configs/<ip_port>.json
  以及一个汇总文件 <输出前缀>_configs.json（{ip_port: {...}} 结构）

用法:
    python openclaw_endpoint_alive.py part1.csv part2.csv part3.csv
    python openclaw_endpoint_alive.py *.csv --concurrency 120
    python openclaw_endpoint_alive.py *.csv -o results.csv --timeout 4

依赖:
    pip install aiohttp          # 若未安装则自动回退到线程池 + urllib
"""

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime

# ── Windows: 切换为 SelectorEventLoop，规避 ProactorEventLoop 的 WinError 10054 崩溃 ──
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ── 优先使用 aiohttp，回退到 urllib + ThreadPool ────────────────────────────
try:
    import aiohttp
    _BACKEND = "aiohttp"
except ImportError:
    _BACKEND = "urllib"
    import urllib.request
    import urllib.error
    from concurrent.futures import ThreadPoolExecutor

# ── 端点定义 ─────────────────────────────────────────────────────────────────
# 只记录状态码的端点
STATUS_ONLY_ENDPOINTS = [
    "/health",
    "/healthz",
    "/ready",
    "/readyz",
    "/avatar/main?meta=1",
]
# 需要保存响应体的端点
CONFIG_ENDPOINT = "/__openclaw/control-ui-config.json"

ALL_ENDPOINTS = STATUS_ONLY_ENDPOINTS + [CONFIG_ENDPOINT]

def col(path: str) -> str:
    """将端点路径转为 CSV 安全列名。"""
    return path.lstrip("/").replace("/", "_").replace("?", "_").replace("=", "_")

COL_NAMES = [col(p) for p in ALL_ENDPOINTS]
CONFIG_COL = col(CONFIG_ENDPOINT)

DEFAULT_CONCURRENCY = 80
DEFAULT_TIMEOUT      = 5


# ── aiohttp 后端 ─────────────────────────────────────────────────────────────

async def fetch_aiohttp(
    session: "aiohttp.ClientSession",
    sem: asyncio.Semaphore,
    ip_port: str,
    path: str,
    save_body: bool,
) -> tuple[str, str | None]:
    """
    返回 (status_str, body_or_None)。
    save_body=True 且状态为 200 时，body 为响应文本；否则 body=None。
    """
    url = f"http://{ip_port}{path}"
    async with sem:
        try:
            async with session.get(url, allow_redirects=False) as resp:
                status = str(resp.status)
                if save_body and resp.status == 200:
                    body = await resp.text(encoding="utf-8", errors="replace")
                else:
                    body = None
                return status, body
        except aiohttp.ClientConnectorError:
            return "refused", None
        except asyncio.TimeoutError:
            return "timeout", None
        except aiohttp.ServerDisconnectedError:
            return "disconnected", None
        except aiohttp.ClientResponseError as e:
            return str(e.status), None
        except Exception:
            return "err", None


async def run_aiohttp(
    entries: list[str], timeout: int, concurrency: int
) -> tuple[dict[str, dict], dict[str, str]]:
    """
    返回:
      results   : {ip_port: {col_name: status_str}}
      config_bodies : {ip_port: raw_body_text}  （仅 200 的条目）
    """
    # 静默 Windows 下 ConnectionReset / WinError 10054 等回调层噪声日志
    loop = asyncio.get_event_loop()
    def _suppress_conn_reset(loop, context):
        exc = context.get("exception")
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, OSError)):
            return
        loop.default_exception_handler(context)
    loop.set_exception_handler(_suppress_conn_reset)

    sem  = asyncio.Semaphore(concurrency)
    conn = aiohttp.TCPConnector(limit=concurrency, ssl=False, force_close=True)
    to   = aiohttp.ClientTimeout(total=timeout, connect=timeout)

    results: dict[str, dict]       = {ip: {} for ip in entries}
    config_bodies: dict[str, str]  = {}

    total_tasks = len(entries) * len(ALL_ENDPOINTS)
    done_count  = 0
    start       = time.monotonic()

    CHUNK_IPS = 5_000  # 每批最多创建的 IP 数，避免一次性挂载过多 task 引发 WinError 10055

    async with aiohttp.ClientSession(connector=conn, timeout=to) as session:
        for chunk_start in range(0, len(entries), CHUNK_IPS):
            chunk = entries[chunk_start:chunk_start + CHUNK_IPS]
            task_list = [
                (ip, path, asyncio.create_task(
                    fetch_aiohttp(session, sem, ip, path, save_body=(path == CONFIG_ENDPOINT))
                ))
                for ip in chunk
                for path in ALL_ENDPOINTS
            ]
            for ip, path, task in task_list:
                status, body = await task
                results[ip][col(path)] = status
                if path == CONFIG_ENDPOINT and body is not None:
                    config_bodies[ip] = body
                done_count += 1
                if done_count % 100 == 0 or done_count == total_tasks:
                    elapsed = time.monotonic() - start
                    print(f"\r进度: {done_count}/{total_tasks} "
                          f"({done_count/total_tasks*100:.0f}%)  "
                          f"用时 {elapsed:.1f}s", end="", flush=True)

    print()
    return results, config_bodies


# ── urllib 回退后端 ──────────────────────────────────────────────────────────

def fetch_urllib(ip_port: str, path: str, timeout: int, save_body: bool) -> tuple[str, str | None]:
    url = f"http://{ip_port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "probe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = str(resp.status)
            body   = resp.read().decode("utf-8", errors="replace") if save_body and resp.status == 200 else None
            return status, body
    except urllib.error.HTTPError as e:
        return str(e.code), None
    except urllib.error.URLError as e:
        reason = str(e.reason).lower()
        if "refused" in reason:
            return "refused", None
        if "timed out" in reason or "timeout" in reason:
            return "timeout", None
        return "err", None
    except Exception:
        return "err", None


def run_urllib(
    entries: list[str], timeout: int, concurrency: int
) -> tuple[dict[str, dict], dict[str, str]]:
    import concurrent.futures
    results: dict[str, dict]      = {ip: {} for ip in entries}
    config_bodies: dict[str, str] = {}
    tasks  = [(ip, path) for ip in entries for path in ALL_ENDPOINTS]
    total  = len(tasks)
    done   = 0
    start  = time.monotonic()

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {
            ex.submit(fetch_urllib, ip, path, timeout, path == CONFIG_ENDPOINT): (ip, path)
            for ip, path in tasks
        }
        for fut in concurrent.futures.as_completed(futs):
            ip, path = futs[fut]
            status, body = fut.result()
            results[ip][col(path)] = status
            if path == CONFIG_ENDPOINT and body is not None:
                config_bodies[ip] = body
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.monotonic() - start
                print(f"\r进度: {done}/{total} ({done/total*100:.0f}%)  "
                      f"用时 {elapsed:.1f}s", end="", flush=True)

    print()
    return results, config_bodies


# ── 读取 CSV，提取 ip_port ───────────────────────────────────────────────────

def load_ip_ports(csv_files: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in csv_files:
        if not os.path.isfile(path):
            print(f"[警告] 文件不存在，跳过: {path}", file=sys.stderr)
            continue
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            if not fieldnames:
                print(f"[警告] 文件无表头，跳过: {path}", file=sys.stderr)
                continue
            first_col = fieldnames[0]
            for row in reader:
                ip = (row.get(first_col) or "").strip()
                if ip and ip not in seen:
                    seen.add(ip)
                    ordered.append(ip)
    return ordered


# ── 写出结果 ─────────────────────────────────────────────────────────────────

def write_results(
    results: dict[str, dict],
    config_bodies: dict[str, str],
    out_csv: str,
    configs_json: str,
) -> None:
    # ── 主 CSV ──────────────────────────────────────────────────────────────
    fieldnames = ["ip_port", "any_200", "config_ok"] + COL_NAMES
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ip, cols in results.items():
            any_200   = any(v == "200" for v in cols.values())
            config_ok = cols.get(CONFIG_COL) == "200"
            writer.writerow({
                "ip_port":   ip,
                "any_200":   "true" if any_200 else "false",
                "config_ok": "true" if config_ok else "false",
                **cols,
            })

    # ── config body 汇总 JSON ────────────────────────────────────────────────
    # 每条 body 尝试解析为 JSON，解析失败则保存原始字符串
    parsed: dict[str, object] = {}
    for ip, raw in config_bodies.items():
        try:
            parsed[ip] = json.loads(raw)
        except Exception:
            parsed[ip] = raw  # 非 JSON 原文保留

    with open(configs_json, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)


# ── 主函数 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenClaw 批量端点存活性探测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("csv_files", nargs="+", help="一个或多个 CSV 文件路径")
    parser.add_argument("--concurrency", "-c", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"并发连接数（默认 {DEFAULT_CONCURRENCY}）")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT,
                        help=f"每个请求超时秒数（默认 {DEFAULT_TIMEOUT}）")
    parser.add_argument("--rows", "-n", type=int, default=0,
                        help="测试条数（默认 0 = 全部）")
    parser.add_argument("--offset", type=int, default=0,
                        help="跳过前 N 条（默认 0）")
    parser.add_argument("--part", "-p", type=int, default=0,
                        help="分批序号，从 1 开始（与 --of 配合，例如 -p 1 --of 2）")
    parser.add_argument("--of", type=int, default=1,
                        help="总批次数，默认 1（不分批）")
    parser.add_argument("-o", "--output",
                        help="输出 CSV 文件路径（默认自动生成带时间戳文件名）")
    args = parser.parse_args()

    all_entries = load_ip_ports(args.csv_files)
    if not all_entries:
        sys.exit("[错误] 未找到任何有效的第一列 IP:PORT 条目")

    # 分批逻辑：--part/--of 优先于 --offset/--rows
    if args.part > 0 and args.of > 1:
        if args.part > args.of:
            sys.exit(f"[错误] --part {args.part} 超过总批次 --of {args.of}")
        step = (len(all_entries) + args.of - 1) // args.of
        effective_offset = (args.part - 1) * step
        entries = all_entries[effective_offset:effective_offset + step]
    else:
        effective_offset = args.offset
        entries = all_entries[effective_offset:]
        if args.rows > 0:
            entries = entries[:args.rows]

    if not entries:
        sys.exit("[提示] 指定范围内无数据，请检查参数")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    part_suffix = f"_part{args.part}of{args.of}" if args.part > 0 and args.of > 1 else ""
    out_csv     = args.output or f"endpoint_alive_{ts}{part_suffix}.csv"
    configs_json = os.path.splitext(out_csv)[0] + "_configs.json"

    print(f"后端  : {_BACKEND}")
    print(f"总 IP : {len(all_entries)}（已去重）  测试范围: [{effective_offset}, {effective_offset + len(entries) - 1}]  共 {len(entries)} 条")
    print(f"端点数: {len(ALL_ENDPOINTS)}")
    print(f"总请求: {len(entries) * len(ALL_ENDPOINTS)}  ({len(entries)} IP × {len(ALL_ENDPOINTS)} 端点)")
    print(f"并发  : {args.concurrency}  |  超时: {args.timeout}s")
    print(f"CSV   : {out_csv}")
    print(f"配置体: {configs_json}")
    print()

    t0 = time.monotonic()

    if _BACKEND == "aiohttp":
        results, config_bodies = asyncio.run(
            run_aiohttp(entries, args.timeout, args.concurrency)
        )
    else:
        results, config_bodies = run_urllib(entries, args.timeout, args.concurrency)

    elapsed = time.monotonic() - t0
    write_results(results, config_bodies, out_csv, configs_json)

    total  = len(entries)
    alive  = sum(1 for cols in results.values() if any(v == "200" for v in cols.values()))
    config = len(config_bodies)

    print(f"完成! 用时 {elapsed:.1f}s  （平均 {elapsed / total * 1000:.0f}ms/IP）")
    print(f"任意端点 200      : {alive}/{total}")
    print(f"config.json 200  : {config}/{total}  → {configs_json}")
    print()
    print("各端点 200 命中率:")
    for path, cname in zip(ALL_ENDPOINTS, COL_NAMES):
        hits = sum(1 for cols in results.values() if cols.get(cname) == "200")
        bar  = "█" * min(hits, 40) + "░" * max(0, min(total, 40) - hits)
        print(f"  {path:<42} {hits:>4}/{total}  {bar}")

    print(f"\n主结果已写入  : {out_csv}")
    print(f"配置响应已写入: {configs_json}")


if __name__ == "__main__":
    main()
