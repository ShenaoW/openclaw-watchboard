#!/usr/bin/env python3
"""Generate a static skills source distribution chart for the frontend."""

import os
import sqlite3
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "data" / "skills.db"
OUTPUT_DIR = ROOT_DIR / "frontend" / "public" / "charts"
OUTPUT_FILE = OUTPUT_DIR / "skills-source-distribution.svg"


def load_source_distribution():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    row = cursor.execute(
        """
        SELECT source_clawhub, source_skills_rest, source_skillsmp
        FROM skill_stats
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    if not row:
        raise RuntimeError("No skill statistics found in skills.db")

    return [
        ("ClawHub", row[0], "#52c41a"),
        ("Skills.rest", row[1], "#1890ff"),
        ("SkillsMP.com", row[2], "#722ed1"),
    ]


def generate_chart():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = [(label, value, color) for label, value, color in load_source_distribution() if value > 0]

    labels = [item[0] for item in sources]
    sizes = [item[1] for item in sources]
    colors = [item[2] for item in sources]
    total = sum(sizes)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=160)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "#ffffff", "linewidth": 2},
        autopct=lambda pct: f"{pct:.1f}%" if pct > 1 else "",
        pctdistance=0.78,
        labeldistance=1.08,
        textprops={"fontsize": 11, "color": "#1f1f1f"},
    )

    for autotext in autotexts:
      autotext.set_color("#ffffff")
      autotext.set_fontsize(10)
      autotext.set_weight("bold")

    ax.text(0, 0.08, f"{total:,}", ha="center", va="center", fontsize=22, weight="bold", color="#111827")
    ax.text(0, -0.11, "Total Skills", ha="center", va="center", fontsize=11, color="#6b7280")
    ax.set_title("Skills Source Distribution", fontsize=15, weight="bold", pad=18)
    ax.axis("equal")

    plt.tight_layout()
    fig.savefig(OUTPUT_FILE, format="svg", bbox_inches="tight", transparent=False)
    plt.close(fig)

    print(f"✅ 生成静态图成功: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_chart()
