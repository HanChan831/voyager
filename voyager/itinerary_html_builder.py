#!/usr/bin/env python3
"""
读取 trip_data.json，按天整理出按时间排序的行程：
  - 在时间轴上方生成一张 Google 无 API 懒加载互动地图：
      * 不需要 Google API Key
      * 默认不自动加载 iframe，避免拖慢页面或被浏览器嵌入策略拦截
      * 按用户选择的租车/公共交通判断驾车或公共交通路线
  - 为每一段相邻的、都填了 location 的行程生成外部地图 App 的导航跳转链接，
    平台依据 trip.nav_map_provider（可以是高德/百度/Google/Apple/不要）
  - 如果 trip.start_date 是合法日期，给每个有时间的行程项生成"加入日历"按钮，
    并把整个行程合并导出成 trip_calendar.ics（细节见 calendar_notes.md）
  - 给带 booking_platform 的项目生成预订平台链接
  - 给每个有 location 的行程项，按是否有 photo_url 生成真实照片缩略图
  - 额外生成一份独立的 places_gallery.html，把行程里所有不重复的地点汇总成卡片
    （照片+评分+点评摘要+配套服务），对应第12步要填的"地点图鉴"标签页

用法:
    python3 itinerary_html_builder.py <trip_data.json> [output.html] [output.ics] [gallery.html]
"""

import base64
import json
import html
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MODE_LABELS = {"driving": "驾车", "walking": "步行", "transit": "公交/地铁", "taxi": "打车"}

# 类别 → 地图标记颜色
CATEGORY_COLORS = {
    "长途交通": "#e74c3c",
    "当地交通": "#e67e22",
    "住宿":     "#27ae60",
    "门票/活动": "#2980b9",
    "餐饮":     "#f39c12",
    "租车/装备": "#8e44ad",
}
DEFAULT_COLOR = "#7f8c8d"

PLATFORM_HOMEPAGES = {
    "携程": "https://www.ctrip.com",
    "飞猪": "https://www.fliggy.com",
    "去哪儿": "https://www.qunar.com",
    "同程": "https://www.ly.com",
    "美团": "https://www.meituan.com",
    "大众点评": "https://www.dianping.com",
    "Booking.com": "https://www.booking.com",
    "Airbnb": "https://www.airbnb.cn",
    "Agoda": "https://www.agoda.com",
    "Expedia": "https://www.expedia.com",
}


def esc(value):
    return html.escape(str(value), quote=True)


def to_minutes(t):
    try:
        h, m = map(int, str(t).split(":"))
        return h * 60 + m
    except Exception:
        return 0



# ---------------------------------------------------------------------------
# 出行交通方式
# ---------------------------------------------------------------------------

def infer_default_transport_mode(trip):
    """根据用户在开头选择的租车/公共交通推断默认路线模式。"""
    raw_values = [
        trip.get("transport_mode"),
        trip.get("travel_mode"),
        trip.get("primary_transport_mode"),
        trip.get("local_transport_mode"),
        trip.get("route_mode"),
        trip.get("self_drive"),
        trip.get("rental_car"),
        trip.get("rent_car"),
        trip.get("car_rental"),
    ]
    text = " ".join(str(v) for v in raw_values if v is not None).lower()

    if any(token in text for token in ["公共交通", "公交", "地铁", "火车", "巴士", "大巴", "bus", "metro", "train", "public", "transit"]):
        return "transit"
    if any(token in text for token in ["步行", "walk", "walking"]):
        return "walking"
    if any(token in text for token in ["打车", "出租车", "网约车", "taxi", "ridehail"]):
        return "taxi"
    if any(token in text for token in ["租车", "自驾", "驾车", "开车", "car", "drive", "driving", "self-drive", "self drive", "road trip", "true", "yes", "1"]):
        return "driving"
    return "driving"


def google_travel_mode(mode):
    return {"driving": "driving", "walking": "walking", "transit": "transit", "taxi": "driving"}.get(mode or "driving", "driving")


def google_place_query(item, trip=None):
    """Google Maps 查询词。优先英文名，缺少时用 location；自动追加目的地减少歧义。"""
    trip = trip or {}
    name = (
        item.get("location_en")
        or item.get("name_en")
        or item.get("english_name")
        or item.get("location")
        or item.get("location_local")
        or item.get("name_local")
        or item.get("local_name")
        or ""
    )
    name = str(name).strip()
    destination = str(trip.get("destination_en") or trip.get("destination_country") or trip.get("country") or trip.get("destination") or "").strip()
    if destination and destination.lower() not in name.lower():
        return f"{name}, {destination}"
    return name


def google_directions_url(places, mode="driving", embed=False):
    """无 API Google Directions URL。embed=True 仅用于用户点击后的 iframe 尝试。

    部分浏览器或 Google 页面可能拒绝 iframe 嵌入，所以页面必须保留新窗口打开链接。
    """
    clean = [p for p in places if p]
    if not clean:
        return ""
    if len(clean) == 1:
        base = f"https://www.google.com/maps?q={quote(clean[0])}"
        return base + ("&output=embed" if embed else "")
    origin, destination = clean[0], clean[-1]
    waypoints = "|".join(clean[1:-1])
    url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={quote(origin)}"
        f"&destination={quote(destination)}"
        f"&travelmode={google_travel_mode(mode)}"
    )
    if waypoints:
        url += f"&waypoints={quote(waypoints)}"
    if embed:
        url += "&output=embed"
    return url



def google_search_embed_url(query):
    """第一版 Google 无 API iframe：只做地点/区域搜索，不嵌入 Directions 路线页。"""
    q = str(query or "").strip()
    if not q:
        q = "Google Maps"
    return f"https://www.google.com/maps?q={quote(q)}&output=embed"


