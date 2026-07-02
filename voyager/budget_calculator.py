#!/usr/bin/env python3
"""
旅行预算核算脚本。

读取 trip_data.json，先按天分组，天内再按类别汇总费用，自动处理 per_person 换算，
输出"每一天 → 天内各类别明细 → 当天小计 → 总计"的清晰层级。

所有金额一律按 trip.currency 这个统一口径核算（用户在第1步选定，默认人民币 CNY）——
trip_data.json 里的 amount 不应该出现跟 trip.currency 不一致的数字。
第11步只做核算和生成，不再追加询问或显示第二种换算货币。

用法:
    python3 budget_calculator.py <trip_data.json> [output.md]
"""

import html
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def esc(value):
    return html.escape(str(value), quote=True)



def day_label(day, base_date=None):
    """生成"第N天（M月D日 周X）"格式的标签。"""
    if not day:
        return "行前/通用"
    prefix = f"第{day}天"
    if base_date:
        try:
            d = base_date + timedelta(days=int(day) - 1)
            prefix += f"（{d.month}月{d.day}日 {WEEKDAYS[d.weekday()]}）"
        except Exception:
            pass
    return prefix


def compute(data):
    trip = data.get("trip", {})
    travelers = trip.get("travelers", 1)
    currency = trip.get("currency", "CNY")
    items = data.get("items", [])

    # 解析出发日期
    start_date_str = trip.get("start_date")
    base_date = None
    if start_date_str:
        try:
            base_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # {day -> {category -> [rows]}}
    by_day_cat = defaultdict(lambda: defaultdict(list))
    grand_total = 0.0

    for item in items:
        try:
            amount = float(item["amount"])
        except (KeyError, ValueError, TypeError):
            print(f"[警告] 跳过缺少有效 amount 的记录: {item}", file=sys.stderr)
            continue
        per_person = bool(item.get("per_person", False))
        total_amount = amount * travelers if per_person else amount
        day = item.get("day") or 0
        category = item.get("category", "其他")
        row = dict(item)
        row["total_amount"] = total_amount
        by_day_cat[day][category].append(row)
        grand_total += total_amount

    return {
        "by_day_cat": by_day_cat,
        "grand_total": grand_total,
        "travelers": travelers,
        "currency": currency,
        "base_date": base_date,
    }


def format_markdown(result, trip):
    lines = []
    lines.append("# 预算核算汇总\n")
    lines.append(f"- 路线：{trip.get('origin', '?')} → {trip.get('destination', '?')}")
    lines.append(f"- 出行人数：{result['travelers']} 人")
    lines.append(f"- 货币单位：{result['currency']}")
    lines.append(f"- **总预算：{result['grand_total']:.2f} {result['currency']}**")
    if result["travelers"] > 1:
        per_head = result["grand_total"] / result["travelers"]
        lines.append(f"- 人均预算：{per_head:.2f} {result['currency']}")
    lines.append("")

    base_date = result["base_date"]
    by_day_cat = result["by_day_cat"]

    for d in sorted(by_day_cat.keys(), key=lambda x: (x == 0, x)):
        lbl = day_label(d, base_date)
        day_total = sum(r["total_amount"] for cats in by_day_cat[d].values() for r in cats)
        lines.append(f"## {lbl}\n")
        lines.append("| 类别 | 项目 | 金额 |")
        lines.append("|---|---|---|")
        for cat in sorted(by_day_cat[d].keys()):
            for r in sorted(by_day_cat[d][cat], key=lambda x: x.get("time_start") or "99:99"):
                lines.append(f"| {cat} | {r.get('description', '')} | {r['total_amount']:.2f} |")
        lines.append(f"| **{lbl}小计** | | **{day_total:.2f}** |")
        lines.append("")

    return "\n".join(lines)


