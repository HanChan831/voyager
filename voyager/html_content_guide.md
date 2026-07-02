# `trip_template.html` 填充指南

用 `str_replace` 工具逐个把占位注释替换成真实内容（替换后注释标记本身也会被一并清除）。**顶部操作栏的"打印/导出PDF"按钮是模板自带的固定结构（基于浏览器原生 `window.print()`），不需要填、不需要改，第12步直接复制模板就有。**

### 1. `<title>` 里的 `<!-- PLACEHOLDER:TITLE -->出行计划`

替换成实际标题，例如 `上海 → 成都 4日行程方案`。

### 2. `<h1>` 里的 `<!-- PLACEHOLDER:TITLE -->出发地 → 目的地 N日行程方案`

同一个标题在 `<title>` 和 `<h1>` 各出现一次（两处周围文本不同，分别替换）。

### 3. `<!-- PLACEHOLDER:FIELDROW -->`（护照式信息条）

替换成 4 个 `.field` 数据块，呈现关键信息，像护照信息页或登机牌的字段一样：

```html
<div class="field"><div class="k">Route</div><div class="v">上海 → 成都</div></div>
<div class="field"><div class="k">Dates</div><div class="v">08.10–08.13</div></div>
<div class="field"><div class="k">Pax</div><div class="v">2人</div></div>
<div class="field"><div class="k">Budget</div><div class="v">舒适优先</div></div>
```

`Budget` 这一格直接写用户在第1步选的"经济优先/舒适优先/自定义"。

### 4. `<!-- PLACEHOLDER:OVERVIEW -->`（概览区）

放一个 `overview-grid` 统计卡片组 + 一两句话的行程主线概述：

```html
<div class="overview-grid">
  <div class="stat"><div class="label">总天数</div><div class="value">4 天</div></div>
  <div class="stat"><div class="label">出行人数</div><div class="value">2 人</div></div>
  <div class="stat accent"><div class="label">总预算</div><div class="value">¥6800</div></div>
  <div class="stat accent"><div class="label">人均预算</div><div class="value">¥3400</div></div>
</div>
<p>这趟行程以市区文化古迹和熊猫基地为主线，节奏适中，长途交通选择了高铁二等座这个性价比最高的方案。</p>
```

可以在统计卡片组下面追加一句"本次预订渠道优先参考携程/飞猪"之类的说明，呼应第3/6步收集到的平台信息。这里的数字必须跟 `budget_summary.html` 里脚本算出来的一致，不要凭印象重新生成。

### 5. `<!-- PLACEHOLDER:WEATHER -->`（概览区的天气小卡片）

把第8步产出的 `weather_notes.md` 转写成简短的 HTML，放在 `.weather-card` 这个 div 里，结构参考：

```html
<h4>🌤️ 出行天气参考</h4>
<div class="weather-row">
  <div class="weather-day"><div class="d">8/10</div><div class="t">28-34℃ 多云</div></div>
  <div class="weather-day"><div class="d">8/11</div><div class="t">27-33℃ 雷阵雨</div></div>
</div>
<p class="weather-tip">出行期间天气炎热，午后有阵雨概率，建议携带雨具和防晒用品，户外行程尽量安排在上午或傍晚。</p>
```

如果出发日期距今超过两周、查到的是历史同期气候参考而不是精确预报，在 `weather-tip` 里明确写一句"以下为该季节历史气候参考，并非精确预报，临近出发请再查实时预报"，不要让用户误以为是确切预报。这个 div 留空时会自动隐藏（`.weather-card:empty`），所以如果第8步确实查不到任何天气信息，不写这部分也不会在页面上留下难看的空白——按真实性要求，查不到就让它空着，不要编几个温度数字填进去。

### 6. `<!-- PLACEHOLDER:PRETRIP_CHECKLIST -->`（行前准备清单区，独立标签页，在 `<ul class="checklist-items">` 内）

把 `pretrip_checklist.md`（第10步产出，参考 `pretrip_checklist.md`）里的每一条，转成一个真实可点击的复选框 `<li>`：

```html
<li><label><input type="checkbox"><span>检查护照有效期（需≥6个月）</span></label></li>
<li><label><input type="checkbox"><span>购买旅行保险</span></label></li>
<li><label><input type="checkbox"><span>兑换日元现金（建议5000元等值起）</span></label></li>
```

注意 `<span>` 包裹文字不能省略——勾选后的删除线效果是靠 CSS 选中这个 `<span>` 实现的。**不要预先帮用户把任何一项标成 `checked`**（除非用户明确说"这件事我已经办好了"），这份清单的默认状态应该是"全部待办"，由用户自己点击勾选。

### 7. `<!-- PLACEHOLDER:ITINERARY -->`（逐日时间轴区）

