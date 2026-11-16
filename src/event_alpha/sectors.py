"""申万一级行业与首期大宗对照。"""

SW_INDUSTRIES = (
    "农林牧渔",
    "基础化工",
    "钢铁",
    "有色金属",
    "电子",
    "家用电器",
    "食品饮料",
    "纺织服饰",
    "轻工制造",
    "医药生物",
    "公用事业",
    "交通运输",
    "房地产",
    "商贸零售",
    "社会服务",
    "综合",
    "建筑材料",
    "建筑装饰",
    "电力设备",
    "国防军工",
    "计算机",
    "传媒",
    "通信",
    "银行",
    "非银金融",
    "汽车",
    "机械设备",
    "煤炭",
    "石油石化",
    "环保",
    "美容护理",
)

# 期货代码接入时与 futures_display_main_sina 核对。对不上则偏离留空。
COMMODITY_SYMBOLS = {
    "有色金属": "CU0",
    "煤炭": "JM0",
    "石油石化": "SC0",
    "基础化工": "TA0",
    "农林牧渔": "M0",
    "钢铁": "RB0",
}

# 东财板块名称与申万不一致。这里只放首期明确对照，其余走势留空。
EASTMONEY_INDUSTRY = {
    "有色金属": "有色金属",
    "煤炭": "煤炭行业",
    "石油石化": "石油石化",
    "基础化工": "化学制品",
    "农林牧渔": "农牧饲渔",
    "钢铁": "钢铁行业",
    "电力设备": "电力设备",
    "机械设备": "机械设备",
}

EVENT_TYPES = ("policy", "supply", "tech", "overseas", "macro")
DIRECTIONS = ("positive", "negative", "neutral")
HORIZONS = ("short_1_5", "mid_5_20")
MAGNITUDES = ("weak", "mid", "strong")
HORIZON_LABELS = {"short_1_5": "1至5日", "mid_5_20": "5至20日"}
DIRECTION_LABELS = {"positive": "利多", "negative": "利空", "neutral": "中性"}
MAGNITUDE_VALUE = {"weak": 0.35, "mid": 0.65, "strong": 0.90}
