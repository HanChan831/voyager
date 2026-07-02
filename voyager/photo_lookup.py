#!/usr/bin/env python3
"""
为 trip_data.json 里的真实地点生成 Google Images / Bing Images 图片查询入口。

v9 图片规则：
  - 不再自动取图，只生成搜索入口。
  - 不自动抓取 Google/Bing 搜索结果里的图片，避免误取广告图、缩略图、版权不明图或错误地点图。
  - 只为真实地点生成 Google Images / Bing Images 查询链接。
  - 查询词默认同时保留英文和本地语言；英文优先，本地语言作为第二入口。
  - 默认只给“门票/活动”类景点/地标生成图片搜索入口；住宿、餐饮、交通默认跳过。
  - 人工打开链接确认图片真实、清晰、可用后，再把最终图片地址填写到 photo_url。

用法:
    python3 photo_lookup.py <trip_data.json>

可选:
    --include-food       默认跳过餐饮图片搜索入口，打开后生成餐饮图片搜索入口
    --include-stays      默认跳过住宿图片搜索入口，打开后生成住宿图片搜索入口
    --include-transport  默认跳过交通/机场/租车图片搜索入口，打开后生成交通图片搜索入口
    --include-day0       包含 day=0 的行前事项
    --overwrite          覆盖已有 photo_search_urls / photo_url
"""

import argparse
import json
import os
import re
import urllib.parse

IMG_SEARCH_SOURCES = ("google_images", "bing_images")

MAINLAND_MARKERS = {
    "北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "内蒙古", "广西", "西藏",
    "宁夏", "新疆", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "苏州", "厦门", "青岛", "长沙", "郑州", "昆明",
    "大理", "丽江", "三亚", "桂林", "张家界", "黄山", "拉萨", "哈尔滨", "沈阳", "大连", "济南", "宁波", "无锡",
}
NON_MAINLAND_MARKERS = {
    "香港", "澳门", "澳門", "台湾", "臺灣", "台北", "高雄", "日本", "韩国", "韓國", "朝鲜", "蒙古", "泰国", "新加坡", "马来西亚",
    "印度尼西亚", "越南", "菲律宾", "柬埔寨", "老挝", "缅甸", "印度", "斯里兰卡", "尼泊尔", "马尔代夫", "阿联酋",
    "土耳其", "英国", "法国", "德国", "意大利", "西班牙", "葡萄牙", "瑞士", "奥地利", "荷兰", "比利时", "希腊", "冰岛",
    "挪威", "瑞典", "芬兰", "丹麦", "爱尔兰", "美国", "加拿大", "墨西哥", "巴西", "阿根廷", "智利", "澳大利亚",
    "新西兰", "南非", "埃及", "摩洛哥", "肯尼亚", "Russia", "Iceland", "Japan", "Korea", "Thailand", "Singapore", "United States",
    "USA", "Canada", "France", "Germany", "Italy", "Spain", "United Kingdom", "UK", "Australia", "New Zealand",
}