**直接复制 `itinerary_blocks.html`（`itinerary_html_builder.py` 的完整输出）粘贴进来**，不要重新手写——这份输出在时间轴最上方已经包含一张交互式在线地图（默认Leaflet + OpenFreeMap（OSM 数据）），有坐标的地点按类别标记，点击时间轴里的导航段条目，地图会自动缩放至那两点并画出连线。下方是每天的票根卡片（含“一键导入全部行程到日历”按钮、评分徽标、导航链接、加入日历、预订平台链接、照片缩略图）。如果脚本提示有未生成导航链接/日历事件/照片的项目，先确认是否需要回去补 `location`/`lat`/`lng`/`photo_url`/`trip.start_date` ，而不是在这里手动编。

### 8. `<!-- PLACEHOLDER:GALLERY -->`（地点图鉴区，独立标签页）

**直接复制 `places_gallery.html`（同一个脚本的输出）粘贴进来**，这是把行程里所有不重复的地点汇总成卡片网格（照片+评分+点评摘要），同样不要手写，没有照片/评分的地点脚本会自动用"暂无图片"占位，不会留下空白卡片或者编造内容。

### 9. `<!-- PLACEHOLDER:BUDGET -->`（预算区）

**直接复制 `budget_summary.html`（`budget_calculator.py` 的输出）粘贴进来**，不要重新计算或重新输入数字。货币口径只使用第1步选定的 `trip.currency`，不要在最终阶段再次询问或临时追加另一种显示货币。

### 10. `<!-- PLACEHOLDER:VISA -->`（签证区，在 `data-stamp="ENTRY · 入境核查"` 的卡片内）

把 `visa_notes.md` 的内容转写成 HTML，结构参考 `visa_checklist.md`。**有先后顺序的步骤（比如"先做什么、再做什么"的办理流程）用 `<ol class="steps"><li>...</li></ol>` 而不是在一段文字里写"1. 2. 3."**——这是模板自带的编号步骤样式，会渲染成圆形编号徽标，比纯文字数字编号清楚很多；没有顺序关系的并列要点用普通 `<ul><li>`。国内出行没有签证问题时写一句明确说明即可：`<p>本次为国内出行，无需办理签证。</p>`。

示例：

```html
<p>结论：需要办理普通签证，建议出发前6周开始准备。</p>
<ol class="steps">
  <li><strong>准备材料</strong>：护照原件、2张白底照片、申请表、酒店预订证明。</li>
  <li><strong>预约签证中心</strong>：通过官网预约递交材料的时间。</li>
  <li><strong>等待审理</strong>：预计 5-7 个工作日，可在线查询进度。</li>
</ol>
```

### 11. `<!-- PLACEHOLDER:CUSTOMS -->`（当地须知区，在 `data-stamp="CUSTOMS · 入乡随俗"` 的卡片内）

把 `customs_notes.md` 的内容转写成 HTML，结构参考 `customs_guidance.md`。禁带物品清单用 `<ol class="steps">`，行为举止这类并列提醒用 `<ul>`。国内出行且没有特别需要提醒的内容时，写一句：`<p>国内出行通常不涉及入境限制，建议遵守当地公共场所基本礼仪。</p>`。

示例：

```html
<ol class="steps">
  <li><strong>禁带新鲜水果、肉类制品</strong>入境时会被海关查扣。</li>
  <li><strong>处方药</strong>建议随身携带医生开具的英文处方证明。</li>
</ol>
<h4>行为举止提醒</h4>
<ul>
  <li>进入寺庙需脱鞋，肩膀和膝盖需遮盖。</li>
  <li>当地小费文化：餐厅一般支付账单金额的10%作为小费。</li>
</ul>
```

### 12. `<!-- PLACEHOLDER:LOCAL_NEEDS -->`（本地特殊需求区，在 `data-stamp="LOCAL · 在地准备"` 的卡片内）

把 `local_needs_notes.md` 的内容转写成 HTML，结构参考 `local_needs_checklist.md`，同样是**有顺序的准备步骤用 `<ol class="steps">`，并列要点用 `<ul>`**。没有额外需求时写：`<p>本次行程无额外本地特殊需求。</p>`。

### 13. `<!-- PLACEHOLDER:NOTES -->`（注意事项区）

放免责声明和提醒事项：价格为搜索时参考价、多币种换算说明（如适用）、预算/时间轴脚本运行后仍未处理的警告。可以用普通 `<ul>` 列出几条提醒，不需要用编号步骤样式（这些是并列的提醒事项，不是有先后顺序的流程）。

### 通用注意事项