def google_focus_query(places, trip):
    """生成页面内 Google iframe 的搜索词。

    用第一版方案：把当天核心地点 + 目的地拼成搜索词，而不是把 Directions 路线页嵌入 iframe。
    这样比 /maps/dir 页面更不容易被 Zen/浏览器拦截。
    """
    names = []
    for p in places[:5]:
        if p and p not in names:
            names.append(p)
    destination = str(trip.get("destination_en") or trip.get("destination_country") or trip.get("country") or trip.get("destination") or "").strip()
    if destination and destination not in " ".join(names):
        names.append(destination)
    return " ".join(names[:6])


def collect_day_routes(items, trip):
    """按天收集路线地点，用于 Google 懒加载地图。"""
    by_day = defaultdict(list)
    for it in items:
        day = it.get("day")
        loc = it.get("location")
        if day is None or day == "" or not loc:
            continue
        try:
            day_key = int(day)
        except Exception:
            continue
        by_day[day_key].append(it)

    default_mode = infer_default_transport_mode(trip)
    routes = []
    for day in sorted(by_day):
        day_items = sorted(by_day[day], key=lambda x: to_minutes(x.get("time_start", "00:00")))
        places = []
        place_cards = []
        last_query = None
        segment_modes = []
        for idx, it in enumerate(day_items):
            q = google_place_query(it, trip)
            if not q or q == last_query:
                continue
            places.append(q)
            place_cards.append({
                "label": it.get("location") or q,
                "query": q,
                "category": it.get("category", ""),
                "time": it.get("time_start", ""),
            })
            last_query = q
            if idx > 0:
                segment_modes.append(it.get("transport_mode_from_prev"))

        if not places:
            continue

        # 一天只能给 Google Directions 一个整体 travelmode。
        # 若行程段单独写了 walking/transit/driving，则优先第一个有效段；否则使用用户全局选择。
        mode = default_mode
        for m in segment_modes:
            if m in {"driving", "walking", "transit", "taxi"}:
                mode = m
                break

        title = f"Day {day}"
        desc_parts = [it.get("description", "") for it in day_items if it.get("description")]
        if desc_parts:
            title += "｜" + str(desc_parts[0])[:28]

        routes.append({
            "day": day,
            "title": title,
            "mode": google_travel_mode(mode),
            "mode_label": MODE_LABELS.get(mode, mode),
            "places": place_cards,
            "iframe_url": google_search_embed_url(google_focus_query(places, trip)),
            "embed_query": google_focus_query(places, trip),
            "external_url": google_directions_url(places, mode, embed=False),
            "summary": " → ".join(p["label"] for p in place_cards[:8]) + (" → ..." if len(place_cards) > 8 else ""),
        })
    return routes


# ---------------------------------------------------------------------------
# 导航跳转链接（点击打开外部地图 App）
# ---------------------------------------------------------------------------

def build_nav_link(provider, origin, destination, mode="driving"):
    if provider == "none" or not provider:
        return None
    origin_name = origin.get("location", "")
    dest_name = destination.get("location", "")
    if not origin_name or not dest_name:
        return None
    o_lat, o_lng = origin.get("lat"), origin.get("lng")
    d_lat, d_lng = destination.get("lat"), destination.get("lng")
    label = f"{origin_name} → {dest_name}（{MODE_LABELS.get(mode, mode)}）"

    if provider == "google":
        gmode = {"driving": "driving", "walking": "walking", "transit": "transit", "taxi": "driving"}.get(mode, "driving")
        url = f"https://www.google.com/maps/dir/?api=1&origin={quote(origin_name)}&destination={quote(dest_name)}&travelmode={gmode}"
        return url, label

    if provider == "apple":
        amode = {"driving": "d", "walking": "w", "transit": "r", "taxi": "d"}.get(mode, "d")
        url = f"http://maps.apple.com/?saddr={quote(origin_name)}&daddr={quote(dest_name)}&dirflg={amode}"
        return url, label

    if provider == "amap":
        amap_mode = {"driving": "car", "walking": "walk", "transit": "bus", "taxi": "car"}.get(mode, "car")
        if o_lat and o_lng and d_lat and d_lng:
            url = (f"https://uri.amap.com/navigation?from={o_lng},{o_lat},{quote(origin_name)}"
                   f"&to={d_lng},{d_lat},{quote(dest_name)}&mode={amap_mode}&policy=1&src=travel-planner&coordinate=gaode&callnative=1")
        else:
            url = f"https://www.amap.com/search?query={quote(dest_name)}"
        return url, label

    if provider == "baidu":
        baidu_mode = {"driving": "driving", "walking": "walking", "transit": "transit", "taxi": "driving"}.get(mode, "driving")
        if o_lat and o_lng and d_lat and d_lng:
            origin_param, dest_param = f"{o_lat},{o_lng}", f"{d_lat},{d_lng}"
        else:
            origin_param, dest_param = f"name:{origin_name}", f"name:{dest_name}"
        url = (f"https://api.map.baidu.com/direction?origin={quote(origin_param)}&destination={quote(dest_param)}"
               f"&mode={baidu_mode}&output=html&src=travel-planner")
        return url, label

    return None


# ---------------------------------------------------------------------------
# 交互式在线地图（Leaflet + OpenStreetMap）
# ---------------------------------------------------------------------------

def collect_geo_items(items):
    """收集所有已有坐标的行程项。

    地图标记不再要求 day / time_start；只要 item 有有效 lat/lng，
    就应该出现在页面内的 Leaflet 在线地图上。
    这样住宿、机场、租车点、备用餐厅、行前地点等没有具体时间的地点也不会被漏掉。
    """
    geo_items = []
    for it in items:
        lat = it.get("lat")
        lng = it.get("lng")
        if lat is None or lng is None:
            continue
        try:
            it["lat"] = float(lat)
            it["lng"] = float(lng)
        except (TypeError, ValueError):
            continue
        geo_items.append(it)
    return geo_items


