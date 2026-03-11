#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import csv
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import shutil

try:
    import websocket
except ImportError:
    websocket = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REPORT_PATH = BASE_DIR / "openclaw_security_report.md"
DEFAULT_SUMMARY_PATH = BASE_DIR / "openclaw_security_report.json"
VULNERABILITY_DB_PATH = BASE_DIR / "openclaw_vulnerabilities_1.csv"

OPENCLAW_DIRS = [
    "/opt/openclaw",
    "/home/openclaw",
    "/etc/openclaw",
    os.path.expanduser("~/.openclaw"),
]

SKILL_DIRS = [
    "/opt/openclaw/skills",
    "/home/openclaw/skills",
    os.path.expanduser("~/.openclaw/workspace/skills"),
]

MCP_DIRS = [
    "/opt/openclaw/mcp",
    "/home/openclaw/mcp",
    os.path.expanduser("~/.openclaw/workspace/mcp"),
]

CONFIG_DIRS = [
    "/opt/openclaw/config",
    "/home/openclaw/config",
    "/etc/openclaw",
    os.path.expanduser("~/.openclaw"),
]

PROMPT_KEYWORDS = ["prompt", "system_prompt", "template", "instruction"]
PROMPT_PATTERNS = [
    r"\{\{.*\}\}",
    r"\$\{.*\}",
    r"(;|&&|\|\|)",
    r"(os\.system|subprocess|exec|eval)",
    r"(ignore previous|system prompt|developer message)",
]

DLP_PATTERNS = {
    "openai_api_key": r"sk-[A-Za-z0-9]{20,}",
    "ssh_private_key": r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
    "jwt_token": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "generic_api_key": r"(api[_-]?key|token|secret)[\"'\s:=]+[A-Za-z0-9_\-]{16,}",
    "mnemonic_phrase": r"([a-z]+\s){11,23}[a-z]+",
}

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
}

MAX_FILE_SIZE = 2 * 1024 * 1024


class Reporter:
    def __init__(self, report_path: Path) -> None:
        self.lines: List[str] = []
        self.report_path = report_path

    def write(self, line: str = "") -> None:
        self.lines.append(line)

    def section(self, title: str) -> None:
        self.write("")
        self.write(f"## {title}")

    def flush(self) -> None:
        with self.report_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))


class TeeReporter(Reporter):
    def write(self, line: str = "") -> None:
        super().write(line)
        print(line)


def run_cmd(cmd: List[str], timeout: int = 8) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "command not found"
    except Exception as e:
        return 1, "", str(e)


def parse_version(version: str) -> Optional[Tuple[int, ...]]:
    nums = re.findall(r"\d+", version)
    if not nums:
        return None
    return tuple(int(x) for x in nums)


def compare_versions(a: Tuple[int, ...], b: Tuple[int, ...]) -> int:
    max_len = max(len(a), len(b))
    a_padded = a + (0,) * (max_len - len(a))
    b_padded = b + (0,) * (max_len - len(b))
    if a_padded < b_padded:
        return -1
    if a_padded > b_padded:
        return 1
    return 0


def parse_constraints(text: str) -> List[Tuple[str, Tuple[int, ...]]]:
    if not text:
        return []
    constraints = []
    for match in re.finditer(r"(<=|>=|<|>|=)?\s*([0-9][0-9A-Za-z\.\-]*)", text):
        op = match.group(1) or "="
        raw_version = match.group(2)
        v = parse_version(raw_version)
        if v:
            constraints.append((op, v))
    return constraints


def match_constraints(version: Tuple[int, ...], constraints: List[Tuple[str, Tuple[int, ...]]]) -> bool:
    if not constraints:
        return False
    for op, c in constraints:
        cmp_res = compare_versions(version, c)
        if op == "<" and not (cmp_res < 0):
            return False
        if op == "<=" and not (cmp_res <= 0):
            return False
        if op == ">" and not (cmp_res > 0):
            return False
        if op == ">=" and not (cmp_res >= 0):
            return False
        if op == "=" and not (cmp_res == 0):
            return False
    return True