NON_PLACE_CATEGORIES = {
    "签证/证件", "保险", "旅行保险", "预算", "预算/费用", "证件", "行前准备", "通讯", "换汇", "小费", "税费", "当地交通"
}
NON_PLACE_KEYWORDS = {
    "签证", "visa", "保险", "insurance", "公证", "翻译公证", "预算", "指南", "攻略", "费用", "燃油",
    "油费", "公里税", "自炊食材", "申根旅行保险", "机场简餐", "路上加油站简餐"
}
GENERIC_FOOD_KEYWORDS = {"早餐", "自炊", "简餐", "午餐 - 路上", "晚餐 - 民宿", "超市采购"}
AMBIGUOUS_PATTERNS = [r"\bor\b", r"\bOR\b", r"\s或\s", r" 或", r"或 ", r"\bor\s+", r"\s+or\b"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path")
    parser.add_argument("--include-food", action="store_true")
    parser.add_argument("--include-stays", action="store_true")
    parser.add_argument("--include-transport", action="store_true")
    parser.add_argument("--include-day0", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def infer_mainland_destination(trip):
    raw_fields = [
        trip.get("destination_region"),
        trip.get("destination_area"),
        trip.get("destination_country"),
        trip.get("country"),
        trip.get("destination"),
    ]
    text = " ".join(str(x) for x in raw_fields if x)
    lowered = text.lower()
    if any(token in text for token in ["中国内地以外", "境外", "海外", "港澳台", "非中国内地"]):
        return False
    if any(token in lowered for token in ["outside mainland", "overseas", "non-mainland"]):
        return False
    if "中国内地" in text or "中国大陆" in text or "mainland china" in lowered:
        return True
    if any(marker in text for marker in NON_MAINLAND_MARKERS):
        return False
    country = str(trip.get("destination_country") or trip.get("country") or "")
    if country:
        if any(marker in country for marker in ["香港", "澳门", "澳門", "台湾", "臺灣"]):
            return False
        if country in {"中国", "中华人民共和国", "中国大陆", "中国内地", "China", "PRC"}:
            return True
        return False
    if any(marker in text for marker in MAINLAND_MARKERS):
        return True
    return None


def normalize_space(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def uniq(values):
    out, seen = [], set()
    for value in values:
        if value is None:
            continue
        candidates = value if isinstance(value, (list, tuple)) else [value]
        for candidate in candidates:
            text = normalize_space(candidate)
            if text and text not in seen:
                out.append(text)
                seen.add(text)
    return out


def is_ambiguous_location(text):
    raw = normalize_space(text)
    if not raw:
        return True
    return any(re.search(pattern, raw) for pattern in AMBIGUOUS_PATTERNS)


def skip_reason(item, include_day0=False, include_food=False, include_stays=False, include_transport=False, overwrite=False):
    location = normalize_space(item.get("location"))
    if not location:
        return "无 location 字段"

    if item.get("photo_url") and not overwrite:
        return "已有 photo_url"
    if item.get("photo_search_urls") and not overwrite:
        return "已有图片搜索链接"

    day = item.get("day")
    if not include_day0 and (day == 0 or str(day) == "0"):
        return "day=0 行前事项"

    category = normalize_space(item.get("category"))
    if category in NON_PLACE_CATEGORIES:
        return f"非地点类别：{category}"
    if category == "住宿" and not include_stays:
        return "住宿图片默认跳过"
    if category in {"长途交通", "当地交通", "租车/装备"} and not include_transport:
        return "交通/租车图片默认跳过"
    if category == "餐饮" and not include_food:
        return "餐饮图片默认跳过"
    if category and category not in {"门票/活动", "餐饮", "住宿", "长途交通", "当地交通", "租车/装备"}:
        return f"非默认图片类别：{category}"

    blob = " ".join(
        normalize_space(item.get(k)) for k in ("location", "location_en", "location_local", "address", "description")
        if item.get(k)
    ).lower()
    if any(keyword.lower() in blob for keyword in NON_PLACE_KEYWORDS):
        return "明显不是地点图片对象"
    if category == "餐饮" and any(k in blob for k in GENERIC_FOOD_KEYWORDS):
        return "泛餐饮/自炊项目"
    if is_ambiguous_location(location):
        return "地点不明确，需要人工拆成单一地点"
    return None


def destination_aliases(trip):
    return uniq([
        trip.get("destination_en"),
        trip.get("destination_local"),
        trip.get("destination_country"),
        trip.get("country"),
        trip.get("destination"),
    ])


def search_queries(item, trip):
    """生成图片搜索词：英文优先，本地语言第二，不使用 description。"""
    dest_en = normalize_space(trip.get("destination_en") or trip.get("destination_country") or trip.get("country") or trip.get("destination"))
    dest_local = normalize_space(trip.get("destination_local") or trip.get("destination"))

    en_name = normalize_space(item.get("location_en") or item.get("name_en") or item.get("english_name"))
    local_name = normalize_space(item.get("location_local") or item.get("name_local") or item.get("local_name"))
    readable = normalize_space(item.get("location"))
    address = normalize_space(item.get("address"))

    queries = []
    if en_name:
        if dest_en and dest_en.lower() not in en_name.lower():
            queries.append(f"{en_name} {dest_en}")
        else:
            queries.append(en_name)
    if local_name and local_name != en_name:
        if dest_local and dest_local not in local_name:
            queries.append(f"{local_name} {dest_local}")
        else:
            queries.append(local_name)
    if readable and readable not in {en_name, local_name}:
        if dest_en and dest_en.lower() not in readable.lower():
            queries.append(f"{readable} {dest_en}")
        else:
            queries.append(readable)
    if address:
        queries.append(address)

    return uniq(q for q in queries if len(q) <= 140)[:2]


def build_image_search_urls(query):
    q = urllib.parse.quote(query)
    return {
        "google_images": f"https://www.google.com/search?tbm=isch&q={q}",
        "bing_images": f"https://www.bing.com/images/search?q={q}",
    }


def cache_key(item, trip):
    parts = [
        normalize_space(item.get("location_en")).lower(),
        normalize_space(item.get("location_local")).lower(),
        normalize_space(item.get("location")).lower(),
        normalize_space(trip.get("destination_en") or trip.get("destination")).lower(),
    ]
    return " | ".join(p for p in parts if p)


def apply_search_links(items, queries):
    # queries: 英文优先，本地语言第二。
    urls = {}
    if queries:
        urls["primary"] = build_image_search_urls(queries[0])
    if len(queries) > 1:
        urls["local_language"] = build_image_search_urls(queries[1])

    for item in items:
        item["photo_search_queries"] = queries
        item["photo_search_urls"] = urls
        item["photo_search_note"] = (
            "请优先打开 Google Images 或 Bing Images 人工核对图片。"
            "Bing Images 可作为中国大陆访问相对更方便的备选入口；确认真实、清晰、可用后再把最终图片地址填写到 photo_url。"
        )


def main():
    args = parse_args()
    path = args.json_path

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    trip = data.get("trip", {})
    mainland = infer_mainland_destination(trip)
    region_label = "中国内地" if mainland is True else "中国内地以外" if mainland is False else "未明确"

    groups, skipped = {}, {}
    for item in data.get("items", []):
        reason = skip_reason(
            item,
            include_day0=args.include_day0,
            include_food=args.include_food,
            include_stays=args.include_stays,
            include_transport=args.include_transport,
            overwrite=args.overwrite,
        )
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        key = cache_key(item, trip)
        groups.setdefault(key, []).append(item)

    print(f"📍 目的地区域判断：{region_label}。")
    print("🖼 v9 图片模式：不自动取图；只生成 Google Images + Bing Images 查询入口。")
    if mainland is False:
        print("ℹ️ 接下来会用 Google/Bing 等境外来源入口辅助核对/补充地点图片；Bing 可作为中国大陆访问相对更方便的备选入口。")
    print(f"🖼 待生成图片搜索入口的唯一地点 {len(groups)} 个；跳过项：{sum(skipped.values())} 个。")
    for reason, count in sorted(skipped.items()):
        print(f"   - {reason}: {count}")

    written, no_query = 0, []
    for idx, (key, same_items) in enumerate(groups.items(), 1):
        first = same_items[0]
        location = normalize_space(first.get("location"))
        queries = search_queries(first, trip)
        if not queries:
            no_query.append(location)
            print(f"  ❌ [{idx}/{len(groups)}] {location[:28]}: 无可用英文/本地语言查询词")
            continue
        apply_search_links(same_items, queries)
        written += len(same_items)
        q_preview = " / ".join(queries)
        print(f"  🔎 [{idx}/{len(groups)}] {location[:28]}: {q_preview}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 图片搜索入口生成完成：写入 {written} 个 item。")
    if no_query:
        print("⚠️ 以下地点缺少英文/本地语言查询词，请补 location_en / location_local：")
        for loc in no_query:
            print(f"   - {loc}")


if __name__ == "__main__":
    main()
