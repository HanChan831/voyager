import json

with open('./trip-plan-workspace/trip_data.json', 'r') as f:
    data = json.load(f)

attractions = [
    # Day 2 - Golden Circle
    {
        'day': 2, 'category': '门票/活动',
        'description': '辛格维利尔国家公园 (Thingvellir)',
        'time_start': '10:30', 'time_end': '12:00',
        'amount': 0, 'per_person': True,
        'location': 'Thingvellir National Park',
        'location_en': 'Thingvellir National Park',
        'location_local': 'Þingvellir',
        'transport_mode_from_prev': 'driving',
        'rating': 4.7, 'rating_source': 'Google Maps',
        'review_summary': 'UNESCO世界遗产，北美与欧亚板块裂缝，冰岛议会发源地',
        'services': ['免费停车场', '游客中心', '洗手间'],
        'notes': '免费入场，停车费约750ISK(¥50)。'
    },
    {
        'day': 2, 'category': '门票/活动',
        'description': '盖歇尔间歇泉 (Geysir)',
        'time_start': '12:30', 'time_end': '13:15',
        'amount': 0, 'per_person': True,
        'location': 'Geysir Hot Spring Area',
        'location_en': 'Geysir Geothermal Area',
        'location_local': 'Geysir',
        'transport_mode_from_prev': 'driving',
        'rating': 4.6, 'rating_source': 'Google Maps',
        'review_summary': 'Strokkur间歇泉每5-10分钟喷发20米高，免费24小时开放',
        'services': ['免费停车', '游客中心', '餐厅', '洗手间'],
        'notes': '免费入场。'
    },
    {
        'day': 2, 'category': '门票/活动',
        'description': '黄金瀑布 (Gullfoss)',
        'time_start': '13:30', 'time_end': '14:15',
        'amount': 0, 'per_person': True,
        'location': 'Gullfoss Waterfall',
        'location_en': 'Gullfoss',
        'location_local': 'Gullfoss',
        'transport_mode_from_prev': 'driving',
        'rating': 4.8, 'rating_source': 'Google Maps',
        'review_summary': '冰岛最壮观的瀑布之一，双层跌落32米，晴天必有彩虹',
        'services': ['免费停车', '游客中心', '餐厅', '洗手间'],
        'notes': '免费入场。'
    },
    # Day 3 - South Coast
    {
        'day': 3, 'category': '门票/活动',
        'description': '塞里雅兰瀑布 + Gljufrabui隐秘瀑布 (Seljalandsfoss)',
        'time_start': '09:30', 'time_end': '10:30',
        'amount': 0, 'per_person': True,
        'location': 'Seljalandsfoss',
        'location_en': 'Seljalandsfoss',
        'location_local': 'Seljalandsfoss',
        'transport_mode_from_prev': 'driving',
        'rating': 4.7, 'rating_source': 'Google Maps',
        'review_summary': '走到瀑布水帘后面看世界，隔壁Gljufrabui藏在岩缝里别有洞天',
        'services': ['停车场', '洗手间', '小型商店'],
        'notes': '免费入场，停车费约700ISK。穿雨衣！会被淋湿。'
    },
    {
        'day': 3, 'category': '门票/活动',
        'description': '斯科加瀑布 (Skogafoss)',
        'time_start': '11:00', 'time_end': '11:45',
        'amount': 0, 'per_person': True,
        'location': 'Skogafoss',
        'location_en': 'Skogafoss',
        'location_local': 'Skogafoss',
        'transport_mode_from_prev': 'driving',
        'rating': 4.8, 'rating_source': 'Google Maps',
        'review_summary': '60米落差，晴天常现双彩虹，可登370级台阶俯瞰',
        'services': ['停车场', '洗手间', '露营地'],
        'notes': '免费入场。'
    },
    {
        'day': 3, 'category': '门票/活动',
        'description': '雷尼斯黑沙滩 (Reynisfjara)',
        'time_start': '13:30', 'time_end': '14:30',
        'amount': 0, 'per_person': True,
        'location': 'Reynisfjara Black Sand Beach',
        'location_en': 'Reynisfjara Beach',
        'location_local': 'Reynisfjara',
        'transport_mode_from_prev': 'driving',
        'rating': 4.7, 'rating_source': 'Google Maps',
        'review_summary': '玄武岩柱+黑沙+雷尼斯岩海柱群，冰岛最出片的沙滩，警惕偷袭巨浪远离水线',
        'services': ['免费停车', '餐厅', '洗手间'],
        'notes': '免费入场。危险：偷袭巨浪可把人卷走，务必远离水边至少30米。'
    },
    # Day 4 - Glacier Lagoon
    {
        'day': 4, 'category': '门票/活动',
        'description': '斯卡夫塔山/Svartifoss黑色玄武岩瀑布',
        'time_start': '10:00', 'time_end': '11:30',
        'amount': 0, 'per_person': True,
        'location': 'Skaftafell, Vatnajokull National Park',
        'location_en': 'Skaftafell',
        'location_local': 'Skaftafell',
        'transport_mode_from_prev': 'driving',
        'rating': 4.6, 'rating_source': 'Google Maps',
        'review_summary': '瓦特纳冰川国家公园门户，Svartifoss黑色玄武岩柱瀑布徒步往返约1h',
        'services': ['游客中心', '停车场', '洗手间', '露营地'],
        'notes': '免费入场。Svartifoss徒步往返约1.5h/3km上坡。'
    },
    {
        'day': 4, 'category': '门票/活动',
        'description': '杰古沙龙冰河湖 (Jokulsarlon)',
        'time_start': '12:30', 'time_end': '13:30',
        'amount': 0, 'per_person': True,
        'location': 'Jokulsarlon Glacier Lagoon',
        'location_en': 'Jokulsarlon',
        'location_local': 'Jokulsarlon',
        'transport_mode_from_prev': 'driving',
        'rating': 4.9, 'rating_source': 'Google Maps',
        'review_summary': '冰岛必去！巨型浮冰在湖中漂流入海，海豹在冰山间嬉戏，景色震撼',
        'services': ['停车场', '洗手间', '咖啡厅', '游船售票处'],
        'notes': '免费参观。游船可选（约400元/人，预算原因建议跳过）。'
    },
    {
        'day': 4, 'category': '门票/活动',
        'description': '钻石沙滩 (Diamond Beach)',
        'time_start': '13:30', 'time_end': '14:00',
        'amount': 0, 'per_person': True,
        'location': 'Diamond Beach, Jokulsarlon',
        'location_en': 'Diamond Beach',
        'location_local': 'Diamond Beach',
        'transport_mode_from_prev': 'walking',
        'rating': 4.8, 'rating_source': 'Google Maps',
        'review_summary': '被海浪冲回黑沙滩的冰块像钻石散落，冰岛最出片的机位之一',
        'services': ['免费停车'],
        'notes': '冰河湖对面，步行过桥即达。免费。'
    },
    # Day 5 - North
    {
        'day': 5, 'category': '门票/活动',
        'description': '黛提瀑布 (Dettifoss)',
        'time_start': '13:00', 'time_end': '13:45',
        'amount': 0, 'per_person': True,
        'location': 'Dettifoss, Vatnajokull National Park',
        'location_en': 'Dettifoss',
        'location_local': 'Dettifoss',
        'transport_mode_from_prev': 'driving',
        'rating': 4.8, 'rating_source': 'Google Maps',
        'review_summary': '欧洲水量最大的瀑布，100米宽44米高，雷神之锤般的水声',
        'services': ['停车场', '洗手间'],
        'notes': '免费入场。从1号公路有岔路，东岸西岸均可到。'
    },
    {
        'day': 5, 'category': '门票/活动',
        'description': 'Namafjall Hverir地热区',
        'time_start': '14:30', 'time_end': '15:00',
        'amount': 0, 'per_person': True,
        'location': 'Namaskard geothermal area, Myvatn',
        'location_en': 'Namafjall Hverir',
        'location_local': 'Namaskard',
        'transport_mode_from_prev': 'driving',
        'rating': 4.5, 'rating_source': 'Google Maps',
        'review_summary': '沸腾泥浆池、蒸汽喷口、硫磺地貌，像走在火星表面',
        'services': ['免费停车'],
        'notes': '免费。硫磺味重，地面很烫，走木栈道。'
    },
    {
        'day': 5, 'category': '门票/活动',
        'description': '米湖温泉 Myvatn Nature Baths（可选）',
        'time_start': '15:30', 'time_end': '17:00',
        'amount': 275, 'per_person': True,
        'location': 'Myvatn Nature Baths',
        'location_en': 'Myvatn Nature Baths',
        'location_local': 'Jardbodin vid Myvatn',
        'transport_mode_from_prev': 'driving',
        'rating': 4.5, 'rating_source': 'Google Maps',
        'review_summary': '比蓝湖便宜、人更少的天然温泉，蓝色温泉水俯瞰米湖景色',
        'services': ['停车场', '更衣室', '淋浴', '储物柜', '咖啡厅'],
        'notes': '约5500ISK(¥275)/人，可选项目。如不去可提前去Godafoss。'
    },
    {
        'day': 5, 'category': '门票/活动',
        'description': '众神瀑布 (Godafoss)',
        'time_start': '17:45', 'time_end': '18:15',
        'amount': 0, 'per_person': True,
        'location': 'Godafoss Waterfall',
        'location_en': 'Godafoss',
        'location_local': 'Godafoss',
        'transport_mode_from_prev': 'driving',
        'rating': 4.7, 'rating_source': 'Google Maps',
        'review_summary': '12米高30米宽的马蹄形瀑布，公元1000年冰岛皈依基督教时众神像投入此瀑布',
        'services': ['停车场', '洗手间', '商店'],
        'notes': '免费入场。'
    },
    # Parking fees
    {
        'day': 2, 'category': '门票/活动',
        'description': '辛格维利尔国家公园停车费',
        'amount': 50, 'per_person': False,
        'notes': '停车费约750ISK(¥50)/车。'
    },
]

for attr in attractions:
    data['items'].append(attr)

with open('./trip-plan-workspace/trip_data.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f'Added {len(attractions)} attraction items')