def check_openclaw_version(r: Reporter) -> None:
    """检查当前 openclaw 版本及漏洞情况"""
    import subprocess
    import re

    r.section("1. OpenClaw 版本与漏洞")

    try:
        # 获取当前版本
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True,
            text=True
        )

        version = None
        if result.returncode == 0 and result.stdout:
            version = result.stdout.strip()
            r.write(f"当前版本: {version}")
        else:
            r.write("无法获取当前版本 (openclaw --version 失败)")
        clean_version = None
        if version:
            match = re.search(r"(\d+\.\d+\.\d+)", version)
            if match:
                clean_version = match.group(1)

        # 获取最新版本（正确命令）
        update_result = subprocess.run(
            ["openclaw", "update", "status"],
            capture_output=True,
            text=True
        )

        latest_version = None

        if update_result.returncode == 0 and update_result.stdout:

            # 从输出中提取 latest 版本号
            match = re.search(r"latest\s+([0-9]+\.[0-9]+\.[0-9]+)", update_result.stdout)

            if match:
                latest_version = match.group(1)

        if latest_version:
            r.write(f"最新版本: {latest_version}")
        else:
            r.write("无法获取最新版本信息")

        if not latest_version:
            r.write("无法获取最新版本，无法判断是否需要升级。")
        elif not version:
            r.write("无法获取当前版本。")
        else:
            if clean_version == latest_version:
                r.write("当前版本已经是最新版本。")
            else:
                r.write("[警告] 当前版本不是最新，建议升级！")

        # 基于本地漏洞库匹配历史受影响版本
        vuln_csv = VULNERABILITY_DB_PATH
        if not vuln_csv.exists():
            r.write(f"未找到漏洞库: {vuln_csv}")
            return

        if not clean_version:
            r.write("未识别到当前版本号，无法匹配漏洞。")
            return

        cur_v = parse_version(clean_version)
        if not cur_v:
            r.write("当前版本号无法解析，无法匹配漏洞。")
            return

        matched = []
        with vuln_csv.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                affected = (row.get("Affected Versions") or "").strip()
                if not affected:
                    continue
                constraints = parse_constraints(affected)
                if match_constraints(cur_v, constraints):
                    matched.append({
                        "title": (row.get("Vulnerability Title") or "").strip(),
                        "id": (row.get("Vulnerability ID") or "").strip(),
                        "cve": (row.get("CVE") or "").strip(),
                        "severity": (row.get("Severity") or "").strip(),
                        "affected": affected,
                    })

        if matched:
            r.write("检测到当前版本可能受影响的漏洞:")
            for item in matched[:10]:
                cve_part = f"CVE: {item['cve']}, " if item["cve"] else ""
                r.write(
                    f"- 危害性: {item['severity']}, {cve_part}漏洞编号: {item['id']}, "
                    f"{item['title']} (Affected: {item['affected']})"
                )
            if len(matched) > 10:
                r.write(f"仅展示前10条，命中总数: {len(matched)}")
        else:
            r.write("未在本地漏洞库中匹配到受影响项。")

    except Exception as e:
        r.write(f"版本检测异常: {e}")


