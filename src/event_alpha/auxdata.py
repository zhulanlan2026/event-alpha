from __future__ import annotations

from datetime import date, datetime

from event_alpha.models import AuxContext, ParsedEvent, RawSeries, SectorImpact
from event_alpha.scoring import futures_deviation, pmi_deviation, sector_trend_text, trailing_deviation
from event_alpha.sectors import COMMODITY_SYMBOLS, EASTMONEY_INDUSTRY


def select_macro_series(text: str) -> str | None:
    if "PMI" in text:
        return "pmi"
    if "CPI" in text or "居民消费价格" in text:
        return "cpi"
    if "PPI" in text or "工业品出厂价格" in text:
        return "ppi"
    if "工业增加值" in text:
        return "industrial"
    return None


def closes_before(rows: list[tuple[date, float]], news_day: date) -> list[float]:
    ordered = sorted((item_date, price) for item_date, price in rows if item_date < news_day)
    return [price for _, price in ordered]


def build_context(
    *,
    event_type: str,
    sector: str,
    news_day: date,
    raw: RawSeries,
) -> AuxContext:
    deviation = None
    basis = None
    if event_type == "macro" and raw.kind == "pmi" and raw.values:
        history = raw.values[:-1][-12:]
        deviation = pmi_deviation(raw.values[-1], history)
        basis = "pmi_vs_50_and_trailing_12"
    elif event_type == "macro" and raw.kind == "level" and raw.values:
        window = raw.values[:-1][-12:]
        deviation = trailing_deviation(raw.values[-1], window)
        basis = "trailing_12_mean"
    elif event_type == "supply" and sector in COMMODITY_SYMBOLS and raw.kind == "futures":
        if raw.dates and raw.values and len(raw.dates) == len(raw.values):
            pairs = [
                (item.date() if isinstance(item, datetime) else item, price)
                for item, price in zip(raw.dates, raw.values)
            ]
            closes = closes_before(pairs, news_day)
        else:
            closes = list(raw.values or [])
        deviation = futures_deviation(closes)
        basis = "futures_trailing_20" if deviation is not None else None

    return AuxContext(
        historical_deviation=deviation,
        deviation_basis=basis,
        sector_trend_before_news=sector_trend_text(raw.sector_closes),
        series_name=raw.series_name,
    )


class FixtureAux:
    """样例默认不访问网络。PMI 使用固定公布序列，铜价留空。"""

    def fetch(self, content: str, event_type: str, sector: str, news_day: date | None = None) -> RawSeries:
        if "PMI" in content:
            return RawSeries(
                kind="pmi",
                values=[50.0] * 12 + [49.3],
                series_name="macro_china_pmi",
                sector_closes=[100.0, 101.0, 102.0, 101.0, 103.0],
            )
        if event_type == "supply" and sector in COMMODITY_SYMBOLS:
            return RawSeries(kind="futures", values=[], series_name=COMMODITY_SYMBOLS[sector])
        return RawSeries(kind="none")


class AkshareAux:
    def fetch(self, content: str, event_type: str, sector: str, news_day: date) -> RawSeries:
        raw = RawSeries(kind="none")
        if event_type == "macro":
            kind = select_macro_series(content)
            values, name = _load_macro(kind)
            if values:
                raw.kind = "pmi" if kind == "pmi" else "level"
                raw.values = values
                raw.series_name = name
        elif event_type == "supply" and sector in COMMODITY_SYMBOLS:
            symbol = COMMODITY_SYMBOLS[sector]
            dates, values = _load_futures(symbol)
            raw.kind = "futures"
            raw.dates = dates
            raw.values = values
            raw.series_name = symbol
        board = EASTMONEY_INDUSTRY.get(sector)
        if board:
            raw.sector_closes = _load_sector_closes(board, news_day)
        return raw


def _load_macro(kind: str | None) -> tuple[list[float] | None, str | None]:
    if kind is None:
        return None, None
    import akshare as ak

    loaders = {
        "pmi": ("macro_china_pmi", "制造业-指数"),
        "cpi": ("macro_china_cpi", "全国-同比增长"),
        "ppi": ("macro_china_ppi", "当月同比增长"),
        "industrial": ("macro_china_industrial_value_added", "同比增长"),
    }
    function_name, column = loaders[kind]
    frame = getattr(ak, function_name)()
    values = [float(item) for item in frame[column].dropna().tolist()]
    values.reverse()
    return values, function_name


def _load_futures(symbol: str) -> tuple[list[datetime], list[float]]:
    import akshare as ak

    frame = ak.futures_main_sina(symbol=symbol, start_date="20200101", end_date="22220101")
    dates = list(frame["日期"])
    closes = [float(item) for item in frame["收盘价"].tolist()]
    return dates, closes


def _load_sector_closes(board: str, news_day: date) -> list[float] | None:
    import akshare as ak

    try:
        start = "20200101"
        end = news_day.strftime("%Y%m%d")
        frame = ak.stock_board_industry_hist_em(
            symbol=board, start_date=start, end_date=end, period="日k", adjust=""
        )
    except Exception:
        return None
    if frame is None or frame.empty or "收盘" not in frame.columns:
        return None
    closes: list[float] = []
    for _, row in frame.iterrows():
        if "日期" in frame.columns:
            raw_day = row["日期"]
            if isinstance(raw_day, datetime):
                row_day = raw_day.date()
            else:
                row_day = datetime.strptime(str(raw_day)[:10], "%Y-%m-%d").date()
            if row_day >= news_day:
                continue
        closes.append(float(row["收盘"]))
    return closes[-5:] or None


def aux_for_card(raw: RawSeries, event: ParsedEvent, item: SectorImpact, news_day: date) -> AuxContext:
    return build_context(
        event_type=event.event_type,
        sector=item.sector,
        news_day=news_day,
        raw=raw,
    )