def build_no_coords_map():
    return (
        '<div class="map-no-coords">'
        '🗺️ 暂无地图坐标数据——在 <code>trip_data.json</code> 中为各地点填写 <code>lat</code> / <code>lng</code> 字段后，重新运行脚本即可显示交互式地图。'
        '</div>'
    )


def map_points_and_legend(items):
    geo_items = collect_geo_items(items)
    if not geo_items:
        return [], ""

    points = []
    shown_cats = {}
    for idx, it in enumerate(geo_items):
        color = CATEGORY_COLORS.get(it.get("category", ""), DEFAULT_COLOR)
        cat = it.get("category", "其他")
        shown_cats.setdefault(cat, color)
        points.append({
            "id": f"p{idx}",
            "lat": it["lat"],
            "lng": it["lng"],
            "name": it.get("location", ""),
            "cat": cat,
            "day": it.get("day", 0),
            "color": color,
        })

    legend_items = ""
    for cat, color in shown_cats.items():
        legend_items += (
            f'<span class="map-legend-item">'
            f'<span class="map-legend-dot" style="background:{color}"></span>{esc(cat)}'
            f'</span>'
        )
    return points, legend_items




def google_route_url_for_points(points, mode="driving"):
    '''用坐标生成新窗口 Google Maps 路线链接；不嵌入 iframe。'''
    clean = [p for p in points if p.get("lat") is not None and p.get("lng") is not None]
    if not clean:
        return "#"
    if len(clean) == 1:
        return f"https://www.google.com/maps?q={quote(str(clean[0]['lat']) + ',' + str(clean[0]['lng']))}"
    origin = f"{clean[0]['lat']},{clean[0]['lng']}"
    destination = f"{clean[-1]['lat']},{clean[-1]['lng']}"
    url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={quote(origin)}"
        f"&destination={quote(destination)}"
        f"&travelmode={google_travel_mode(mode)}"
    )
    if len(clean) > 2:
        waypoints = "|".join(f"{p['lat']},{p['lng']}" for p in clean[1:-1])
        url += f"&waypoints={quote(waypoints)}"
    return url