def check_isolation_environment(r: Reporter) -> None:
    """检查运行环境是否为隔离环境，容器逃逸风险、宿主机敏感目录挂载"""
    import subprocess
    from pathlib import Path

    r.section("2. 检查运行环境隔离性及容器逃逸风险：")

    # ----------------- 检查是否在容器环境 -----------------
    docker_env = Path('/.dockerenv').exists()
    cgroup_info = ''
    try:
        with open('/proc/1/cgroup', 'r') as f:
            cgroup_info = f.read()
    except Exception:
        pass

    if docker_env or ('docker' in cgroup_info.lower() or 'kubepods' in cgroup_info.lower()):
        r.write("检测到容器环境 (Docker/Kubernetes)")
    else:
        r.write("未检测到容器环境")

    # ----------------- 检查虚拟机 -----------------
    try:
        dmi = subprocess.run(['cat', '/sys/class/dmi/id/product_name'], capture_output=True, text=True)
        if dmi.returncode == 0 and any(x in dmi.stdout.lower() for x in ['vmware', 'virtualbox', 'kvm', 'qemu', 'xen', 'hyper-v']):
            r.write(f"检测到虚拟机环境: {dmi.stdout.strip()}")
        else:
            r.write("未检测到虚拟机环境")
    except Exception:
        r.write("虚拟机检测异常")

    # ----------------- 检查 systemd 虚拟化类型 -----------------
    try:
        virt = subprocess.run(['systemd-detect-virt'], capture_output=True, text=True)
        if virt.returncode == 0 and virt.stdout.strip() != 'none':
            r.write(f"虚拟化类型: {virt.stdout.strip()}")
    except Exception:
        pass

    # ----------------- 检查宿主机敏感目录挂载 -----------------
    sensitive_mounts = []
    try:
        with open('/proc/self/mountinfo', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                mount_source = parts[3]  # 挂载源
                mount_target = parts[4]  # 容器挂载点

                # 只检测宿主机系统敏感目录挂载
                if any(mount_source.startswith(p) for p in ['/root', '/etc', '/var', '/boot', '/usr']):
                    if not any(x in mount_source for x in ['/var/lib/docker/containers']):
                        sensitive_mounts.append(f"{mount_source} -> {mount_target}")
    except Exception:
        pass

    if sensitive_mounts:
        r.write("[警告] 检测到宿主机敏感目录挂载：")
        for m in sensitive_mounts[:5]:
            r.write(f"  {m}")
    else:
        r.write("未检测到宿主机敏感目录挂载")
    # ----------------- 检查常见容器逃逸风险设备 -----------------
    escape_risks = []
    for path in ['/dev/kmsg', '/dev/mem', '/dev/sda', '/dev/vda', '/dev/hypervisor', '/proc/sysrq-trigger']:
        if Path(path).exists():
            escape_risks.append(path)
    if escape_risks:
        r.write("[警告] 检测到容器逃逸风险设备：" + ', '.join(escape_risks))
    else:
        r.write("未检测到容器逃逸风险设备")


from typing import List

def get_openclaw_pids() -> List[str]:
    rc, out, _ = run_cmd(["pgrep", "-af", "openclaw"])
    if rc != 0 or not out:
        return []

    pids = []
    for line in out.splitlines():
        parts = line.strip().split()
        if not parts:
            continue

        pid = parts[0]
        cmdline = " ".join(parts[1:])

        # 排除包含 "openclaw_scan" 的进程
        if "openclaw_scan" in cmdline:
            continue

        pids.append(pid)
    return pids

def list_descendant_pids(root_pids: List[str]) -> List[str]:
    roots = {pid for pid in root_pids if pid.isdigit()}
    if not roots:
        return []
    parent_map = {}
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        stat_path = proc / "stat"
        try:
            stat = stat_path.read_text(errors="ignore")
        except Exception:
            continue
        parts = stat.split()
        if len(parts) < 4:
            continue
        pid = parts[0]
        ppid = parts[3]
        parent_map.setdefault(ppid, []).append(pid)
    descendants = []
    queue = list(roots)
    seen = set(roots)
    while queue:
        p = queue.pop(0)
        for child in parent_map.get(p, []):
            if child in seen:
                continue
            seen.add(child)
            descendants.append(child)
            queue.append(child)
    return descendants


def read_cmdline(pid: str) -> str:
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    try:
        raw = cmdline_path.read_bytes()
    except Exception:
        return ""
    if not raw:
        return ""
    return raw.replace(b"\x00", b" ").decode(errors="ignore").strip()


def read_comm(pid: str) -> str:
    comm_path = Path(f"/proc/{pid}/comm")
    try:
        return comm_path.read_text(errors="ignore").strip()
    except Exception:
        return ""


def check_root_privilege(r: Reporter) -> None:
    r.section("3. 运行权限与 root 检查")
    pids = get_openclaw_pids()
    if not pids:
        r.write("未检测到 openclaw 进程。")
        return
    for pid in pids:
        rc, out, _ = run_cmd(["ps", "-o", "user=", "-p", pid])
        user = out.strip() if out else "unknown"
        if user == "root":
            r.write(f"openclaw 进程 PID={pid} 以 root 运行，存在风险。")
        else:
            r.write(f"openclaw 进程 PID={pid} 以用户 {user} 运行。")


def check_filesystem_write_scope(r: Reporter) -> None:
    r.section("4. 文件系统写权限范围")
    pids = get_openclaw_pids()
    if not pids:
        r.write("未检测到 openclaw 进程。")
        return
    check_dirs = ["/etc", "/var", "/tmp", "/root", "/home", "/usr/local", "/opt"]
    for pid in pids:
        root_path = Path(f"/proc/{pid}/root")
        if not root_path.exists():
            r.write(f"PID={pid} root 挂载点不存在，无法检测。")
            continue
        writable = []
        for d in check_dirs:
            test_path = root_path / d.lstrip("/")
            try:
                if os.access(str(test_path), os.W_OK):
                    writable.append(d)
            except Exception:
                continue
        if writable:
            r.write(f"PID={pid} 可写目录: {', '.join(writable)}")
        else:
            r.write(f"PID={pid} 未检测到常见目录可写权限。")
        try:
            if os.access(str(root_path), os.W_OK):
                r.write(f"PID={pid} 对根目录有写权限，风险较高。")
        except Exception:
            pass


def list_public_ipv4() -> List[str]:
    rc, out, _ = run_cmd(["ip", "-o", "-4", "addr", "show"])
    if rc != 0 or not out:
        return []
    public = []
    for line in out.splitlines():
        m = re.search(r"inet\s+([0-9\.]+)/", line)
        if not m:
            continue
        ip = m.group(1)
        if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("127.") or ip.startswith("169.254."):
            continue
        if ip.startswith("172."):
            try:
                second = int(ip.split(".")[1])
                if 16 <= second <= 31:
                    continue
            except Exception:
                pass
        public.append(ip)
    return public


def check_gateway_port_exposure(r: Reporter) -> None:
    r.section("5. Gateway 端口 18789 暴露情况")
    if not shutil.which("ss"):
        r.write("未检测到 ss 命令，无法获取端口监听信息。")
        if sys.stdin.isatty():
            choice = input("是否安装 ss(来自 iproute2)？输入 y 安装，其它键跳过: ").strip().lower()
            if choice == "y":
                if not install_ss_package(r):
                    return
            else:
                return
        else:
            return
    rc, out, _ = run_cmd(["ss", "-lntp"])
    if rc != 0:
        r.write("无法获取端口监听信息 (ss -lntp 失败)。")
        return
    listen_lines = [l for l in out.splitlines() if ":18789" in l]
    if not listen_lines:
        r.write("未检测到 18789 端口监听。")
        return
    for line in listen_lines:
        r.write(f"监听记录: {line}")
    bound_all = any("0.0.0.0:18789" in l or "[::]:18789" in l for l in listen_lines)
    bound_local = any("127.0.0.1:18789" in l or "[::1]:18789" in l for l in listen_lines)
    public_ips = list_public_ipv4()
    if bound_all and public_ips:
        r.write("18789 监听所有接口且存在公网 IP，存在公网暴露风险。")
        r.write(f"公网 IP: {', '.join(public_ips)}")
    elif bound_all:
        r.write("18789 监听所有接口，未检测到公网 IP，但仍建议仅绑定本地或内网。")
    elif bound_local:
        r.write("18789 仅监听本地地址。")
    else:
        r.write("18789 监听非本地地址，请人工确认是否安全。")


def install_ss_package(r: Reporter) -> bool:
    managers = [
        ("apt-get", ["apt-get", "update"]),
        ("apt-get", ["apt-get", "install", "-y", "iproute2"]),
        ("dnf", ["dnf", "install", "-y", "iproute"]),
        ("yum", ["yum", "install", "-y", "iproute"]),
        ("apk", ["apk", "add", "iproute2"]),
        ("pacman", ["pacman", "-Sy", "--noconfirm", "iproute2"]),
        ("zypper", ["zypper", "--non-interactive", "install", "iproute2"]),
    ]

    def run_install(cmd: List[str]) -> bool:
        rc, out, err = run_cmd(cmd, timeout=120)
        if rc == 0:
            return True
        r.write(f"安装命令失败: {' '.join(cmd)}")
        if err:
            r.write(f"错误: {err}")
        return False

    if os.geteuid() != 0 and shutil.which("sudo"):
        r.write("当前非 root，尝试使用 sudo 安装 iproute2。")
        managers = [(m, ["sudo"] + cmd) for m, cmd in managers]
    elif os.geteuid() != 0:
        r.write("当前非 root 且无 sudo，无法自动安装。")
        return False

    for mgr, cmd in managers:
        if not shutil.which(cmd[0]):
            continue
        if cmd[0].endswith("apt-get") and cmd[-1] != "iproute2":
            if run_install(cmd):
                continue
            else:
                return False
        if run_install(cmd):
            r.write("ss 安装完成，继续检测。")
            return True

    r.write("未找到可用包管理器，无法自动安装 ss。")
    return False


def check_api_and_websocket(r: Reporter) -> None:
    r.section("6. WebSocket/HTTP API/RPC/Debug/Metrics 接口")
    rc, out, _ = run_cmd(["ss", "-lntp"])
    if rc != 0:
        r.write("无法获取端口监听信息。")
        return
    api_ports = {
        "http": [80, 8080, 8000, 5000, 18789],
        "ws": [18789, 9000, 8888],
        "rpc": [8545, 18545],
        "debug": [9229, 5001],
        "metrics": [9100, 9090, 8001],
    }
    findings = []
    for line in out.splitlines():
        for proto, ports in api_ports.items():
            for port in ports:
                if f":{port}" in line:
                    findings.append((proto, port, line.strip()))
    if not findings:
        r.write("未检测到常见 API/WebSocket/RPC/Debug/Metrics 端口监听。")
    for proto, port, info in findings:
        if "0.0.0.0" in info or "[::]" in info:
            r.write(f"{proto.upper()} 端口 {port} 监听所有地址: {info}")
        elif "127.0.0.1" in info or "[::1]" in info:
            r.write(f"{proto.upper()} 端口 {port} 仅监听本地: {info}")
        else:
            r.write(f"{proto.upper()} 端口 {port} 监听: {info}")

    config_hits = []
    for base in CONFIG_DIRS:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for path in base_path.rglob("*"):
            if path.is_dir():
                if path.name in EXCLUDE_DIRS:
                    continue
                continue
            if path.suffix.lower() not in [".yaml", ".yml", ".json", ".toml", ".env", ".conf"]:
                continue
            try:
                content = path.read_text(errors="ignore").lower()
            except Exception:
                continue
            if "0.0.0.0" in content or "listen" in content or "bind" in content:
                config_hits.append(str(path))
    if config_hits:
        r.write("配置文件中检测到疑似监听配置:")
        for p in config_hits[:10]:
            r.write(f"- {p}")
        if len(config_hits) > 10:
            r.write(f"仅展示前10条，命中总数: {len(config_hits)}")


def audit_agent_behavior(r: Reporter) -> None:
    r.section("7. AI Agent 行为权限审计")
    pids = get_openclaw_pids()
    if not pids:
        r.write("未检测到 openclaw 进程。")
    else:
        rc, out, _ = run_cmd(["pgrep", "-af", "openclaw"])
        if rc == 0 and out:
            r.write("检测到 openclaw 主进程:")
            for line in out.splitlines():
                line_l = line.lower()
                if any(x in line_l for x in ["--shell", "--exec", "--system", "--eval", "tools.exec", "system.run"]):
                    r.write(f"命令行包含危险参数: {line}")
                elif "openclaw_scan" in line_l:
                    continue
                else:
                    r.write(f"命令行: {line}")
        descendant_pids = list_descendant_pids(pids)
        if descendant_pids:
            r.write("检测到 openclaw 子孙进程:")
            risky_flags = ["--shell", "--exec", "--system", "--eval", "tools.exec", "system.run", "bash", "sh", "python", "curl", "wget"]
            for pid in sorted(descendant_pids, key=lambda x: int(x)):
                cmd = read_cmdline(pid)
                if not cmd:
                    cmd = read_comm(pid)
                if not cmd:
                    continue
                cmd_l = cmd.lower()
                if any(x in cmd_l for x in risky_flags):
                    r.write(f"子进程命令行包含高风险关键词: pid={pid} cmd={cmd}")
                else:
                    r.write(f"子进程命令行: pid={pid} cmd={cmd}")
        else:
            r.write("未检测到 openclaw 子孙进程。")

    risky_keys = ["shell", "exec", "system.run", "tools.exec", "file_write", "file_read", "filesystem"]
    for base in CONFIG_DIRS:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for path in base_path.rglob("*"):
            if path.is_dir():
                if path.name in EXCLUDE_DIRS:
                    continue
                continue
            if path.suffix.lower() not in [".yaml", ".yml", ".json", ".toml", ".env", ".conf"]:
                continue
            try:
                content = path.read_text(errors="ignore").lower()
            except Exception:
                continue
            if any(k in content for k in risky_keys):
                r.write(f"配置中包含高权限能力关键词: {path}")


def check_prompt_injection_risk(r: Reporter) -> None:
    r.section("8. Prompt Injection 风险检测")
    hits = []
    for base in OPENCLAW_DIRS + CONFIG_DIRS + SKILL_DIRS:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for path in base_path.rglob("*"):
            if path.is_dir():
                if path.name in EXCLUDE_DIRS:
                    continue
                continue
            name_l = path.name.lower()
            if not (any(k in name_l for k in PROMPT_KEYWORDS) or path.suffix.lower() in [".md", ".txt", ".prompt"]):
                continue
            try:
                content = path.read_text(errors="ignore")
            except Exception:
                continue
            for pattern in PROMPT_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    hits.append((str(path), pattern))
    if hits:
        r.write("检测到可能的 prompt 注入风险模式:")
        for path, pattern in hits[:20]:
            r.write(f"- {path} 命中 {pattern}")
        if len(hits) > 20:
            r.write(f"仅展示前20条，命中总数: {len(hits)}")
    else:
        r.write("未检测到明显的 prompt 注入风险。")


def hashlib_sha256(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def check_skill_trust_and_hash(r: Reporter) -> None:
    r.section("9. 技能来源可信性与哈希扫描")
    dangerous_funcs = ["subprocess", "os.system", "exec", "eval"]
    skill_count = 0
    from_git = 0
    from_local = 0
    hash_snapshot = {}

    def scan_dir(root_dir: str) -> None:
        nonlocal skill_count, from_git, from_local
        root_path = Path(root_dir)
        if not root_path.exists():
            return
        for skill in root_path.iterdir():
            if not skill.is_dir():
                continue
            skill_count += 1
            if (skill / ".git").exists():
                from_git += 1
            else:
                from_local += 1
            for path in skill.rglob("*.py"):
                try:
                    content = path.read_text(errors="ignore").lower()
                except Exception:
                    continue
                for func in dangerous_funcs:
                    if func in content:
                        r.write(f"技能包含危险函数: {path} -> {func}")
                h = hashlib_sha256(content.encode("utf-8"))
                hash_snapshot[str(path)] = h

    for d in SKILL_DIRS:
        scan_dir(d)

    r.write(f"技能总数: {skill_count}, Git 来源: {from_git}, 本地来源: {from_local}")
    if skill_count > 10:
        r.write("技能数量偏多，建议定期审计。")

    for d in MCP_DIRS:
        d_path = Path(d)
        if not d_path.exists():
            continue
        for path in d_path.rglob("*.py"):
            try:
                content = path.read_text(errors="ignore").lower()
            except Exception:
                continue
            for func in dangerous_funcs:
                if func in content:
                    r.write(f"MCP 包含危险函数: {path} -> {func}")
            h = hashlib_sha256(content.encode("utf-8"))
            hash_snapshot[str(path)] = h

    if hash_snapshot:
        r.write("Skill/MCP 文件哈希快照(部分):")
        for k in list(hash_snapshot.keys())[:10]:
            r.write(f"- {k}: {hash_snapshot[k]}")
        if len(hash_snapshot) > 10:
            r.write(f"仅展示前10条，命中总数: {len(hash_snapshot)}")
    else:
        r.write("未检测到 Skill/MCP 目录文件。")


def check_resource_anomalies(r: Reporter) -> None:
    r.section("10. 资源异常检测")
    rc, out, _ = run_cmd(["ps", "-eo", "pid,pcpu,pmem,comm", "--sort=-pcpu"])
    if rc == 0 and out:
        r.write("高CPU进程快照(前10):")
        for line in out.splitlines()[1:11]:
            r.write(line)
    else:
        r.write("无法获取高CPU进程快照。")

    rc, out, _ = run_cmd(["ss", "-tunap"])
    if rc == 0 and out:
        public_conns = []
        for line in out.splitlines():
            if "ESTAB" not in line:
                continue
            m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):\d+", line)
            if not m:
                continue
            ip = m.group(1)
            if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("127.") or ip.startswith("169.254."):
                continue
            if ip.startswith("172."):
                try:
                    second = int(ip.split(".")[1])
                    if 16 <= second <= 31:
                        continue
                except Exception:
                    pass
            public_conns.append(line.strip())
        if public_conns:
            r.write("检测到对公网IP的连接(部分):")
            for l in public_conns[:10]:
                r.write(l)
        else:
            r.write("未检测到明显对公网IP的连接。")
    else:
        r.write("无法获取网络连接信息。")

    large_files = []
    try:
        find_cmd = ["find", "/var", "/tmp", "-type", "f", "-size", "+100M", "-mtime", "-1"]
        rc, out, _ = run_cmd(find_cmd, timeout=12)
        if rc == 0 and out:
            large_files = out.splitlines()
    except Exception:
        pass
    if large_files:
        r.write(f"近24小时大文件(>100M)数量: {len(large_files)}")
        for f in large_files[:5]:
            r.write(f"- {f}")
    else:
        r.write("未检测到近24小时大文件写入(仅扫描/var与/tmp)。")


def check_logs_and_auth(r: Reporter) -> None:
    r.section("11. 日志与认证检测")
    rc, out, _ = run_cmd(["last", "-a", "-n", "5"])
    if rc == 0 and out:
        r.write("最近登录记录:")
        for l in out.splitlines()[:5]:
            r.write(l)
    else:
        r.write("无法获取最近登录记录。")

    failed_ssh = 0
    rc, out, _ = run_cmd(["journalctl", "-u", "sshd", "--since", "24 hours ago"])
    if rc == 0 and out:
        failed_ssh = out.lower().count("failed") + out.lower().count("invalid")
    if failed_ssh == 0:
        for log_file in ["/var/log/auth.log", "/var/log/secure", "/var/log/messages"]:
            if Path(log_file).exists():
                rc, out, _ = run_cmd(["grep", "-Ei", "sshd.*(Failed|Invalid)", log_file])
                if rc == 0 and out:
                    failed_ssh = len(out.splitlines())
                break
    r.write(f"SSH 失败尝试(近24h): {failed_ssh}")

    keywords = ["sudo", "root", "failed", "invalid", "error", "denied", "password", "token", "key"]
    for log_file in ["/var/log/auth.log", "/var/log/secure", "/var/log/messages"]:
        if not Path(log_file).exists():
            continue
        try:
            lines = Path(log_file).read_text(errors="ignore").splitlines()
        except Exception:
            continue
        matched = [l for l in lines if any(k in l.lower() for k in keywords)]
        if matched:
            r.write(f"{log_file} 命中关键词日志 {len(matched)} 条(前5):")
            for l in matched[:5]:
                r.write(f"- {l}")


def check_config_secret_exposure(r: Reporter) -> None:
    r.section("12. 配置明文凭据与环境变量泄露")
    findings = []
    for base in CONFIG_DIRS + OPENCLAW_DIRS:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for path in base_path.rglob("*"):
            if path.is_dir():
                if path.name in EXCLUDE_DIRS:
                    continue
                continue
            if path.suffix.lower() not in [".yaml", ".yml", ".json", ".toml", ".env", ".conf", ".ini"]:
                continue
            try:
                content = path.read_text(errors="ignore")
            except Exception:
                continue
            for name, pattern in DLP_PATTERNS.items():
                if re.search(pattern, content):
                    findings.append((str(path), name))

    # 去重：避免同一路径/规则在多次扫描中重复输出
    deduped = []
    seen = set()
    for item in findings:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)

    if deduped:
        r.write("配置文件中检测到疑似明文凭据:")
        for path, name in deduped[:20]:
            r.write(f"- {path} 命中 {name}")
        if len(deduped) > 20:
            r.write(f"仅展示前20条，命中总数: {len(deduped)}")
    else:
        r.write("未在配置文件中检测到明显明文凭据。")

    pids = get_openclaw_pids()
    for pid in pids:
        env_path = Path(f"/proc/{pid}/environ")
        if not env_path.exists():
            continue
        try:
            env_data = env_path.read_bytes().decode(errors="ignore")
        except Exception:
            continue
        env_items = env_data.split("\x00")
        for item in env_items:
            low = item.lower()
            if any(k in low for k in ["token", "apikey", "api_key", "secret", "password"]):
                r.write(f"PID={pid} 环境变量含敏感关键词: {item.split('=')[0]}")


