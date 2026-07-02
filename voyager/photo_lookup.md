# 地点照片查找指南

第3/5/6/7/8步收集每个具体地点（交通枢纽、租车点、住宿、景点、餐厅等）时，尽量给它配一张真实照片。核心原则仍然是：**找不到就留空，绝不编造图片链接**。

## 不再依赖地图接口

地点图片不再通过专有地图接口获取。自动脚本会使用 Google Images / Bing Images、Google Images / Bing Images、Bing Images等公开来源；人工补图时再按地区选择官方渠道或主流平台。

## 英文名 + 本地语言名一起搜

每个地点尽量记录：

- `location_en`：英文名。
- `location_local`：当地语言名。
- `address`：完整地址。
- `search_aliases`：其他别名。

自动脚本和人工搜索都要优先尝试“英文名 + 本地语言名 + 完整地址/城市/国家”的组合。境外地点不要只用中文译名搜索。

## 自动化查找顺序

`photo_lookup.py` 会按以下顺序尝试：

- **中国内地地点**：Bing Images → Google Images / Bing Images → 中文Google/Bing 图片搜索 → 英文Google/Bing 图片搜索。
- **中国内地以外地点**：Google Images / Bing Images → 英文/当地语言Google/Bing 图片搜索 → 中文Google/Bing 图片搜索 → Bing Images。
- **未明确地区**：先尝试中文与英文公开来源，再根据地点名和已有别名扩大搜索。

例如 Blue Lagoon, Grindavík, Iceland，应同时尝试 `Blue Lagoon Iceland`、`Bláa lónið`、`Norðurljósavegur 9, 240 Grindavík, Iceland`，而不是只搜中文名。

如果使用境外来源，只需要提醒用户一句：**“接下来会用境外来源补充地点图片。”**提醒到这里即可。

## 手动补图优先级

第11步运行 `photo_lookup.py` 后，如果终端列出“未找到照片”的地点，再逐项手动搜索补充：

- 中国内地地点：优先地点官网/官方公众号、携程、飞猪、美团、大众点评、高德详情页、Bing Images等。
- 中国内地以外地点：优先官方网站、Google Maps、Tripadvisor、Booking.com、Agoda、Google Images / Bing Images、Google Images / Bing Images 等境外常用来源。
- 如果搜到的是网页而不是直接图片链接，用页面的 `og:image` 或正文图片真实地址填入，不要把网页链接当图片链接。

每个地点尝试 1–2 轮搜索即可。确实找不到就留空，不要为了补齐而使用不相关图片。

## 版权与使用边界

- 自动脚本优先使用 Google Images / Bing Images / 图片搜索类公开页面图片，但仍要尊重来源页面的授权说明。
- 手动搜索的图片优先选地点官方渠道或授权状态清晰的平台主图；不要从个人博客或社交媒体随意抓取版权不明的图片。
- 这是面向用户个人旅行规划的私用交付物，不用于公开发布或商业宣传；即便如此，也要尽量选择来源可靠的图片。

## 怎么运行自动化查找

```bash
python3 photo_lookup.py ./trip-plan-workspace/trip_data.json
```

脚本会直接修改 `trip_data.json`：给每个有 `location` 但没有 `photo_url` 的项目自动配图，并尽量下载到同目录的 `img/` 文件夹；已经有 `photo_url` 的项目不会被覆盖，只会尝试把远程链接本地化。

## 在最终网页里怎么呈现

只要 `trip_data.json` 里的 item 有 `photo_url`，`itinerary_html_builder.py` 会自动在逐日时间轴和“地点图鉴”里展示照片。第12步直接复用脚本输出即可。分享时必须把 `trip_plan.html` 和 `img/` 文件夹一起打包，否则本地化照片会丢失。


## 默认极速模式

`photo_lookup.py` 默认只给“门票/活动”类景点/地标查图，每个唯一地点只尝试 1 个查询词，并且只写入远程 `photo_url`，不下载到本地。这样能明显减少网络请求和图片下载时间。

需要更完整但更慢时再加：
- `--include-food`：查餐饮图片。
- `--include-stays`：查住宿图片。
- `--include-transport`：查机场/交通/租车图片。
- `--download`：把远程图片下载到 `img/`，适合离线分享。
- `--deep`：增加更多来源和语言查询。


## Google Images / Bing Images fallback

维基体系没有找到图片时，脚本会自动写入 `photo_search_urls`，包含：
- Google Images / Bing Images 图片搜索
- Google Images
- Bing Images

Google/Bing 只作为人工搜索入口，不自动抓取搜索页结果。Bing Images 可作为中国大陆访问相对更方便的备选入口。人工确认图片真实、清晰、可用后，再把最终地址填写到 `photo_url`。


## v9：Google Images + Bing Images

`photo_lookup.py` 不再自动请求旧自动取图来源来源。脚本只生成图片搜索入口：

- `photo_search_urls.primary.google_images`
- `photo_search_urls.primary.bing_images`
- `photo_search_urls.local_language.google_images`
- `photo_search_urls.local_language.bing_images`

英文查询优先，本地语言查询第二。Bing Images 可以作为中国大陆访问相对更方便的备选入口。人工确认图片真实、清晰、可用后，再把最终图片地址写入 `photo_url`。
