#!/usr/bin/env python3
"""OpenClaw Watchboard data analysis pipeline."""

import subprocess
import sys
import time
import os
from pathlib import Path

# 配置路径
SCRIPT_DIR = Path(__file__).parent

def run_script(script_name, description):
    """运行脚本并显示进度"""
    script_path = SCRIPT_DIR / script_name

    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run([sys.executable, str(script_path)],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print(result.stdout)
            duration = time.time() - start_time
            print(f"✅ {description} 完成 (耗时: {duration:.2f}秒)")
        else:
            print(f"❌ {description} 失败:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 运行 {script_name} 时出错: {str(e)}")
        return False

    return True

def main():
    """主函数"""
    print("🎯 OpenClaw Watchboard 数据分析开始...")
    print("📅 开始时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

    overall_start_time = time.time()

    # 运行分析脚本
    has_vuln_sync_credentials = bool(
        os.getenv("OPENCLAW_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    )

    scripts = [
        ("setup_database.py", "数据库初始化"),
        ("analyze_clawhub_skills.py", "ClawHub技能数据分析"),
        ("analyze_csv_skills.py", "CSV技能数据分析"),
        ("generate_statistics.py", "Skills统计数据生成"),
        ("generate_skills_source_chart.py", "Skills数据源静态图生成"),
        ("analyze_exposure_data.py", "Exposure数据分析"),
    ]

    if has_vuln_sync_credentials:
        scripts.append(("update_openclaw_vulnerabilities.py", "GitHub漏洞同步与入库"))
    else:
        scripts.extend(
            [
                ("analyze_vulnerabilities.py", "漏洞标注分析"),
                ("import_vulnerabilities_to_db.py", "漏洞数据入库"),
            ]
        )

    success_count = 0

    for script, description in scripts:
        if run_script(script, description):
            success_count += 1
        else:
            print(f"\n💥 分析管道在 '{description}' 步骤失败")
            return False

    overall_duration = time.time() - overall_start_time

    print(f"\n{'='*60}")
    print("🎉 数据分析管道完成!")
    print(f"📊 成功完成: {success_count}/{len(scripts)} 个步骤")
    print(f"⏱️ 总耗时: {overall_duration:.2f}秒")
    print(f"🗄️ 数据库文件: {SCRIPT_DIR.parent}/data/skills.db")
    print(f"🗄️ 数据库文件: {SCRIPT_DIR.parent}/data/exposure.db")
    print(f"🗄️ 数据库文件: {SCRIPT_DIR.parent}/data/risks.db")
    print("💡 下一步: 启动后端后由 API 直接读取数据库")
    print(f"{'='*60}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