def scan_dlp(r: Reporter) -> None:
    r.section("13. 明文私钥/助记词泄露扫描(DLP)")
    findings = []
    scan_roots = [p for p in OPENCLAW_DIRS + [os.getcwd()] if Path(p).exists()]
    for base in scan_roots:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                file_path = Path(root) / file
                try:
                    if file_path.stat().st_size > MAX_FILE_SIZE:
                        continue
                    content = file_path.read_text(errors="ignore")
                except Exception:
                    continue
                for name, pattern in DLP_PATTERNS.items():
                    if re.search(pattern, content):
                        findings.append((str(file_path), name))

    if findings:
        r.write("检测到疑似明文敏感信息:")
        for path, name in findings[:20]:
            r.write(f"- {path} 命中 {name}")
        if len(findings) > 20:
            r.write(f"仅展示前20条，命中总数: {len(findings)}")
    else:
        r.write("未检测到明显明文敏感信息。")


def simulate_local_attack(r: Reporter, host: str = "127.0.0.1", port: int = 18789) -> None:
    r.section("14. 本地服务攻击模拟")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
        r.write(f"端口 {port} 可访问。")
    except Exception:
        r.write(f"端口 {port} 不可访问或未开放。")
        return
    finally:
        sock.close()

    try:
        import http.client
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/")
        resp = conn.getresponse()
        r.write(f"HTTP / 响应: {resp.status}")
        conn.close()
    except Exception:
        r.write("HTTP / 探测失败。")

    for path in ["/health", "/metrics", "/debug"]:
        try:
            import http.client
            conn = http.client.HTTPConnection(host, port, timeout=2)
            conn.request("GET", path)
            resp = conn.getresponse()
            r.write(f"HTTP {path} 响应: {resp.status}")
            conn.close()
        except Exception:
            continue


