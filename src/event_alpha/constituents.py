"""申万成份股。一级是因子篮子，二级只标记篮子内部的对照子集。"""

from __future__ import annotations

from datetime import date, datetime

CONSTITUENT_BASIS = "current_sw_index_entered_by_news_day"

# 申万指数发布页的行业指数代码。没有公开指数的二级行业不在这里。
SW_INDEX_CODES = {
    '农林牧渔': '801010',
    '基础化工': '801030',
    '钢铁': '801040',
    '有色金属': '801050',
    '电子': '801080',
    '家用电器': '801110',
    '食品饮料': '801120',
    '纺织服饰': '801130',
    '轻工制造': '801140',
    '医药生物': '801150',
    '公用事业': '801160',
    '交通运输': '801170',
    '房地产': '801180',
    '商贸零售': '801200',
    '社会服务': '801210',
    '综合': '801230',
    '建筑材料': '801710',
    '建筑装饰': '801720',
    '电力设备': '801730',
    '国防军工': '801740',
    '计算机': '801750',
    '传媒': '801760',
    '通信': '801770',
    '银行': '801780',
    '非银金融': '801790',
    '汽车': '801880',
    '机械设备': '801890',
    '煤炭': '801950',
    '石油石化': '801960',
    '环保': '801970',
    '美容护理': '801980',
    '农产品加工': '801012',
    '饲料': '801014',
    '渔业': '801015',
    '种植业': '801016',
    '养殖业': '801017',
    '动物保健Ⅱ': '801018',
    '化学纤维': '801032',
    '化学原料': '801033',
    '化学制品': '801034',
    '塑料': '801036',
    '橡胶': '801037',
    '农化制品': '801038',
    '非金属材料Ⅱ': '801039',
    '冶钢原料': '801043',
    '普钢': '801044',
    '特钢Ⅱ': '801045',
    '金属新材料': '801051',
    '贵金属': '801053',
    '小金属': '801054',
    '工业金属': '801055',
    '能源金属': '801056',
    '通用设备': '801072',
    '专用设备': '801074',
    '轨交设备Ⅱ': '801076',
    '工程机械': '801077',
    '自动化设备': '801078',
    '半导体': '801081',
    '其他电子Ⅱ': '801082',
    '元件': '801083',
    '光学光电子': '801084',
    '消费电子': '801085',
    '电子化学品Ⅱ': '801086',
    '汽车服务': '801092',
    '汽车零部件': '801093',
    '乘用车': '801095',
    '商用车': '801096',
    '计算机设备': '801101',
    '通信设备': '801102',
    'IT服务Ⅱ': '801103',
    '软件开发': '801104',
    '白色家电': '801111',
    '黑色家电': '801112',
    '小家电': '801113',
    '厨卫电器': '801114',
    '照明设备Ⅱ': '801115',
    '家电零部件Ⅱ': '801116',
    '食品加工': '801124',
    '白酒Ⅱ': '801125',
    '非白酒': '801126',
    '饮料乳品': '801127',
    '休闲食品': '801128',
    '调味发酵品Ⅱ': '801129',
    '纺织制造': '801131',
    '服装家纺': '801132',
    '饰品': '801133',
    '包装印刷': '801141',
    '家居用品': '801142',
    '造纸': '801143',
    '文娱用品': '801145',
    '化学制药': '801151',
    '生物制品': '801152',
    '医疗器械': '801153',
    '医药商业': '801154',
    '中药Ⅱ': '801155',
    '医疗服务': '801156',
    '电力': '801161',
    '燃气Ⅱ': '801163',
    '物流': '801178',
    '铁路公路': '801179',
    '房地产开发': '801181',
    '房地产服务': '801183',
    '多元金融': '801191',
    '证券Ⅱ': '801193',
    '保险Ⅱ': '801194',
    '贸易Ⅱ': '801202',
    '一般零售': '801203',
    '专业连锁Ⅱ': '801204',
    '互联网电商': '801206',
    '专业服务': '801218',
    '酒店餐饮': '801219',
    '通信服务': '801223',
    '综合Ⅱ': '801231',
    '水泥': '801711',
    '玻璃玻纤': '801712',
    '装修建材': '801713',
    '房屋建设Ⅱ': '801721',
    '装修装饰Ⅱ': '801722',
    '基础建设': '801723',
    '专业工程': '801724',
    '工程咨询服务Ⅱ': '801726',
    '电机Ⅱ': '801731',
    '其他电源设备Ⅱ': '801733',
    '光伏设备': '801735',
    '风电设备': '801736',
    '电池': '801737',
    '电网设备': '801738',
    '航天装备Ⅱ': '801741',
    '航空装备Ⅱ': '801742',
    '地面兵装Ⅱ': '801743',
    '航海装备Ⅱ': '801744',
    '军工电子Ⅱ': '801745',
    '游戏Ⅱ': '801764',
    '广告营销': '801765',
    '影视院线': '801766',
    '数字媒体': '801767',
    '出版': '801769',
    '国有大型银行Ⅱ': '801782',
    '股份制银行Ⅱ': '801783',
    '城商行Ⅱ': '801784',
    '农商行Ⅱ': '801785',
    '摩托车及其他': '801881',
    '煤炭开采': '801951',
    '焦炭Ⅱ': '801952',
    '油服工程': '801962',
    '炼化及贸易': '801963',
    '环境治理': '801971',
    '环保设备Ⅱ': '801972',
    '个护用品': '801981',
    '化妆品': '801982',
    '航空机场': '801991',
    '航运港口': '801992',
    '旅游及景区': '801993',
    '教育': '801994',
    '电视广播Ⅱ': '801995',
}


