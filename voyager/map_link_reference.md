# 地图 App 导航链接格式说明

`itinerary_html_builder.py` 内置了四种地图 App 的链接生成逻辑，对应 `trip.nav_map_provider` 字段（第14题用户选的"点击跳转用哪个App"）。这份文档说明各自的原理和稳定性，方便在需要时手动核实或调整。

> 这份文档讲的是“点击跳转到地图 App”的导航按钮。页面内的交互式在线地图和地点图片是另一套机制：在线地图固定使用 OSM，地点图片按英文名和本地语言名搜索公开来源，详见 `online_map_embed.md`。

## 目的地在中国大陆以外时，第14题该怎么引导用户

高德、百度的导航数据以国内为主，对境外的道路、POI、公交线路覆盖通常不完整甚至直接搜不到——**如果第1步判断出目的地不在国内（跟第2步签证核查同样的判断逻辑），问第14题之前先主动提醒用户一句，推荐选 Google 地图或 Apple 地图**，而不是把五个选项平铺直叙列出来让用户自己猜哪个适合。Apple 地图在非 iOS/macOS 设备的浏览器里打开会跳转到网页版，同样可用，不是只有苹果用户能选。如果用户出于个人习惯仍然坚持选高德/百度（比如本来就装惯了、只是临时去周边国家短途），也尊重用户的选择，不强行替用户做决定。

## Google 地图（`google`）— 官方文档化、稳定

```
https://www.google.com/maps/dir/?api=1&origin=<起点>&destination=<终点>&travelmode=driving
```

`travelmode` 可选 `driving` / `walking` / `bicycling` / `transit`。这是 Google 官方文档化的 Directions URL（不需要额外配置即可跳转），格式长期稳定，可以直接信任脚本里的实现。起点/终点既可以是地名也可以是经纬度。

## Apple 地图（`apple`）— 官方文档化、稳定

```
http://maps.apple.com/?saddr=<起点>&daddr=<终点>&dirflg=d
```

`dirflg` 取值：`d`=驾车，`w`=步行，`r`=公交。同样是苹果官方支持的跳转格式，长期稳定。在非 Apple 设备的浏览器里打开会跳转到 Apple 地图网页版。

## 高德地图（`amap`）— ⚠️ 建议生成前核实

```
https://uri.amap.com/navigation?from=<起点经度>,<起点纬度>,<起点名称>&to=<终点经度>,<终点纬度>,<终点名称>&mode=car&policy=1&src=travel-planner&coordinate=gaode&callnative=1
```

这是高德"网页端调起 APP"的 URI 链接格式，**强烈依赖经纬度**才能保证准确跳转；如果 `trip_data.json` 里的行程项没有 `lat`/`lng`，脚本会退化成一个普通的高德网页搜索链接（只能定位到目的地，不会直接带出导航界面）。高德的接口参数和版本更新比 Google/Apple 更频繁，**生成最终文档前，建议联网搜索"高德地图 uri.amap.com navigation 最新参数"之类的关键词确认格式是否有变化**，如有出入直接修改 `itinerary_html_builder.py` 里 `build_nav_link` 函数对应分支的 URL 模板。

如果想要更准确的导航（即使用户没给经纬度），可以在第 8 步搜索景点信息时顺手把 OSM、官网或其他可靠来源能查到的坐标记下来，填进 `lat`/`lng` 字段。

## 百度地图（`baidu`）— ⚠️ 建议生成前核实

```
https://api.map.baidu.com/direction?origin=<起点>&destination=<终点>&mode=driving&output=html&src=travel-planner
```

`origin`/`destination` 支持两种写法：`纬度,经度`（有坐标时更准）或 `name:地点名称`（脚本在没有坐标时使用的写法，百度会尝试自动地理编码，但准确度不如带坐标）。和高德类似，**建议生成前联网核实当前参数格式**，必要时直接修改脚本里的对应分支。

## 没有地图 App 偏好（`none`）

`itinerary_html_builder.py` 会跳过所有导航链接生成，只输出纯文字时间轴。适合不需要导航功能、或者目的地是用户非常熟悉的本地短途行程。

## 通用建议

- 优先通过第 11 步的 `geocode_lookup.py` 使用 OSM/Nominatim 补齐经纬度；在第 6-8 步（住宿、景点、餐饮）搜索具体地点时如果顺手查到坐标，也可以直接记录，这会显著提升导航链接的准确度。
- 不确定某个地点该填什么 `location` 名称时，写得越具体越好（带上城市名/国家名，比如“成都武侯祠”而不是“武侯祠”）；境外地点尤其要补 `location_en` 和 `location_local`，提高 OSM、Google/Apple 跳转和图片/评分搜索命中率。


## Google 无 API 路线链接

Google Maps 无 API 路线链接格式：
`https://www.google.com/maps/dir/?api=1&origin=...&destination=...&waypoints=...&travelmode=driving|transit|walking`

页面内 iframe 仅在用户点击后尝试加载；如果浏览器阻止嵌入，使用同一个路线的新窗口链接。