def build_leaflet_esri_map(items, trip):
    '''Leaflet + Esri/ArcGIS 底图 + 自绘 marker/路线。

    不使用 Google iframe，不依赖 OSM 官方瓦片。marker 与每日路线线条由页面自己绘制，
    因此“全部 / Day X”都会稳定显示所有有坐标的地点。路线规划和路程时间仍通过
    新窗口 Google Maps 打开。
    '''
    geo_items = collect_geo_items(items)
    if not geo_items:
        return build_no_coords_map()

    day_colors = ["#2563eb", "#7c3aed", "#0f766e", "#d97706", "#dc2626", "#0891b2", "#4b5563", "#be185d"]
    day_color_map = {}

    def day_key(value):
        try:
            return int(value)
        except Exception:
            return 0

    geo_items = sorted(
        geo_items,
        key=lambda it: (day_key(it.get("day")), to_minutes(it.get("time_start", "00:00")))
    )

    all_points = []
    day_groups = defaultdict(list)
    day_order_counter = defaultdict(int)

    for idx, it in enumerate(geo_items):
        day = day_key(it.get("day"))
        day_order_counter[day] += 1
        if day not in day_color_map:
            day_color_map[day] = day_colors[len(day_color_map) % len(day_colors)]

        name = it.get("location") or it.get("location_en") or it.get("description") or f"地点 {idx + 1}"
        point = {
            "id": f"p{idx}",
            "day": day,
            "order": day_order_counter[day],
            "time": it.get("time_start", ""),
            "label": name,
            "name": it.get("location_en") or it.get("location_local") or name,
            "cat": it.get("category", "其他"),
            "lat": float(it["lat"]),
            "lng": float(it["lng"]),
            "color": day_color_map[day],
        }
        all_points.append(point)
        day_groups[day].append(point)

    default_mode = infer_default_transport_mode(trip)

    views = [{
        "key": "all",
        "label": "全部",
        "title": "全部｜全行程地点",
        "subtitle": f"{len(all_points)} 个地点",
        "places": all_points,
        "route_url": google_route_url_for_points(all_points, default_mode),
    }]

    for day in sorted(day_groups):
        if day <= 0:
            continue
        places = day_groups[day]
        mode = default_mode
        for it in geo_items:
            if day_key(it.get("day")) == day and it.get("transport_mode_from_prev") in {"driving", "walking", "transit", "taxi"}:
                mode = it.get("transport_mode_from_prev")
                break
        title_tail = places[0].get("label", "")
        views.append({
            "key": f"day{day}",
            "label": f"Day {day}",
            "title": f"Day {day}｜{title_tail}",
            "subtitle": f"{len(places)} 个地点 · {MODE_LABELS.get(mode, mode)}",
            "places": places,
            "route_url": google_route_url_for_points(places, mode),
        })

    views_js = json.dumps(views, ensure_ascii=False)
    first = views[0]

    tab_html = []
    for idx, view in enumerate(views):
        tab_html.append(
            f'<button class="leaflet-day-tab{" active" if idx == 0 else ""}" onclick="tripLeafletShowView({idx})">'
            f'<strong>{esc(view["label"])}</strong><span>{esc(view["subtitle"])}</span></button>'
        )

    return f'''<section class="leaflet-esri-map" id="trip-map-wrap">
  <div class="leaflet-map-head">
    <div>
      <strong id="leaflet-map-title">🗺 {esc(first["title"])}</strong>
      <span id="leaflet-map-subtitle">{esc(first["subtitle"])} · marker 和路线由页面自己绘制</span>
    </div>
    <a id="leaflet-route-link" href="{esc(first["route_url"])}" target="_blank" rel="noopener">新窗口打开路线</a>
  </div>
  <div class="leaflet-day-tabs">
    {''.join(tab_html)}
  </div>
  <div class="leaflet-layout">
    <div class="leaflet-map-area">
      <div class="leaflet-title-row">
        <strong id="leaflet-current-title">{esc(first["title"])}</strong>
        <span id="leaflet-current-count">{len(first["places"])} 个地点</span>
      </div>
      <div id="trip-leaflet-map" class="trip-leaflet-map"></div>
      <div id="leaflet-map-warning" class="leaflet-map-warning" hidden>地图底图加载失败时，marker 数据仍在右侧列表中；可点击“新窗口打开路线”。</div>
    </div>
    <aside class="leaflet-map-side">
      <h4 id="leaflet-list-title">{esc(first["title"])}</h4>
      <ol id="leaflet-place-list" class="leaflet-place-list"></ol>
    </aside>
  </div>
</section>
<script>
(function() {{
  var views = {views_js};
  var map = null;
  var layerGroup = null;
  var markers = [];
  var initialized = false;
  var currentViewIndex = 0;
  var pendingViewIndex = 0;
  var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function escapeHtml(value) {{
    return String(value || '').replace(/[&<>"']/g, function(ch) {{
      return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch];
    }});
  }}

  function markerText(point, index, total) {{
    if (total > 26 && point.day) return 'D' + point.day;
    return index < letters.length ? letters.charAt(index) : String(index + 1);
  }}

  function mapContainerIsReady() {{
    var el = document.getElementById('trip-leaflet-map');
    if (!el) return false;
    var rect = el.getBoundingClientRect();
    return rect.width > 160 && rect.height > 160 && el.offsetParent !== null;
  }}

  function ensureMap() {{
    if (initialized) return true;
    if (!mapContainerIsReady()) return false;
    if (typeof L === 'undefined') {{
      var warn = document.getElementById('leaflet-map-warning');
      if (warn) warn.hidden = false;
      return false;
    }}
    map = L.map('trip-leaflet-map', {{
      preferCanvas: true,
      zoomAnimation: false,
      markerZoomAnimation: false,
      inertia: false
    }}).setView([0, 0], 2);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Tiles &copy; Esri, TomTom, Garmin, FAO, NOAA, USGS, &copy; OpenStreetMap contributors, and the GIS User Community',
      maxZoom: 18,
      updateWhenIdle: true,
      updateWhenZooming: false,
      keepBuffer: 2
    }}).on('tileerror', function() {{
      var warn = document.getElementById('leaflet-map-warning');
      if (warn) warn.hidden = false;
    }}).addTo(map);

    layerGroup = L.layerGroup().addTo(map);
    initialized = true;
    return true;
  }}

  function refreshLeafletSize() {{
    if (!initialized || !map) return;
    [60, 180, 360, 720].forEach(function(delay) {{
      setTimeout(function() {{
        map.invalidateSize(true);
        map.eachLayer(function(layer) {{
          if (layer && layer.redraw) layer.redraw();
        }});
      }}, delay);
    }});
  }}

  function makeIcon(point, index, total) {{
    var label = markerText(point, index, total);
    return L.divIcon({{
      html: '<div class="leaflet-pin-marker" style="background:' + point.color + '">' + label + '</div>',
      className: '',
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -16]
    }});
  }}

  function renderList(view) {{
    var html = '';
    view.places.forEach(function(point, index) {{
      var label = markerText(point, index, view.places.length);
      html += '<li onclick="tripLeafletFocusPlace(' + index + ')">' +
        '<span class="leaflet-list-pin" style="background:' + point.color + '">' + label + '</span>' +
        '<div><strong>' + escapeHtml(point.label) + '</strong>' +
        '<small><em>Day ' + escapeHtml(point.day) + '</em>' + escapeHtml(point.time) + ' · ' + escapeHtml(point.cat) + '</small></div>' +
        '</li>';
    }});
    var list = document.getElementById('leaflet-place-list');
    if (list) list.innerHTML = html;
  }}

  window.tripLeafletShowView = function(index) {{
    currentViewIndex = index || 0;
    pendingViewIndex = currentViewIndex;
    var view = views[index] || views[0];

    document.getElementById('leaflet-map-title').textContent = '🗺 ' + view.title;
    document.getElementById('leaflet-map-subtitle').textContent = view.subtitle + ' · marker 和路线由页面自己绘制';
    document.getElementById('leaflet-current-title').textContent = view.title;
    document.getElementById('leaflet-current-count').textContent = view.places.length + ' 个地点';
    document.getElementById('leaflet-list-title').textContent = view.title;
    document.getElementById('leaflet-route-link').href = view.route_url;

    document.querySelectorAll('.leaflet-day-tab').forEach(function(btn, i) {{
      btn.classList.toggle('active', i === index);
    }});

    renderList(view);

    if (!ensureMap()) return;
    refreshLeafletSize();
    layerGroup.clearLayers();
    markers = [];

    var latlngs = [];
    view.places.forEach(function(point, i) {{
      var latlng = [point.lat, point.lng];
      var marker = L.marker(latlng, {{icon: makeIcon(point, i, view.places.length)}})
        .bindPopup('<strong>' + escapeHtml(point.label) + '</strong><br>Day ' + escapeHtml(point.day) + ' · ' + escapeHtml(point.time) + '<br>' + escapeHtml(point.cat));
      marker.addTo(layerGroup);
      markers.push(marker);
      latlngs.push(latlng);
    }});

    var byDay = {{}};
    view.places.forEach(function(point) {{
      if (!byDay[point.day]) byDay[point.day] = [];
      byDay[point.day].push(point);
    }});
    Object.keys(byDay).forEach(function(day) {{
      var pts = byDay[day];
      if (pts.length > 1) {{
        L.polyline(pts.map(function(p) {{ return [p.lat, p.lng]; }}), {{
          color: pts[0].color,
          weight: 3,
          opacity: 0.78
        }}).addTo(layerGroup);
      }}
    }});

    refreshLeafletSize();
    if (latlngs.length === 1) {{
      map.setView(latlngs[0], 12);
    }} else if (latlngs.length > 1) {{
      map.fitBounds(latlngs, {{padding: [35, 35], maxZoom: index === 0 ? 8 : 12}});
    }}
    refreshLeafletSize();
  }};

  window.tripLeafletFocusPlace = function(index) {{
    if (!ensureMap()) return;
    var marker = markers[index];
    if (marker) {{
      map.setView(marker.getLatLng(), 12);
      marker.openPopup();
    }}
  }};

  window.tripLeafletRefreshMap = function() {{
    var index = pendingViewIndex || currentViewIndex || 0;
    if (!mapContainerIsReady()) {{
      [120, 300, 700, 1200].forEach(function(delay) {{
        setTimeout(function() {{
          if (mapContainerIsReady()) window.tripLeafletRefreshMap();
        }}, delay);
      }});
      return;
    }}
    window.tripLeafletShowView(index);
    refreshLeafletSize();
  }};

  if ('ResizeObserver' in window) {{
    var mapElForResize = document.getElementById('trip-leaflet-map');
    if (mapElForResize) {{
      var ro = new ResizeObserver(function() {{
        window.tripLeafletRefreshMap();
      }});
      ro.observe(mapElForResize);
    }}
  }}

  if ('IntersectionObserver' in window) {{
    var wrapEl = document.getElementById('trip-map-wrap');
    var observer = new IntersectionObserver(function(entries) {{
      entries.forEach(function(entry) {{
        if (entry.isIntersecting) {{
          window.tripLeafletRefreshMap();
        }}
      }});
    }}, {{threshold: 0.05}});
    if (wrapEl) observer.observe(wrapEl);
  }}

  window.tripMapShowAll = function() {{}};
  window.tripMapShowSegment = function(fLat, fLng, tLat, tLng, el) {{
    if (el) el.classList.add('map-active');
    var wrap = document.getElementById('trip-map-wrap');
    if (wrap) wrap.scrollIntoView({{behavior:'smooth', block:'nearest'}});
  }};

  renderList(views[0]);
  [80, 250, 650, 1200].forEach(function(delay) {{ setTimeout(window.tripLeafletRefreshMap, delay); }});
}})();
</script>'''