def format_html(result, trip):
    parts = []
    parts.append('<div class="budget-summary">')

    # 头部汇总信息
    parts.append(
        f'<p class="budget-meta">路线：{esc(trip.get("origin","?"))} → {esc(trip.get("destination","?"))}'
        f'　|　{result["travelers"]} 人　|　{esc(result["currency"])}</p>'
    )
    parts.append(
        f'<p class="grand-total">总预算：<strong>{result["grand_total"]:.2f} {esc(result["currency"])}</strong>'
    )
    if result["travelers"] > 1:
        per_head = result["grand_total"] / result["travelers"]
        parts.append(f'　人均：<strong>{per_head:.2f} {esc(result["currency"])}</strong>')
    parts.append("</p>")


    base_date = result["base_date"]
    by_day_cat = result["by_day_cat"]

    # 按天展开，天内按类别
    for d in sorted(by_day_cat.keys(), key=lambda x: (x == 0, x)):
        lbl = day_label(d, base_date)
        day_total = sum(r["total_amount"] for cats in by_day_cat[d].values() for r in cats)

        parts.append(f'<div class="budget-day-block">')
        parts.append(f'<h4 class="budget-day-title">{esc(lbl)}</h4>')
        parts.append('<table class="budget-table"><thead><tr><th>类别</th><th>项目</th><th>金额</th></tr></thead><tbody>')

        for cat in sorted(by_day_cat[d].keys()):
            rows = sorted(by_day_cat[d][cat], key=lambda x: x.get("time_start") or "99:99")
            # 类别首行加 rowspan 跨行显示
            rowspan = len(rows)
            first = True
            cat_subtotal = sum(r["total_amount"] for r in rows)
            for r in rows:
                desc = esc(r.get("description", ""))
                amt = f"{r['total_amount']:.2f}"
                if first:
                    cat_td = f'<td class="budget-cat-cell" rowspan="{rowspan}">{esc(cat)}</td>'
                    first = False
                else:
                    cat_td = ""
                parts.append(f"<tr>{cat_td}<td>{desc}</td><td class='budget-amt'>{amt}</td></tr>")

        # 当天小计行
        parts.append(
            f'<tr class="day-subtotal-row"><td colspan="2">📌 {esc(lbl)}小计</td>'
            f'<td class="budget-amt"><strong>{day_total:.2f}</strong></td></tr>'
        )
        parts.append("</tbody></table>")
        parts.append("</div>")

    # 最终汇总
    parts.append('<div class="budget-grand-summary">')
    parts.append(
        f'<p class="grand-total-final">🧾 全程总计：<strong>{result["grand_total"]:.2f} {esc(result["currency"])}</strong></p>'
    )
    if result["travelers"] > 1:
        per_head = result["grand_total"] / result["travelers"]
        parts.append(f'<p class="per-head-final">人均：<strong>{per_head:.2f} {esc(result["currency"])}</strong></p>')
    parts.append("</div>")
    parts.append("</div>")
    return "\n".join(parts)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 budget_calculator.py <trip_data.json> [output.md]")
        sys.exit(1)

    data = json.load(open(sys.argv[1], encoding="utf-8"))
    result = compute(data)
    trip = data.get("trip", {})

    md = format_markdown(result, trip)
    html_fragment = format_html(result, trip)

    out_path = sys.argv[2] if len(sys.argv) > 2 else "budget_summary.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    html_out_path = os.path.splitext(out_path)[0] + ".html"
    with open(html_out_path, "w", encoding="utf-8") as f:
        f.write(html_fragment)

    print(f"[Markdown 已保存到 {out_path}]")
    print(f"[可直接嵌入最终文档的 HTML 片段已保存到 {html_out_path}]")
    print(f"\n[摘要] 总预算：{result['grand_total']:.2f} {result['currency']}", end="")
    if result["travelers"] > 1:
        per_head = result["grand_total"] / result["travelers"]
        print(f"（人均 {per_head:.2f} {result['currency']}）", end="")
    print()
    print("[提示] 完整明细已写入上述文件，如需查看具体每一项金额，用 view 工具读取文件内容。")


if __name__ == "__main__":
    main()
