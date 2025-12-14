#!/usr/bin/env python3
"""
Lightweight CLI to run the learning control system described in learning-control-system.md.
Keeps a simple CSV log, generates short missions, checks bias, and outputs a NotebookLM-ready weekly summary.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
from pathlib import Path
from typing import Iterable, List, Tuple

LOG_HEADERS = ["date", "kind", "content", "memo"]
KIND_LABELS = {
    "contact": "接触",
    "experience": "体験",
    "understanding": "理解",
}

CONTACT_MISSIONS = [
    "Twitterで『LLM プロンプト』を5件流し見して1件スクショ",
    "YouTubeで最新AIデモを1本倍速で見る",
    "AI関連ニュースレターを1つ眺めてリンクを1本保存",
    "気になるプロンプトTipsを1件探してスクショ",
]
EXPERIENCE_MISSIONS = [
    "自分のメモをChatGPTに投げて見出しだけ返してもらう",
    "画像生成で『今日の気分』を1枚作る",
    "議事録をClaudeに貼り、要約を1行でもらう",
    "音声→文字起こしを手持ちのツールで1本試す",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Learning control CLI")
    parser.add_argument(
        "--file",
        default="input-log.csv",
        type=Path,
        help="Path to the CSV log (default: input-log.csv)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    mission = sub.add_parser("mission", help="Generate a 5-10 minute mission")
    mission.add_argument(
        "--type",
        choices=["contact", "experience"],
        default=random.choice(["contact", "experience"]),
        help="Mission type (接触/体験)",
    )

    log = sub.add_parser("log", help="Append a 1-line log entry")
    log.add_argument("--type", choices=list(KIND_LABELS), required=True)
    log.add_argument("--content", required=True, help="Link / screenshot / tried action")
    log.add_argument("--memo", default="", help="Optional memo")
    log.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="YYYY-MM-DD (default: today)",
    )

    summary = sub.add_parser("summary", help="Show 7-day bias check and weekly summary text")
    summary.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    summary.add_argument("--themes", nargs="*", default=[], help="Optional themes to carry over")

    return parser.parse_args()


def ensure_log(file: Path) -> None:
    if not file.exists():
        file.write_text(",".join(LOG_HEADERS) + "\n", encoding="utf-8")


def append_log(file: Path, date: str, kind: str, content: str, memo: str) -> None:
    ensure_log(file)
    with file.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([date, kind, content, memo])


def load_logs(file: Path) -> List[Tuple[dt.date, str, str, str]]:
    if not file.exists():
        return []
    rows: List[Tuple[dt.date, str, str, str]] = []
    with file.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                d = dt.date.fromisoformat(row.get("date", ""))
            except ValueError:
                continue
            rows.append((d, row.get("kind", ""), row.get("content", ""), row.get("memo", "")))
    return rows


def filter_recent(logs: Iterable[Tuple[dt.date, str, str, str]], days: int) -> List[Tuple[dt.date, str, str, str]]:
    today = dt.date.today()
    threshold = today - dt.timedelta(days=days - 1)
    return [row for row in logs if row[0] >= threshold]


def count_kinds(logs: Iterable[Tuple[dt.date, str, str, str]]) -> Tuple[int, int, int]:
    c = t = u = 0
    for _, kind, _, _ in logs:
        if kind == "contact":
            c += 1
        elif kind == "experience":
            t += 1
        elif kind == "understanding":
            u += 1
    return c, t, u


def bias_feedback(c: int, t: int, u: int) -> str:
    if t < max(int(c * 0.3), 1) or t <= 2:
        return "接触がリード中。今日のミッションは体験5分にしてみる？"
    if c > t * 3 and c >= 5:
        return "リンク収集中でいい感じ。週に1回だけ、1本手を動かすとバランス取れそう。"
    if c + t < 4:
        return "今週は軽め。余裕が出た日に1ミッション足すだけでOK。"
    return "接触と体験がほどよく混ざってる。続けてOK。"


def meter(c: int, t: int, u: int) -> str:
    return f"接触 {'█' * c or '・'} {c}件 | 体験 {'█' * t or '・'} {t}件 | 理解 {'█' * u or '・'} {u}件"


def weekly_summary_text(c: int, t: int, u: int, themes: List[str]) -> str:
    lines = ["【今週のインプット件数】", f"- 接触: {c}件 / 体験: {t}件 / 理解: {u}件", "", "【気づいたこと】", "- （任意、なければ特になし）", "", "【次に回すと良さそうなテーマ（1〜3件）}"]
    if themes:
        lines.extend([f"- {theme}" for theme in themes[:3]])
    else:
        lines.extend([
            "- 例: 音声→テキスト変換を別サービスで試す",
            "- 例: 画像生成のプロンプト短縮を練習する",
            "- 例: ワークフロー自動化ツールを1つ触る",
        ])
    return "\n".join(lines)


def handle_mission(kind: str) -> None:
    if kind == "experience":
        pick = random.choice(EXPERIENCE_MISSIONS)
        label = "体験"
    else:
        pick = random.choice(CONTACT_MISSIONS)
        label = "接触"
    print(f"今日のミッション（{label}・5〜10分）：{pick}")


def handle_log(file: Path, date: str, kind: str, content: str, memo: str) -> None:
    append_log(file, date, kind, content, memo)
    label = KIND_LABELS.get(kind, kind)
    print(f"保存しました → {date} | {label} | {content} | {memo}")


def handle_summary(file: Path, days: int, themes: List[str]) -> None:
    logs = filter_recent(load_logs(file), days)
    c, t, u = count_kinds(logs)
    print("--- 直近ログ件数 ---")
    print(meter(c, t, u))
    print("\n--- 偏りフィードバック ---")
    print(bias_feedback(c, t, u))
    print("\n--- NotebookLM 用 週次まとめ ---")
    print(weekly_summary_text(c, t, u, themes))


def main() -> None:
    args = parse_args()
    if args.command == "mission":
        handle_mission(args.type)
    elif args.command == "log":
        handle_log(args.file, args.date, args.type, args.content, args.memo)
    elif args.command == "summary":
        handle_summary(args.file, args.days, args.themes)


if __name__ == "__main__":
    main()