def build_online_map(items, trip):
    # Leaflet + Esri/ArcGIS 底图：marker/路线由页面自己绘制，保证全部和每日地点都能显示。
    return build_leaflet_esri_map(items, trip)


# ---------------------------------------------------------------------------
# 地点图鉴
# ---------------------------------------------------------------------------



def gallery_search_query(item):
    """为图鉴生成查询词。优先英文/本地名，自动补目的地减少歧义。"""
    name = (
        item.get("location_en")
        or item.get("name_en")
        or item.get("english_name")
        or item.get("location")
        or item.get("location_local")
        or item.get("name_local")
        or ""
    )
    dest = (
        item.get("country")
        or item.get("destination_country")
        or item.get("destination")
        or ""
    )
    query = str(name).strip()
    if dest and str(dest).lower() not in query.lower():
        query = f"{query} {dest}"
    return query.strip() or str(item.get("location", "")).strip()


def booking_search_url(query):
    """Booking 搜索兜底。用于缺失评分/评价时人工核对，不作为自动结构化抓取。"""
    return "https://www.booking.com/searchresults.html?ss=" + quote(query)


def agoda_search_url(query):
    """Agoda 搜索兜底。用于缺失评分/评价时人工核对，不作为自动结构化抓取。"""
    return "https://www.agoda.com/search?textToSearch=" + quote(query)


def bing_thumbnail_url(query):
    """图片缩略图兜底。不是结构化 API，只作为视觉预览；最终可手动替换为 photo_url。"""
    return "https://tse1.mm.bing.net/th?q=" + quote(query) + "&w=800&h=500&c=7&rs=1&p=0"


