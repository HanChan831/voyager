# 在线地图与地点搜索说明（Leaflet / CARTO Light 栅格瓦片 / OSM 数据版）

最终网页里的交互式地图由 `itinerary_html_builder.py` 自动生成，**固定使用 Leaflet + CARTO Light 栅格瓦片（OSM 数据）**。不再询问、不再保存、也不再使用任何第三方地图配置。

## 在线地图怎么工作

- **坐标来源**：第 11 步先运行 `geocode_lookup.py`，统一用 OpenStreetMap / Nominatim 给地点查 `lat` / `lng`。
- **地图渲染**：第 11 步再运行 `itinerary_html_builder.py`，用 Leaflet + CARTO Light 栅格瓦片（OSM 数据）展示在线地图和地点标记。
- **地点标记**：`trip_data.json` 里凡是有 `lat` / `lng` 的行程项，都会在地图上打点。
- **路线联动**：点击时间轴里的“A → B 导航”条目旁的“↑ 地图”，地图会缩放到这两个点并画线。
- **显示全部**：地图按钮会回到包含全部标记点的总览视角。

## 地点搜索语言规则

无论是查坐标、查图片，还是人工搜索评分/评论，都要优先使用两套名称：

1. **英文名**：例如 `Blue Lagoon Iceland`。
2. **当地语言名**：例如冰岛语 `Bláa lónið`。

建议在 `trip_data.json` 中为每个地点尽量补充：

- `location`：用户可读名称。
- `location_en` / `name_en`：英文名。
- `location_local` / `name_local`：当地语言名。
- `address`：完整地址。
- `search_aliases`：其他别名数组。

脚本会把这些字段和目的地城市/国家组合起来搜索，避免只用中文译名导致 OSM 或境外平台搜不到。

## 坐标从哪里来：geocode_lookup.py

`geocode_lookup.py` 会：

- 跳过已有 `lat` / `lng` 的项目，不覆盖手动坐标。
- 对缺少坐标的地点，依次尝试英文名、本地语言名、完整地址、城市/国家组合。
- 用 `accept-language` 同时偏向英文和当地语言结果。
- 找不到时列出未命中清单，方便手动补 `lat` / `lng`。

## 地点图片从哪里来：photo_lookup.py

`photo_lookup.py` 不再用专有地图接口查图，改用公开来源尝试：

- 中国内地地点：Bing Images、Google Images / Bing Images、中文/英文Google/Bing 图片搜索等。
- 中国内地以外地点：Google Images / Bing Images、英文/当地语言Google/Bing 图片搜索、官方网站或境外主流平台手动补充。

自动脚本找不到时，再手动用 `web_search` + `image_search` 搜索。境外地点优先用英文名和当地语言名搜索，来源优先官方网站、Google Maps、Tripadvisor、Booking、Agoda、Google Images / Bing Images、Google Images / Bing Images 等。

如果使用境外来源，只需要提醒用户一句：**“接下来会用境外来源核对/补充部分评分、评论或图片。”**提醒到这里即可。

## 导航跳转按钮（🧭）与在线地图是两件不同的事

- **页面内在线地图**：固定 OSM，用于在网页里展示地点总览与路线段联动，不需要用户提供任何第三方地图配置。
- **“🧭 A → B（驾车）”按钮**：点击后跳转到外部地图 App，由 `trip.nav_map_provider` 决定，可以是高德、百度、Google、Apple 或不要。
- **地点图鉴数据源**：由 `trip.destination_region` 和实际可查结果决定。中国内地优先国内平台；中国内地以外优先境外平台和官方来源。

## 离线与分享

离线状态下 OSM 在线地图瓦片不会加载，但页面其他部分（时间轴、预算、日历、地点图鉴）仍能查看。如果图片已经本地化到 `img/` 文件夹，照片也可离线显示。分享最终行程时，要把 `trip_plan.html` 和 `img/` 文件夹一起打包。


## 关于 403r

生成的本地 HTML 不应直接使用 `tile.openstreetmap.org`。OSMF 官方瓦片要求有效 Referer，本地 `file://` 页面经常不会发送 Referer，容易出现 403r；因此页面底图改用 CARTO Light 栅格瓦片，坐标搜索仍使用 OSM/Nominatim。


## 搜索加速与过滤规则

