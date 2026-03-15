#!/usr/bin/env python3
"""Annotate OpenClaw vulnerabilities into LLM-specific vs general software classes."""

import csv
import os
from collections import Counter


BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
RAW_CSV_PATH = os.path.join(BASE_DIR, "data", "vuls", "openclaw_vuls.csv")
ANNOTATED_CSV_PATH = os.path.join(BASE_DIR, "data", "vuls", "openclaw_vuls_annotated.csv")

TOP10_META = {
    "prompt-injection": {"rank": 1, "label": "1. Prompt Injection"},
    "malicious-skills": {"rank": 2, "label": "2. 恶意 Skills"},
    "skill-dependency-injection": {"rank": 3, "label": "3. Skill Dependency Injection"},
    "tool-privilege-escalation": {"rank": 4, "label": "4. Tool Privilege Escalation"},
    "clawjacked": {"rank": 5, "label": "5. ClawJacked"},
    "command-injection": {"rank": 6, "label": "6. Command Injection / RCE"},
    "sandbox-hash-collision": {"rank": 7, "label": "7. Sandbox Hash Collision"},
    "token-drain": {"rank": 8, "label": "8. Token Drain / Resource Abuse"},
    "fake-installer": {"rank": 9, "label": "9. Fake Installer / Supply-Chain Malware"},
    "cross-app-leakage": {"rank": 10, "label": "10. Cross-Application Data Leakage"},
}


def contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def classify_vulnerability(row):
    title = row.get("Vulnerability Title", "")
    stage = row.get("Stage", "")
    reason = row.get("Reason", "")
    cwe = row.get("CWE", "")

    text = " ".join([title, stage, reason, cwe]).lower()
    matches = []
    reasons = []

    def add_match(top10_id, why):
        if top10_id not in matches:
            matches.append(top10_id)
            reasons.append(why)

    if contains_any(text, ["llm prompt", "prompt injection", "instruction injection", "unsanitized cwd path injection into llm prompts"]):
        add_match("prompt-injection", "漏洞直接作用于 LLM 提示词或指令上下文。")

    if contains_any(text, ["system.run", "shell-wrapper", "approval gating", "allowlist mode", "dispatch-wrapper", "wrapper-depth", "tool call"]):
        add_match("tool-privilege-escalation", "漏洞作用于 Agent 工具调用审批、allowlist 或命令执行门控。")

    if contains_any(text, ["cwe-77", "cwe-78", "cwe-88", " command ", " shell ", " exec ", " rce ", "subprocess"]):
        if contains_any(text, ["llm", "prompt", "system.run", "shell-wrapper", "tool call", "approval gating"]):
            add_match("command-injection", "漏洞与 Agent/LLM 执行链结合，可演化为命令执行或 RCE。")

    if contains_any(text, ["websocket", "localhost", "gateway", "novnc", "observer", "browser control"]):
        add_match("clawjacked", "漏洞命中了本地控制面、Gateway 或浏览器观察器等 Agent 控制链。")

    if contains_any(text, ["skill", "skills", "plugin", "extension", "marketplace"]):
        if contains_any(text, ["dependency", "download", "fetch", "remote", "webhook", "url payload", "cwe-918", "ssrf"]):
            add_match("skill-dependency-injection", "漏洞涉及 Skill/插件生态中的远程拉取、Webhook 或依赖加载链。")
        elif contains_any(text, ["install", "publish", "source", "repository"]):
            add_match("malicious-skills", "漏洞位于 Skill/插件生态分发链，属于恶意 Skills 风险面。")

    if contains_any(text, ["sandbox", "workspace-only", "container recreation", "config hash", "container", "observer"]) and contains_any(
        text,
        ["cwe-22", "cwe-59", "cwe-367", "cwe-180", "hash", "recreation", "sandbox"],
    ):
        add_match("sandbox-hash-collision", "漏洞位于 OpenClaw 沙箱/容器隔离实现，属于 Agent 隔离面问题。")

    if contains_any(text, ["cwe-400", "resource exhaustion", "dos", "denial", "consumption", "loop", "throttle", "quota"]):
        add_match("token-drain", "漏洞会放大模型/工具资源消耗，接近 Token Drain 风险。")

    if contains_any(text, ["clipboard", "credential leak", "token exposure", "output presentation", "cwe-200", "cwe-201", "cwe-359"]):
        add_match("cross-app-leakage", "漏洞涉及令牌、凭据或输出数据泄露，可演化为跨应用信息外流。")

    if contains_any(text, ["installer", "package", "supply-chain", "fake github", "search ad", "bing ad"]):
        add_match("fake-installer", "漏洞位于安装与分发链，属于假安装包/供应链风险。")

    is_llm_specific = len(matches) > 0

    if is_llm_specific:
        ordered_matches = sorted(matches, key=lambda item: TOP10_META[item]["rank"])
        primary_id = ordered_matches[0]
        primary_label = TOP10_META[primary_id]["label"]
        nature_id = "llm_system_specific"
        nature_label = "大模型系统特有漏洞"
        confidence = 0.65 + min(len(ordered_matches), 3) * 0.1
        analysis_reason = "；".join(reasons)
    else:
        ordered_matches = []
        primary_id = ""
        primary_label = ""
        nature_id = "general_software_vulnerability"
        nature_label = "软件系统通用漏洞"
        confidence = 0.9
        analysis_reason = "漏洞主要表现为通用软件系统中的鉴权、路径处理、资源访问、时序或输入校验缺陷，未体现出大模型系统特有攻击链。"

    return {
        "vulnerability_nature_id": nature_id,
        "vulnerability_nature_label": nature_label,
        "top10_primary_id": primary_id,
        "top10_primary_label": primary_label,
        "top10_match_ids": ", ".join(ordered_matches),
        "top10_match_labels": ", ".join(TOP10_META[item]["label"] for item in ordered_matches),
        "top10_match_count": len(ordered_matches),
        "top10_rank": TOP10_META[primary_id]["rank"] if primary_id else "",
        "mapping_confidence": f"{confidence:.2f}",
        "analysis_reason": analysis_reason,
    }


def main():
    source_csv_path = RAW_CSV_PATH if os.path.exists(RAW_CSV_PATH) else ANNOTATED_CSV_PATH

    with open(source_csv_path, "r", encoding="utf-8-sig", newline="") as source_file:
        rows = list(csv.DictReader(source_file))

    annotated_rows = []
    nature_counter = Counter()
    top10_counter = Counter()

    for row in rows:
        annotation = classify_vulnerability(row)
        merged = dict(row)
        merged.update(annotation)
        annotated_rows.append(merged)
        nature_counter[annotation["vulnerability_nature_label"]] += 1
        if annotation["top10_primary_id"]:
            top10_counter[annotation["top10_primary_label"]] += 1

    fieldnames = list(annotated_rows[0].keys()) if annotated_rows else []

    with open(ANNOTATED_CSV_PATH, "w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(annotated_rows)

    print(f"✅ 已生成漏洞标注 CSV: {ANNOTATED_CSV_PATH}")
    print(f"📄 标注源文件: {source_csv_path}")
    print("📊 漏洞性质分布:")
    for label, count in nature_counter.most_common():
        print(f"  - {label}: {count}")

    if top10_counter:
        print("📊 已映射 OpenClaw Top 10 分布:")
        for label, count in top10_counter.most_common():
            print(f"  - {label}: {count}")


if __name__ == "__main__":
    main()