def build_places_gallery(items):
    """地点图鉴。

    真实字段优先：
    - 有 photo_url：直接显示真实图片。
    - 没 photo_url：显示图片搜索缩略图预览，不再放 Google/Bing 图片按钮。
    - 有 rating：直接显示评分。
    - 没 rating：只显示 fallback 补填提示，不显示外部查询按钮。
    - 有 review_summary：直接显示评价摘要。
    - 没 review_summary：只显示 fallback 补填提示，不显示外部查询按钮。
    """
    seen = set()
    cards = []
    for it in items:
        loc = it.get("location") or it.get("location_en") or it.get("name_en")
        if not loc or loc in seen:
            continue
        seen.add(loc)

        query = gallery_search_query(it)
        booking_url = booking_search_url(query)
        agoda_url = agoda_search_url(query)

        photo_url = it.get("photo_url") or it.get("image_url") or it.get("thumbnail_url")
        if photo_url:
            photo_html = f'<img class="place-photo" src="{esc(photo_url)}" alt="{esc(loc)}照片" loading="lazy">'
            photo_source = it.get("photo_source")
            if photo_source:
                photo_html += f'<div class="place-photo-caption">图片来源：{esc(photo_source)}</div>'
        else:
            thumb = bing_thumbnail_url(query)
            photo_html = (
                '<div class="place-photo-fallback">'
                f'<img class="place-photo" src="{esc(thumb)}" alt="{esc(loc)}图片预览" loading="lazy" '
                'onerror="this.closest(\'.place-photo-fallback\').classList.add(\'image-failed\')">'
                '<div class="place-photo-placeholder gallery-search-placeholder">'
                '<div class="gallery-placeholder-icon">🖼️</div>'
                '<strong>图片预览加载失败</strong>'
                '<span>可以手动补充稳定图片地址到 <code>photo_url</code></span>'
                '</div>'
                '</div>'
            )

        rating = it.get("rating")
        if rating is not None and rating != "":
            bits = [f"⭐ {esc(rating)}"]
            detail = []
            if it.get("rating_count") is not None and it.get("rating_count") != "":
                detail.append(f"{esc(it['rating_count'])}条评价")
            if it.get("rating_source"):
                detail.append(esc(it["rating_source"]))
            if detail:
                bits.append(f"（{' · '.join(detail)}）")
            rating_html = f'<div class="place-rating">{"".join(bits)}</div>'
        else:
            rating_html = ""

        review = it.get("review_summary")
        if review:
            review_html = f'<p class="place-review">{esc(review)}</p>'
        else:
            review_html = ""

        services = it.get("services")
        services_html = ""
        if services:
            svc_items = "".join(f"<li>{esc(s)}</li>" for s in services)
            services_html = (
                '<div class="place-services"><div class="place-services-title">🛎️ 配套服务</div>'
                f"<ul>{svc_items}</ul></div>"
            )

        meta_bits = []
        if it.get("category"):
            meta_bits.append(esc(it["category"]))
        if it.get("day"):
            meta_bits.append(f"第{it['day']}天")
        if it.get("location_en") and it.get("location_en") != loc:
            meta_bits.append(esc(it["location_en"]))
        meta_html = f'<div class="place-meta">{" · ".join(meta_bits)}</div>' if meta_bits else ""

        cards.append(
            '<div class="place-card">'
            f'<div class="place-photo-wrap">{photo_html}</div>'
            '<div class="place-info">'
            f'<h4 class="place-name">{esc(loc)}</h4>'
            f"{meta_html}{rating_html}{review_html}{services_html}"
            "</div></div>"
        )

    if not cards:
        return ""
    return '<div class="gallery-notice">图鉴采用“有数据才显示”：有图片/评分/评价就展示，缺失字段直接跳过，不显示未抓取提示。</div><div class="places-gallery">' + "".join(cards) + "</div>"


# ---------------------------------------------------------------------------
# iCalendar 工具
# ---------------------------------------------------------------------------

def ics_escape(text):
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold_line(line, limit=73):
    if len(line.encode("utf-8")) <= limit:
        return line
    out, current = [], ""
    for ch in line:
        if len((current + ch).encode("utf-8")) > limit:
            out.append(current)
            current = " " + ch
        else:
            current += ch
    out.append(current)
    return "\r\n".join(out)


def build_vevent(uid, dtstart, dtend, summary, location="", description=""):
    lines = [
        "BEGIN:VEVENT", f"UID:{uid}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(summary)}",
    ]
    if location:
        lines.append(f"LOCATION:{ics_escape(location)}")
    if description:
        lines.append(f"DESCRIPTION:{ics_escape(description)}")
    lines.append("END:VEVENT")
    return "\r\n".join(fold_line(l) for l in lines)


def build_vcalendar(vevent_texts, calname="我的行程"):
    header = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//travel-planner//trip//CN",
              "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{ics_escape(calname)}"]
    return "\r\n".join(header) + "\r\n" + "\r\n".join(vevent_texts) + "\r\nEND:VCALENDAR"


def ics_data_uri(ics_text):
    b64 = base64.b64encode(ics_text.encode("utf-8")).decode("ascii")
    return f"data:text/calendar;charset=utf-8;base64,{b64}"


def day_to_date(day, base_date):
    if base_date is None or not day:
        return None
    return base_date + timedelta(days=int(day) - 1)


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 完整 HTML 模板渲染
# ---------------------------------------------------------------------------

def render_overview(trip, items):
    days = sorted({it.get("day") for it in items if it.get("day") not in (None, "")})
    located = sum(1 for it in items if it.get("location"))
    currency = trip.get("currency", "")
    transport = infer_default_transport_mode(trip)
    transport_label = MODE_LABELS.get(transport, transport)
    title = f"{trip.get('origin','')} → {trip.get('destination','')}".strip(" →")
    if not title:
        title = trip.get("destination", "旅行计划")
    return (
        '<div class="overview-grid">'
        f'<div class="overview-card"><strong>目的地</strong><span>{esc(trip.get("destination", ""))}</span></div>'
        f'<div class="overview-card"><strong>天数</strong><span>{len(days)} 天</span></div>'
        f'<div class="overview-card"><strong>地点</strong><span>{located} 个行程地点</span></div>'
        f'<div class="overview-card"><strong>交通</strong><span>{esc(transport_label)}</span></div>'
        f'<div class="overview-card"><strong>货币</strong><span>{esc(currency or "未设置")}</span></div>'
        '</div>'
        '<p class="lede">这是由 travel-planner skill 生成的完整样式示例。页面内 Google 地图使用第一版搜索地图 iframe；每日路线、路程和预计时间通过新窗口 Google Maps 查看。</p>'
    )


def render_fieldrow(trip):
    fields = [
        ("出发地", trip.get("origin", "")),
        ("目的地", trip.get("destination", "")),
        ("出发日期", trip.get("start_date", "")),
        ("交通方式", MODE_LABELS.get(infer_default_transport_mode(trip), infer_default_transport_mode(trip))),
        ("货币", trip.get("currency", "")),
    ]
    return "".join(
        f'<div class="field"><span>{esc(label)}</span><strong>{esc(value or "—")}</strong></div>'
        for label, value in fields
    )