- 坐标和图片脚本只搜索真实地点字段：`location`、`location_en`、`location_local`、`address`、`search_aliases`。
- 不再把 `description` 当地点搜索，避免把签证指南、保险说明、燃油费用、自炊说明等句子拿去查坐标或图片。
- 默认跳过 `day: 0` 的行前事项，以及签证/保险/证件/预算/通讯/税费等非地点类别。
- 重复地点只查询一次，结果会写入 `geocode_cache.json` / `photo_cache.json`，下次复用缓存。
- 图片脚本默认跳过餐饮小店图片；如果确实要查餐厅图片，可以加 `--include-food`，如果要更全面但更慢的查图，可以加 `--deep`。


## 默认极速模式

坐标和图片搜索默认走极速模式：

- 坐标：只查地图必要地点；`description` 不参与搜索；`day: 0` 和餐饮默认跳过；重复地点走缓存。
- 图片：默认只查景点/地标；住宿、交通、餐饮默认跳过；只写远程图片链接，不下载。
- 需要更完整的地点图鉴时，再按需使用 `--include-food`、`--include-stays`、`--include-transport`、`--download`、`--deep`。


## 图片 fallback

自动查图找不到时，`photo_lookup.py` 会保留 `photo_url` 为空，并写入 `photo_search_urls`：
- Google Images / Bing Images：优先核对，图片来源和授权信息更清楚。
- Google Images：境外地点备选搜索入口。
- Bing Images：可作为中国大陆访问相对更方便的备选入口。

脚本不会自动抓取 Google/Bing 搜索结果里的图片，避免误取广告图、低清缩略图或版权不明图片。人工确认后再手动填写 `photo_url`。


## v9 坐标与图片搜索

- 坐标搜索：英文名 + 英文目的地优先；失败后立刻查本地语言名 + 本地语言目的地。
- 图片搜索：不再调用旧自动取图来源来源；只生成 Google Images 和 Bing Images 查询入口。
- Bing Images 作为中国大陆访问相对更方便的图片搜索备选。
- Google/Bing 结果必须人工确认后再填写 `photo_url`，脚本不自动抓取搜索页图片。


## v10 极速地图图层

页面内在线地图固定使用最轻量的方案：
- Leaflet 作为唯一地图库。
- CARTO Light 栅格瓦片作为底图。
- 不使用 MapLibre、矢量地图、路线服务或复杂样式。
- 关闭非必要动画、retina 瓦片和大 buffer，优先减少首屏瓦片数量。
- 地图只做地点总览、marker 和简单直线联动；真实导航继续交给外部地图 App。


## v11 极速无底图模式

页面内地图默认改为零瓦片 SVG 方位图：
- 不加载 Leaflet、MapLibre、CARTO、OSM 官方瓦片或任何地图底图。
- 不需要网络即可显示已有坐标点。
- 只展示地点相对方位、分类 marker、简单直线联动。
- 如果需要真实道路和底图，点击时间轴里的外部导航按钮打开 Google / Apple / 高德 / 百度等地图 App。


## v12 Google 无 API 懒加载模式

默认不自动加载 Google iframe，避免拖慢页面或触发 Zen/浏览器的嵌入拦截。
页面会显示：
- 每天路线地点列表；
- 根据用户交通方式生成的 Google Maps 路线链接；
- “页面内查看 Google 地图”按钮；
- “新窗口打开 Google Maps”兜底按钮。

交通方式：
- `trip.transport_mode = "driving"`：租车/自驾；
- `trip.transport_mode = "transit"`：公共交通；
- `trip.transport_mode = "walking"`：步行；
- `trip.transport_mode = "taxi"`：按驾车路线打开。

注意：Google 无 API iframe 可能被浏览器或 Google 安全策略阻止嵌入，所以新窗口链接必须始终保留。


## v13 第一版 Google 搜索地图

页面内地图回到第一版做法：只嵌入 Google 搜索地图 `q=...&output=embed`，不嵌入 `/maps/dir` 路线页。
这样 iframe 成功率更高，也更接近最早能正常打开的版本。

路线、路程和预计时间不在 iframe 里强制展示，而是通过新窗口 Google Maps 链接打开。


### v18 Leaflet + Esri/ArcGIS 全 marker 地图

