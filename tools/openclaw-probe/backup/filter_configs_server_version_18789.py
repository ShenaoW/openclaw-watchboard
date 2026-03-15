#!/usr/bin/env python3
"""
筛选 configs JSON：
1) 顶层键为 ip:port（可选按端口过滤）
2) 对应值必须是对象(dict)，且包含 serverVersion 键

用法:
    python filter_configs_server_version_18789.py \
        endpoint_alive_20260313_155245_configs.json
  python filter_configs_server_version_18789.py input.json -o output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_port_from_key(key: str) -> int | None:
    """从形如 ip:port 的键中提取端口，失败返回 None。"""
    text = (key or "").strip()
    if not text or ":" not in text:
        return None

    port_text = text.rsplit(":", 1)[1]
    if not port_text.isdigit():
        return None

    return int(port_text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="保留包含 serverVersion 的 JSON 项（可选按端口过滤）"
    )
    parser.add_argument("input_json", help="输入 JSON 文件路径")
    parser.add_argument(
        "-o",
        "--output",
        help="输出 JSON 文件路径（默认: 输入文件名 + _serverVersion_allports 或 _serverVersion_<port>）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="目标端口（不传则不过滤端口）",
    )
    parser.add_argument(
        "--version-key",
        default="serverVersion",
        help="版本键名（默认 serverVersion）",
    )
    args = parser.parse_args()

    in_path = Path(args.input_json)
    if not in_path.exists():
        sys.exit(f"[错误] 输入文件不存在: {in_path}")

    if args.output:
        out_path = Path(args.output)
    else:
        suffix = f"{args.port}" if args.port is not None else "allports"
        out_path = in_path.with_name(
            f"{in_path.stem}_serverVersion_{suffix}.json"
        )

    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.exit(f"[错误] 读取或解析 JSON 失败: {exc}")

    if not isinstance(data, dict):
        sys.exit("[错误] 输入 JSON 顶层不是对象，无法按 ip:port 键筛选")

    total = len(data)
    kept: dict[str, object] = {}

    for key, value in data.items():
        port = parse_port_from_key(key)
        if args.port is not None and port != args.port:
            continue
        if not isinstance(value, dict):
            continue
        if args.version_key not in value:
            continue
        kept[key] = value

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"输入条目数: {total}")
    print(f"保留条目数: {len(kept)}")
    print(f"输出文件: {out_path}")


if __name__ == "__main__":
    main()