def render_full_page(trip, itinerary_html, gallery_html=""):
    """把 itinerary_blocks 片段套进 trip_template.html，生成完整带样式页面。"""
    template_path = "trip_template.html"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        return itinerary_html

    items_placeholder = {
        "TITLE": f'{trip.get("destination", "旅行")}行程计划',
        "FIELDROW": render_fieldrow(trip),
        "OVERVIEW": render_overview(trip, trip.get("_all_items", [])),
        "WEATHER": '<p class="lede">天气信息可在最终行程生成时按目的地和日期补充。</p>',
        "PRETRIP_CHECKLIST": '<li><label><input type="checkbox"> 确认机票、住宿、交通和保险</label></li><li><label><input type="checkbox"> 检查证件、签证和驾照/翻译件</label></li>',
        "ITINERARY": itinerary_html,
        "GALLERY": gallery_html or '<p class="lede">地点图鉴会根据行程地点生成；可后续补充图片、评分和点评摘要。</p>',
        "BUDGET": '<p class="lede">预算明细可由 budget_calculator.py 生成后填入。</p>',
        "VISA": '<p class="lede">签证与证件清单可根据目的地规则补充。</p>',
        "CUSTOMS": '<p class="lede">当地须知可根据目的地补充。</p>',
        "LOCAL_NEEDS": '<p class="lede">本地特殊需求可根据行程补充。</p>',
        "NOTES": '<p class="lede">这里可以放天气、交通、付款、通讯和安全提醒。</p>',
    }

    html_out = template
    for key, value in items_placeholder.items():
        html_out = html_out.replace(f"<!-- PLACEHOLDER:{key} -->", str(value))

    return html_out


