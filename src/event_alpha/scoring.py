from __future__ import annotations

import math

from event_alpha.sectors import MAGNITUDE_VALUE


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def trailing_deviation(latest: float, history: list[float]) -> float | None:
    """最新值相对历史窗口的标准化偏离。标准差为 0 时记 0。"""
    if len(history) < 2:
        return None
    mean = sum(history) / len(history)
    variance = sum((item - mean) ** 2 for item in history) / len(history)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return clip((latest - mean) / std, -3.0, 3.0)


def pmi_deviation(latest: float, history: list[float]) -> float:
    """PMI 相对 50，并相对近端历史。历史不足或标准差为 0 时，第二项记 0。"""
    level_gap = clip((latest - 50.0) / 5.0, -3.0, 3.0)
    trail = trailing_deviation(latest, history)
    trail_gap = 0.0 if trail is None else trail
    return 0.5 * level_gap + 0.5 * trail_gap


def window_before_latest(values: list[float], size: int) -> tuple[float, list[float]] | None:
    if len(values) < 3:
        return None
    latest = values[-1]
    history = values[:-1][-size:]
    if len(history) < 2:
        return None
    return latest, history


def futures_deviation(closes_before_news: list[float]) -> float | None:
    window = window_before_latest(closes_before_news, 20)
    if window is None:
        return None
    latest, history = window
    return trailing_deviation(latest, history)


def sector_trend_text(closes: list[float] | None) -> str | None:
    """新闻日之前最多 5 个收盘价的涨跌。不进入分数。"""
    if not closes or len(closes) < 2:
        return None
    window = closes[-5:]
    if window[0] == 0:
        return None
    change = window[-1] / window[0] - 1.0
    return f"新闻前{len(window)}个交易日涨跌 {change:+.2%}"


def _fmt(value: float | None) -> str:
    if value is None:
        return "null"
    return f"{value:.4f}"


def score_event(
    *,
    event_type: str,
    direction: str,
    confidence: float,
    magnitude_bucket: str,
    sector_in_commodity_map: bool,
    historical_deviation: float | None,
    deviation_basis: str | None,
) -> dict:
    """按修订版公式计算强度和带符号分数。中性也给出数值，由初筛丢弃。"""
    sign = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}[direction]
    magnitude = MAGNITUDE_VALUE[magnitude_bucket]
    base = confidence * magnitude
    needs_quant = event_type == "macro" or (
        event_type == "supply" and sector_in_commodity_map
    )
    use_blend = needs_quant and historical_deviation is not None
    quant = None
    if use_blend:
        quant = min(1.0, abs(historical_deviation) / 2.0)
        intensity = 0.6 * base + 0.4 * quant
    else:
        intensity = base

    if needs_quant and historical_deviation is None:
        intensity = min(intensity, 0.45)
        data_note = "quantitative_missing"
    elif needs_quant:
        data_note = "ok"
    else:
        data_note = "qualitative_only"

    if use_blend:
        formula = "intensity = 0.6 * base + 0.4 * quant"
    else:
        formula = "intensity = base"
    factor_expr = (
        "signed_score = direction_sign * intensity; "
        f"direction_sign = {sign:.0f}; "
        f"base = {_fmt(confidence)} * {_fmt(magnitude)}; "
        f"{formula}; quant = {_fmt(quant)}; "
        f"historical_deviation = {_fmt(historical_deviation)}; "
        f"deviation_basis = {deviation_basis or 'null'}"
    )
    return {
        "intensity": intensity,
        "signed_score": sign * intensity,
        "data_note": data_note,
        "factor_expr": factor_expr,
        "direction_sign": sign,
    }