def normalize_code(code: object) -> str:
    text = str(code or "").strip().upper()
    if "." in text:
        text = text.split(".", 1)[0]
    digits = "".join(character for character in text if character.isdigit())
    if digits:
        return digits.zfill(6)[-6:]
    return text


def select_constituents(rows: list[dict], news_day: date, level2_codes: set[str]) -> list[dict]:
    """丢掉计入日晚于新闻日的股票。二级代码只用来打 in_level2，不新增股票。"""
    chosen = []
    seen = set()
    for row in rows:
        entered = row.get("entered")
        if isinstance(entered, datetime):
            entered = entered.date()
        if entered is not None and entered > news_day:
            continue
        code = normalize_code(row.get("code"))
        if not code or code in seen:
            continue
        seen.add(code)
        chosen.append(
            {
                "code": code,
                "name": str(row.get("name") or ""),
                "in_level2": code in level2_codes,
            }
        )
    return chosen


class FixtureConstituents:
    """样例成份不是真实股票。只用来把交接字段跑通。"""

    def lookup(self, sector: str, sector_l2: str | None, news_day: date) -> tuple[list[dict], str, str]:
        del sector, news_day
        return (
            [
                {"code": "SAMPLE1", "name": "样例成份甲", "in_level2": False},
                {"code": "SAMPLE2", "name": "样例成份乙", "in_level2": bool(sector_l2)},
            ],
            "样例",
            "sample",
        )


class AkshareConstituents:
    def __init__(self, loader=None, codes: dict[str, str] | None = None):
        self.loader = loader or _load_sw_components
        self.codes = SW_INDEX_CODES if codes is None else codes

    def lookup(self, sector: str, sector_l2: str | None, news_day: date) -> tuple[list[dict], str, str]:
        level1 = self.codes.get(sector)
        if not level1:
            return [], "missing", CONSTITUENT_BASIS
        try:
            level1_rows = self.loader(level1)
        except Exception:
            return [], "missing", CONSTITUENT_BASIS
        level2_codes: set[str] = set()
        note = "ok"
        if sector_l2:
            level2 = self.codes.get(sector_l2)
            if not level2:
                note = "level2_missing"
            else:
                try:
                    level2_rows = self.loader(level2)
                    level2_codes = {normalize_code(row.get("code")) for row in level2_rows}
                except Exception:
                    note = "level2_missing"
        return select_constituents(level1_rows, news_day, level2_codes), note, CONSTITUENT_BASIS


def _load_sw_components(symbol: str) -> list[dict]:
    import akshare as ak
    import pandas as pd

    frame = ak.index_component_sw(symbol)
    rows = []
    for record in frame.to_dict("records"):
        entered = record.get("计入日期")
        if entered is None or pd.isna(entered):
            entered = None
        elif isinstance(entered, datetime):
            entered = entered.date()
        rows.append({"code": record.get("证券代码"), "name": record.get("证券名称"), "entered": entered})
    return rows