def main():
    if len(sys.argv) < 2:
        print("用法: python3 itinerary_html_builder.py <trip_data.json> [output.html] [output.ics] [gallery.html]")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    trip = data.get("trip", {})
    nav_provider = trip.get("nav_map_provider", "none")
    default_transport_mode = infer_default_transport_mode(trip)
    start_date_str = trip.get("start_date")
    base_date = None
    if start_date_str:
        try:
            base_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"[警告] trip.start_date 格式应为 YYYY-MM-DD，当前值 '{start_date_str}' 无法解析，日历功能将被跳过。")

    all_items = data.get("items", [])
    trip["_all_items"] = all_items

    # 地点图鉴（独立于时间轴）
    gallery_out_path = sys.argv[4] if len(sys.argv) > 4 else "places_gallery.html"
    gallery_html = build_places_gallery(all_items)
    if gallery_html:
        with open(gallery_out_path, "w", encoding="utf-8") as f:
            f.write(gallery_html)
        place_count = gallery_html.count('class="place-card"')
        print(f"[地点图鉴] 已生成 {place_count} 个地点的图鉴卡片，保存到 {gallery_out_path}")
    else:
        print("[地点图鉴] 没有找到任何带 location 的行程项，跳过图鉴生成。")

    # 按天分组时间轴（仅含 day+time_start+time_end 的条目）
    by_day = defaultdict(list)
    for item in all_items:
        if item.get("day") and item.get("time_start") and item.get("time_end"):
            by_day[item["day"]].append(item)

    if not by_day:
        print("[提示] 没有找到任何带完整 day/time_start/time_end 的行程项，无法生成时间轴。")
        sys.exit(0)

    # 生成交互式在线地图（用所有带坐标的条目，不限于时间轴条目）
    map_html = build_online_map(all_items, trip)

    out_parts = []
    all_vevents = []
    skipped_links = 0
    skipped_cal = 0
    photos_shown = 0
    located_items_count = 0
    ratings_shown = 0

    for day in sorted(by_day.keys()):
        items = sorted(by_day[day], key=lambda x: to_minutes(x["time_start"]))
        day_date = day_to_date(day, base_date)
        date_label = ""
        if day_date:
            date_label = f" · {day_date.month}月{day_date.day}日 {WEEKDAYS[day_date.weekday()]}"

        out_parts.append(f'<div class="day-card" id="day-{day}">')
        out_parts.append(f'<div class="stub"><span class="stub-num">第{day}天</span></div>')
        out_parts.append('<div class="body">')
        out_parts.append(f'<h3><span class="day-date">{esc(date_label.lstrip(" ·") or "行程安排")}</span></h3>')
        out_parts.append('<ol class="timeline">')

        prev_end = None
        last_located = None
        total_minutes = 0

        for idx, it in enumerate(items):
            start = to_minutes(it["time_start"])
            end = to_minutes(it["time_end"])
            desc = it.get("description", "(未命名项目)")
            conflict = prev_end is not None and start < prev_end

            # 导航段：🧭 跳转按钮 + 点击地图联动
            if it.get("location") and last_located is not None:
                mode = it.get("transport_mode_from_prev") or default_transport_mode
                link = build_nav_link(nav_provider, last_located, it, mode)

                # 坐标数据 for 地图联动
                fLat = last_located.get("lat")
                fLng = last_located.get("lng")
                tLat = it.get("lat")
                tLng = it.get("lng")
                has_coords = all(v is not None for v in [fLat, fLng, tLat, tLng])

                onclick_attr = ""
                if has_coords:
                    onclick_attr = (
                        f' data-from-lat="{fLat}" data-from-lng="{fLng}"'
                        f' data-to-lat="{tLat}" data-to-lng="{tLng}"'
                        f' onclick="if(event.target.tagName!==\'A\') tripMapShowSegment({fLat},{fLng},{tLat},{tLng},this)"'
                        f' style="cursor:pointer" title="点击在上方地图中查看这段路线"'
                    )

                if link:
                    url, label = link
                    map_hint = '<span class="map-seg-hint">↑ 地图</span>' if has_coords else ''
                    out_parts.append(
                        f'<li class="nav-leg"{onclick_attr}>'
                        f'<a href="{esc(url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">'
                        f"🧭 {esc(label)}</a>{map_hint}</li>"
                    )
                elif has_coords:
                    out_parts.append(
                        f'<li class="nav-leg"{onclick_attr}>'
                        f'<span class="nav-leg-nolink">{esc(last_located.get("location",""))} → {esc(it.get("location",""))}</span>'
                        f'<span class="map-seg-hint">↑ 地图</span></li>'
                    )
                elif nav_provider != "none":
                    skipped_links += 1

            # 加入日历
            cal_link_html = ""
            if day_date:
                event_start = datetime.combine(day_date, datetime.min.time()) + timedelta(minutes=start)
                event_end = datetime.combine(day_date, datetime.min.time()) + timedelta(minutes=end)
                uid = f"item-{day}-{idx}-{start}@travel-planner"
                vevent = build_vevent(uid, event_start, event_end, desc, it.get("location", ""), it.get("notes", ""))
                all_vevents.append(vevent)
                single_ics = build_vcalendar([vevent], calname=desc)
                cal_link_html = f'<a class="mini-action" href="{ics_data_uri(single_ics)}" download="event.ics">📅 加入日历</a>'
            else:
                skipped_cal += 1

            # 预订平台链接
            booking_html = ""
            platform = it.get("booking_platform")
            if platform:
                url = it.get("booking_url") or PLATFORM_HOMEPAGES.get(platform)
                if url:
                    booking_html = (f'<a class="mini-action booking" href="{esc(url)}" target="_blank" rel="noopener">🎫 {esc(platform)}</a>')
                else:
                    booking_html = f'<span class="mini-action booking-text">🎫 建议通过 {esc(platform)} 预订</span>'

            # 照片缩略图
            media_html = ""
            if it.get("location"):
                located_items_count += 1
                photo_url = it.get("photo_url")
                if photo_url:
                    media_html = f'<span class="item-media"><img class="thumb photo" src="{esc(photo_url)}" alt="{esc(it.get("location"))}照片" loading="lazy"></span>'
                    photos_shown += 1

            # 评分徽标
            rating_html = ""
            rating = it.get("rating")
            if rating is not None:
                bits = [f"⭐ {esc(rating)}"]
                detail = []
                if it.get("rating_count") is not None:
                    detail.append(f"{esc(it['rating_count'])}条评价")
                if it.get("rating_source"):
                    detail.append(esc(it["rating_source"]))
                if detail:
                    bits.append(f"（{' · '.join(detail)}）")
                rating_html = f'<span class="rating">{"".join(bits)}</span>'
                ratings_shown += 1

            conflict_class = ' class="conflict-warning"' if conflict else ""
            conflict_note = " ⚠️ 与上一项时间重叠，请检查" if conflict else ""
            out_parts.append(
                f"<li{conflict_class}>"
                f'<span class="time">{esc(it["time_start"])}–{esc(it["time_end"])}</span> '
                f'<span class="desc">{esc(desc)}</span>{rating_html}{conflict_note}'
                f'<span class="item-actions">{cal_link_html}{booking_html}</span>'
                f"{media_html}</li>"
            )

            total_minutes += max(0, end - start)
            prev_end = end
            if it.get("location"):
                last_located = it

        hours = total_minutes / 60
        out_parts.append("</ol>")
        out_parts.append(f'<p class="day-total">当日有安排活动合计约 {hours:.1f} 小时</p>')
        out_parts.append("</div></div>")

    # 顶部：在线地图 + "一键导入全部行程"按钮
    add_all_html = ""
    ics_out_path = sys.argv[3] if len(sys.argv) > 3 else "trip_calendar.ics"
    if all_vevents:
        full_ics = build_vcalendar(all_vevents, calname=f"{trip.get('origin','')}{trip.get('destination','')}行程")
        with open(ics_out_path, "w", encoding="utf-8", newline="") as f:
            f.write(full_ics)
        add_all_html = (
            '<div class="add-all-calendar">'
            f'<a class="cta-button" href="{ics_data_uri(full_ics)}" download="trip_calendar.ics">📅 一键导入全部行程到日历</a>'
            f'<span class="cta-hint">也可以直接使用同目录下的 {esc(ics_out_path)} 文件导入</span>'
            '</div>'
        )
    elif base_date is None:
        add_all_html = (
            '<p class="cta-hint">提示：trip.start_date 未设置，暂时无法生成"加入日历"功能，'
            "如需要请回到第1步补充具体出发日期。</p>"
        )

    # 最终拼接：地图在最上方；默认输出完整带样式 HTML。
    itinerary_fragment = map_html + "\n" + add_all_html + "\n" + "\n".join(out_parts)
    html_out = render_full_page(trip, itinerary_fragment, gallery_html)
    out_path = sys.argv[2] if len(sys.argv) > 2 else "itinerary.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[已保存到 {out_path}]")
    if all_vevents:
        print(f"[完整行程日历文件已保存到 {ics_out_path}，共 {len(all_vevents)} 个事件]")
    if nav_provider == "none":
        print("[提示] trip.nav_map_provider 为 none，未生成任何导航跳转链接，仅输出时间轴。")
    elif skipped_links:
        print(f"[提示] 有 {skipped_links} 段相邻行程因缺少 location 字段未能生成导航链接，建议回到第8步补全。")
    if skipped_cal:
        print(f"[提示] 有 {skipped_cal} 项因缺少 trip.start_date 未能生成日历事件。")
    if located_items_count:
        print(
            f"[提示] 共 {located_items_count} 个有地点的行程项，其中 {photos_shown} 个配了真实照片、"
            f"{ratings_shown} 个配了评分。"
            f"没有照片的项目可以考虑运行 photo_lookup.py 自动补一批，或手动联网搜索补充。"
        )


if __name__ == "__main__":
    main()