def build_summary(lines: List[str]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "title": "",
        "generatedAt": "",
        "totalSections": 0,
        "warningCount": 0,
        "vulnerabilityMatches": 0,
        "rootProcessRisks": 0,
        "secretFindings": 0,
        "sections": [],
    }

    current_section: Optional[Dict[str, Any]] = None
    for line in lines:
        if line.startswith("# "):
            summary["title"] = line[2:].strip()
            continue

        if line.startswith("检测时间:"):
            summary["generatedAt"] = line.split(":", 1)[1].strip()
            continue

        if line.startswith("## "):
            current_section = {
                "title": line[3:].strip(),
                "items": [],
            }
            summary["sections"].append(current_section)
            continue

        if current_section and line.strip():
            current_section["items"].append(line.strip())

        if "[警告]" in line or "存在风险" in line:
            summary["warningCount"] += 1
        if line.startswith("- 危害性:"):
            summary["vulnerabilityMatches"] += 1
        if "以 root 运行" in line:
            summary["rootProcessRisks"] += 1
        if "命中 " in line:
            summary["secretFindings"] += 1

    summary["totalSections"] = len(summary["sections"])
    return summary


def write_summary(summary_path: Path, lines: List[str]) -> None:
    summary = build_summary(lines)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenClaw 部署安全检测 CLI",
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Markdown 报告输出路径",
    )
    parser.add_argument(
        "--summary-path",
        default=str(DEFAULT_SUMMARY_PATH),
        help="JSON 摘要输出路径",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="仅生成文件，不在终端实时打印检测过程",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_path = Path(args.report_path).expanduser().resolve()
    summary_path = Path(args.summary_path).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    reporter = Reporter(report_path) if args.quiet else TeeReporter(report_path)
    reporter.write("# OpenClaw 部署安全检测报告")
    reporter.write(f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    check_openclaw_version(reporter)
    check_isolation_environment(reporter)

    check_root_privilege(reporter)
    check_filesystem_write_scope(reporter)
    check_gateway_port_exposure(reporter)
    check_api_and_websocket(reporter)
    audit_agent_behavior(reporter)
    check_prompt_injection_risk(reporter)
    check_skill_trust_and_hash(reporter)
    check_resource_anomalies(reporter)
    check_logs_and_auth(reporter)
    check_config_secret_exposure(reporter)
    scan_dlp(reporter)
    # simulate_local_attack(reporter)

    reporter.write("")
    reporter.write("=== 检测完成 ===")
    reporter.flush()
    write_summary(summary_path, reporter.lines)
    print(f"安全检测报告已生成: {report_path}")
    print(f"安全检测摘要已生成: {summary_path}")


if __name__ == "__main__":
    main()
