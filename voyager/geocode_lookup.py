#!/usr/bin/env python3
"""
按 trip_data.json 给真实地点批量查经纬度坐标。

核心规则：
  - 页面内地图使用在线瓦片渲染，坐标查询统一使用 OpenStreetMap / Nominatim。
  - 只搜索真正的地点字段，不再把 description 当作地点搜索。
  - 默认跳过 day=0 的行前事项、签证/保险/证件/预算/指南类项目。
  - 对重复地点去重；已有 lat/lng 的条目跳过；查询结果写入 geocode_cache.json 复用。
  - 查询名优先使用英文名 + 当地语言名 + 地址 + 少量别名，减少无效请求。

用法:
    python3 geocode_lookup.py <trip_data.json>
可选:
    --delay 1.05        Nominatim 请求间隔，默认 1.05 秒
    --timeout 3         单次请求超时，默认 3 秒
    --max-queries 2     每个唯一地点最多尝试几个查询词，默认 2
    --include-day0      包含 day=0 的行前事项
    --include-food      包含餐饮地点坐标；默认跳过餐饮以加速
    --no-cache          不读取/写入 geocode_cache.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "travel-planner-skill/1.3 (personal-trip-planning; osm-nominatim)"
DEFAULT_TIMEOUT = 3
DEFAULT_DELAY = 1.05
DEFAULT_MAX_QUERIES = 2
CACHE_FILENAME = "geocode_cache.json"

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
    "签证/证件", "保险", "旅行保险", "预算", "预算/费用", "证件", "行前准备", "通讯", "换汇", "小费", "税费"
}
NON_PLACE_KEYWORDS = {
    "签证", "visa", "保险", "insurance", "公证", "翻译公证", "预算", "指南", "攻略", "费用", "燃油",
    "油费", "公里税", "自炊食材", "旅行保险", "申根旅行保险"
}
AMBIGUOUS_PATTERNS = [
    r"\bor\b", r"\bOR\b", r"\s或\s", r" 或", r"或 ", r"\bor\s+", r"\s+or\b"
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-queries", type=int, default=DEFAULT_MAX_QUERIES)
    parser.add_argument("--include-day0", action="store_true")
    parser.add_argument("--include-food", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    return parser.parse_args()


def http_get_json(url, accept_language="en", timeout=DEFAULT_TIMEOUT):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": accept_language,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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


def uniq(values):
    out, seen = [], set()
    for value in values:
        if value is None:
            continue
        candidates = value if isinstance(value, (list, tuple)) else [value]
        for candidate in candidates:
            text = str(candidate).strip()
            if text and text not in seen:
                out.append(text)
                seen.add(text)
    return out


def normalize_space(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def has_valid_coords(item):
    return item.get("lat") is not None and item.get("lng") is not None


def is_ambiguous_location(text):
    raw = normalize_space(text)
    if not raw:
        return True
    return any(re.search(pattern, raw) for pattern in AMBIGUOUS_PATTERNS)


def skip_reason(item, include_day0=False, include_food=False):
    """返回 None 表示应该搜索；否则返回跳过原因。"""
    location = normalize_space(item.get("location"))
    if not location:
        return "无 location 字段"

    if has_valid_coords(item):
        return "已有坐标"

    day = item.get("day")
    if not include_day0 and (day == 0 or str(day) == "0"):
        return "day=0 行前事项"

    category = normalize_space(item.get("category"))
    if category in NON_PLACE_CATEGORIES:
        return f"非地点类别：{category}"
    if category == "餐饮" and not include_food:
        return "餐饮地点默认跳过"

    blob = " ".join(
        normalize_space(item.get(k)) for k in ("location", "location_en", "location_local", "address", "description")
        if item.get(k)
    ).lower()
    if any(keyword.lower() in blob for keyword in NON_PLACE_KEYWORDS):
        return "明显不是旅行地点/地图点"

    if is_ambiguous_location(location):
        return "地点不明确，需要人工拆成单一地点"

    return None


def cache_key(item, trip):
    key_parts = []
    for key in ("address", "location_en", "location_local", "location"):
        key_parts.append(normalize_space(item.get(key)).lower())
    key_parts.append(normalize_space(trip.get("destination_en") or trip.get("destination")).lower())
    return " | ".join(part for part in key_parts if part)


def destination_aliases(trip):
    return uniq([
        trip.get("destination_en"),
        trip.get("destination_local"),
        trip.get("destination_country"),
        trip.get("country"),
        trip.get("destination"),
    ])


def search_names(item, trip, max_queries=DEFAULT_MAX_QUERIES):
    """地点坐标搜索词：英文优先；没查到，立刻用本地语言查。

    不使用 description。默认最多 2 个查询词：
      1. 英文名 + 英文目的地
      2. 本地语言名 + 本地语言目的地
    如果缺少英文名，则用 location 作为英文侧兜底；如果缺少本地语言名，则不重复查询。
    """
    dest_en = normalize_space(trip.get("destination_en") or trip.get("destination_country") or trip.get("country") or trip.get("destination"))
    dest_local = normalize_space(trip.get("destination_local") or trip.get("destination"))

    en_name = normalize_space(item.get("location_en") or item.get("name_en") or item.get("english_name"))
    local_name = normalize_space(item.get("location_local") or item.get("name_local") or item.get("local_name"))
    readable = normalize_space(item.get("location"))
    address = normalize_space(item.get("address"))

    queries = []

    # 英文优先。地址只有在缺少英文名时才作为第一查询，避免 address 挤掉英文/本地双语逻辑。
    english_base = en_name or readable or address
    if english_base:
        if dest_en and dest_en.lower() not in english_base.lower():
            queries.append(f"{english_base}, {dest_en}")
        else:
            queries.append(english_base)

    # 没查到英文时，立刻查本地语言。
    if local_name and local_name not in {en_name, readable}:
        if dest_local and dest_local not in local_name:
            queries.append(f"{local_name}, {dest_local}")
        else:
            queries.append(local_name)

    # 如果英文/本地都没有，才用 address。
    if address and address not in queries and not en_name and not local_name:
        queries.append(address)

    cleaned = []
    for q in uniq(queries):
        q = normalize_space(q)
        if len(q) <= 120:
            cleaned.append(q)
    return cleaned[:max_queries]

def accept_language_header(trip):
    """统一返回英文+本地语言偏好；请求顺序由 search_names 控制。"""
    prefs = ["en"]
    local = trip.get("local_language_code") or trip.get("destination_language_code") or trip.get("osm_accept_language")
    if local:
        if isinstance(local, str):
            prefs.extend(part.strip() for part in local.split(",") if part.strip())
        elif isinstance(local, (list, tuple)):
            prefs.extend(str(x).strip() for x in local if str(x).strip())
    if infer_mainland_destination(trip) is True:
        prefs.extend(["zh-CN", "zh"])
    return ",".join(uniq(prefs))

def nominatim_query(query, accept_language="en", timeout=DEFAULT_TIMEOUT):
    params = urllib.parse.urlencode({
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 0,
        "namedetails": 1,
        "accept-language": accept_language,
    })
    try:
        data = http_get_json(f"{NOMINATIM_URL}?{params}", accept_language=accept_language, timeout=timeout)
        if data:
            first = data[0]
            return {
                "lat": round(float(first["lat"]), 6),
                "lng": round(float(first["lon"]), 6),
                "display_name": first.get("display_name") or query,
            }
    except Exception:
        return None
    return None


def load_cache(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(path, cache):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def apply_coords(items, result, source):
    for item in items:
        item["lat"] = result["lat"]
        item["lng"] = result["lng"]
        item["geocode_source"] = source
        if result.get("display_name"):
            item.setdefault("geocode_display_name", result["display_name"])


def main():
    args = parse_args()
    path = args.json_path
    workspace_dir = os.path.dirname(os.path.abspath(path)) or "."

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    trip = data.get("trip", {})
    mainland = infer_mainland_destination(trip)
    region_label = "中国内地" if mainland is True else "中国内地以外" if mainland is False else "未明确"

    items = data.get("items", [])
    groups = {}
    skipped = {}
    for item in items:
        reason = skip_reason(item, include_day0=args.include_day0, include_food=args.include_food)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        key = cache_key(item, trip)
        groups.setdefault(key, []).append(item)

    cache_path = os.path.join(workspace_dir, CACHE_FILENAME)
    cache = {} if args.no_cache else load_cache(cache_path)

    print(f"📍 目的地区域判断：{region_label}。")
    print("📍 坐标搜索顺序：先用英文名 + 英文目的地；没查到立刻用本地语言名 + 本地语言目的地；不使用 description。")
    if mainland is False:
        print("ℹ️ 接下来会用 OSM/Nominatim 等境外来源核对/补充地点坐标。")
    print(f"📍 默认快模式：每个唯一地点最多 {args.max_queries} 个查询词（英文→本地语言），餐饮默认跳过；唯一地点待查 {len(groups)} 个；跳过项：{sum(skipped.values())} 个。")
    for reason, count in sorted(skipped.items()):
        print(f"   - {reason}: {count}")

    found, cached, not_found = 0, 0, []
    lang_header = accept_language_header(trip)
    total = len(groups)

    for idx, (key, same_items) in enumerate(groups.items(), 1):
        first_item = same_items[0]
        label = normalize_space(first_item.get("location"))[:28]
        if key in cache and cache[key].get("lat") is not None and cache[key].get("lng") is not None:
            apply_coords(same_items, cache[key], "geocode-cache")
            cached += len(same_items)
            print(f"  ♻️ [{idx}/{total}] {label}: 使用缓存")
            continue

        queries = search_names(first_item, trip, max_queries=max(1, args.max_queries))
        result = None
        used_query = None
        print(f"  🔍 [{idx}/{total}] {label}...", end="", flush=True)
        for q_index, query in enumerate(queries, 1):
            result = nominatim_query(query, accept_language=lang_header, timeout=args.timeout)
            if result:
                used_query = query
                break
            if q_index < len(queries):
                time.sleep(max(0, args.delay))

        if result:
            result["query"] = used_query
            cache[key] = result
            apply_coords(same_items, result, f"osm-nominatim:{lang_header}")
            found += len(same_items)
            print(f"\r  ✅ [{idx}/{total}] {label}: {result['lat']}, {result['lng']}（{used_query}）")
        else:
            not_found.append(label)
            print(f"\r  ❌ [{idx}/{total}] {label}: 未找到坐标")
        time.sleep(max(0, args.delay))

    if not args.no_cache:
        save_cache(cache_path, cache)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 坐标查询完成：新增/复用到 {found + cached} 个 item；其中缓存命中 {cached} 个。")
    if not_found:
        print("⚠️ 以下唯一地点仍未找到坐标，请补充英文名/本地语言名/完整地址，或手动填写 lat/lng：")
        for loc in not_found:
            print(f"   - {loc}")


if __name__ == "__main__":
    main()