- 所有数字类内容只能来自脚本输出，不要凭印象重新生成；所有评分/点评/照片只能来自实际搜索结果，查不到就让对应区块留空或写"未查到"，绝不编造——这是贯穿整个 skill 的真实性要求，在写 HTML 这一步同样适用。
- 替换完成后搜索一下文件里还有没有残留的 `PLACEHOLDER:` 字样。
- 不要改动 `<style>` 和 `<script>` 部分，除非用户明确要求调整视觉风格。
- **如果第1步选定的 `trip.language` 不是中文**，除了上面这些占位符要用选定语言填内容之外，模板里固定写死的中文界面文字也要一并替换成对应语言，包括：导航标签（"概览""行前准备""逐日时间轴"等）、顶部"打印 / 导出 PDF"按钮、护照信息条的字段标签（`ROUTE`/`DATES`这类英文字段名本身是设计语言不用动，但中文的值要换成对应语言）、页脚文字。逐项用 `str_replace` 找到对应的中文字符串替换，别漏掉藏在 `<button>`/`<h2>`/`<nav>` 里的固定文案。


## 在线地图性能原则

地图优先使用轻量栅格底图。不要在默认 HTML 中引入 MapLibre、矢量地图、3D 地图、路线规划服务或多个瓦片 fallback。默认只加载 Leaflet + CARTO Light 栅格瓦片，保证页面打开速度。


## v11 地图性能原则

最快加载优先时，不使用任何地图底图。默认地图区域使用内嵌 SVG 方位图，所有 marker 和线条都由 HTML 本身渲染，不产生外部地图请求。


### v14 完整 HTML 输出修正

`itinerary_html_builder.py` 现在默认把生成的行程片段套入 `trip_template.html`，直接输出包含 `<html>`、`<head>`、`<style>` 和标签页脚本的完整网页。不要再只把 `itinerary_blocks` 片段直接发给用户，否则浏览器会显示成未套样式的纯内容。


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


### v19 图鉴 搜索 搜索兜底

地点图鉴采用“真实字段优先 + 搜索 搜索入口兜底”：
- 如果 JSON 中有 `photo_url`，直接显示真实图片；否则显示 图片搜索入口。
- 如果 JSON 中有 `rating`、`rating_count`、`rating_source`，直接显示评分；否则显示 Google 评分 / Bing 评价搜索入口。
- 如果 JSON 中有 `review_summary`，直接显示评价摘要；否则显示 搜索 评价搜索入口。
- 普通 搜索 搜索页不是稳定结构化数据源，不应假装能可靠自动抓取评分、图片和评论；需要用户核对后把确认的信息写回 JSON 字段。


### v20 图鉴按钮精简 + 地图放大

- 图鉴不再显示 图片搜索按钮。
- 图鉴不再显示Booking / Agoda 查询按钮。
- 缺失评分或评价摘要时，改为提供 Booking / Agoda 查询入口。
- 没有 `photo_url` 时仍保留图片搜索缩略图预览，但不显示 搜索 图片按钮。
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


### v27 顶部封面横幅满宽

- 顶部蓝色封面横幅 `header.cover` 改为满屏宽度 `100vw`。
- 封面内部文字和字段仍使用统一大边距，与下方页面内容视觉对齐。
- 其他页面模块继续沿用 v26 的统一大边距系统。


### v28 打印 PDF 横幅满宽 + 图鉴说明精简

- 去掉图鉴图片兜底预览下方的“图片搜索预览 · 建议核对后替换为稳定 photo_url”说明文字。
- 打印 / 导出 PDF 按钮栏改为与顶部封面一致的满宽蓝色横幅。
- 打印按钮放在内容容器右侧，桌面端更容易点击；移动端居中并占满宽度。


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


### v31 去除页面左右灰色渐变/阴影

- 去掉顶部封面和打印 PDF 横幅的横向阴影，避免页面左右出现灰色渐变。
- 页面背景统一为纯净纸色 `var(--paper)`，不再叠加额外渐变。
- 保留 v30 商务深蓝横幅颜色、地图修复和右侧列表等高逻辑。


### v32 顶部目录导航居中排列

- 顶部目录导航（概览、行前准备、逐日行程、地点图鉴等）在桌面端整体居中排列。
- 保留换行能力，避免项目太多时挤压变形。
- 移动端仍然保持靠左，更符合小屏操作习惯。


### v33 目录按钮组结构化居中

- 顶部目录导航不再只靠 `nav.tabs { justify-content:center }`。
- 模板结构新增 `.tabs-inner` 内层容器，目录按钮组在该容器中整体居中。
- 外层 `nav.tabs` 满宽承载背景，内层 `.tabs-inner` 使用统一页面宽度。
- 桌面端按钮组居中；移动端保持横向滚动和靠左，方便手指操作。