页面内互动地图改为 Leaflet + Esri/ArcGIS 公共底图：
- 不再使用 Google iframe 或 Google 搜索地图作为页面内地图。
- 不请求 OSM 官方瓦片。
- 底图使用 `server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}`。
- marker 和每日路线线条由 HTML 页面自己绘制，因此“全部 / Day 1 / Day 2 / 后续日期”都会稳定显示所有有 `lat/lng` 的地点。
- 第一个选项固定为“全部”，后面是 Day 1、Day 2、Day 3……
- 右侧地点列表点击后定位到对应 marker。
- 完整路线、路程和预计时间仍通过“新窗口打开路线”跳转 Google Maps；路线模式按用户租车/公共交通选择生成。
- 如果缺少坐标，应先运行 `geocode_lookup.py` 补齐 `lat/lng`。


### v20 图鉴按钮精简 + 地图放大

- 图鉴不再显示 Google 图片 / Bing 图片按钮。
- 图鉴不再显示查 Google 评分 / 查 Bing 评价按钮。
- 缺失评分或评价摘要时，改为提供 Booking / Agoda 查询入口。
- 没有 `photo_url` 时仍保留图片搜索缩略图预览，但不显示 Google/Bing 图片按钮。
- 在线地图区域加大：桌面端高度约 820px，移动端约 620px；地图列比例也加宽。


### v21 图鉴无外部按钮 + 在线地图 XL

- 图鉴缺失评分/评价时不再显示 Booking / Agoda 查询按钮；只提示这些平台可作为人工 fallback 核对来源。
- 图鉴缺失图片时保留缩略图预览和补填提示，但不显示 Google/Bing/Booking/Agoda 按钮。
- 在线地图左侧互动地图区域进一步加大：桌面端地图列更宽、内边距更小，高度约 84vh，最低约 840px；移动端最低约 640px。


### v23 地图布局硬修复

- Leaflet 地图区域不再使用 `<main class="leaflet-map-area">`，改为 `<div class="leaflet-map-area">`，避免被全局 `main { max-width }` 样式挤窄。
- 地图初始化前会检查容器是否可见且有真实宽高；隐藏标签页中不会提前初始化 Leaflet。
- 切换到“逐日行程”时多次触发 `tripLeafletRefreshMap()` 和 `invalidateSize()`，修复瓦片只加载左上角一小块的问题。
- 逐日行程地图宽度改为 `calc(100vw - 8px)`，左右边距进一步缩小。


### v24 地图左右留白舒适化

- 在 v23 修复 Leaflet 地图瓦片错位后，恢复更舒服的页面左右留白。
- 桌面端地图容器从 `calc(100vw - 8px)` 调整为 `calc(100vw - 72px)`，最大宽度约 1360px。
- 地图仍保持大尺寸，但不再贴边。
- 移动端保留较窄留白，宽度约 `calc(100vw - 24px)`。


### v25 大边距地图版

- 逐日行程地图改为大边距视觉：桌面端宽度约 `min(1180px, 100vw - 160px)`。
- 大屏左右留白更明显，不再贴近浏览器边缘。
- 地图高度保持较大：约 `min(920px, 80vh)`，最低约 760px。
- 保留 v23 的 Leaflet 可见后初始化和 `invalidateSize()` 修复。


### v26 全站统一大边距系统

- 不再只单独调整在线地图宽度。
- 封面、按钮栏、顶部导航、所有内容页、逐日行程地图、图鉴、预算、页脚统一使用同一套页面容器。
- 统一变量：
  - `--page-max: 1180px`
  - `--page-gutter: clamp(56px, 8vw, 150px)`
  - `--page-width: min(1180px, 100vw - 左右 gutter)`
- 在线地图不再使用 `100vw` 拉出正文容器，而是严格跟随统一页面宽度。
- 移动端自动缩小 gutter，避免内容过窄。


### v29 统一高级横幅色 + 地图右侧列表等高

- 顶部封面横幅和打印 / 导出 PDF 横幅统一为同一套深蓝灰渐变背景。
- 打印按钮改为低饱和金色渐变，整体更沉稳。
- 逐日行程在线地图右侧地点列表强制与左侧地图等高，避免底部露出空白。
- 移动端保持单列布局，右侧列表不强制固定高度。


### v30 商务深蓝横幅 + 地图右侧列表贴底

- 顶部封面和打印 PDF 横幅改为更深的商务海军蓝渐变。
- 金色按钮降低饱和度，整体更稳重。
- 在线地图右侧列表外层、列表容器、列表本身统一固定高度，与左侧地图区域一致。
- 列表内部滚动，底部不再出现面板未贴到底的空白错位。
