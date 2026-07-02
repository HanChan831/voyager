#!/usr/bin/env python3
"""
旅行时间线核验脚本。

读取 trip_data.json，按天整理出时间轴，检测时间重叠冲突、
统计每天实际占用时长，并对节奏过于紧凑或空档过大的情况给出提示。

用法:
    python3 schedule_checker.py <trip_data.json>
"""

import json
import sys
from collections import defaultdict

DENSE_DAY_THRESHOLD_MINUTES = 12 * 60  # 单日超过12小时视为偏紧凑
LARGE_GAP_THRESHOLD_MINUTES = 60       # 两项之间空档超过60分钟时提示


def to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m


def minutes_to_label(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 schedule_checker.py <trip_data.json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    by_day = defaultdict(list)
    skipped = 0
    for item in data.get("items", []):
        if item.get("time_start") and item.get("time_end") and item.get("day"):
            by_day[item["day"]].append(item)
        elif item.get("time_start") or item.get("time_end"):
            skipped += 1

    if not by_day:
        print("[提示] 没有找到任何带完整 day/time_start/time_end 的行程项，无法生成时间线。")
        sys.exit(0)

    total_warnings = 0

    for day in sorted(by_day.keys()):
        items = sorted(by_day[day], key=lambda x: to_minutes(x["time_start"]))
        print(f"\n=== 第{day}天 时间轴 ===")
        prev_end = None
        prev_desc = None
        total_minutes = 0

        for it in items:
            start = to_minutes(it["time_start"])
            end = to_minutes(it["time_end"])
            desc = it.get("description", "(未命名项目)")

            if end <= start:
                print(f"  ⚠️ 警告：'{desc}' 的结束时间早于或等于开始时间，请检查")
                total_warnings += 1

            if prev_end is not None:
                if start < prev_end:
                    print(
                        f"  ⚠️ 时间冲突：'{desc}' ({it['time_start']}-{it['time_end']}) "
                        f"与上一项 '{prev_desc}' (结束于 {minutes_to_label(prev_end)}) 重叠"
                    )
                    total_warnings += 1
                elif start - prev_end > LARGE_GAP_THRESHOLD_MINUTES:
                    gap = start - prev_end
                    print(
                        f"  ℹ️ 空档 {gap} 分钟（{minutes_to_label(prev_end)} - {it['time_start']}），"
                        f"确认是否需要安排内容，或这本来就是预留的休息/缓冲时间"
                    )

            print(f"  {it['time_start']}-{it['time_end']}  {desc}")
            total_minutes += max(0, end - start)
            prev_end = end
            prev_desc = desc

        hours = total_minutes / 60
        print(f"  —— 当日有安排活动合计约 {hours:.1f} 小时")
        if total_minutes > DENSE_DAY_THRESHOLD_MINUTES:
            print(f"  ⚠️ 当日行程偏紧凑（超过 {DENSE_DAY_THRESHOLD_MINUTES / 60:.0f} 小时），建议适当精简或预留休息时间")
            total_warnings += 1

    print(f"\n=== 核验完成，共 {total_warnings} 条需要关注的警告 ===")
    if skipped:
        print(f"[提示] 有 {skipped} 条记录缺少 day/time_start/time_end 中的部分字段，未计入时间线检查。")


if __name__ == "__main__":
    main()
