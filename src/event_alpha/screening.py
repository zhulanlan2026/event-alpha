from __future__ import annotations

import re

COMPANY_PATTERN = re.compile(r"\d{6}|股份|有限公司")

MIN_INTENSITY = 0.20
CONFLICT_LIMIT = -0.5


def company_in_model_output(*texts: str | None) -> bool:
    blob = "\n".join(text for text in texts if text)
    return COMPANY_PATTERN.search(blob) is not None


def screen_card(
    *,
    has_alpha_potential: bool,
    event_type: str,
    sector: str,
    direction: str,
    horizon: str,
    magnitude_bucket: str,
    confidence: float,
    summary: str,
    chain: str,
    logic: str,
    risk: str,
    allowed_sector: bool,
    allowed_event: bool,
    allowed_direction: bool,
    allowed_horizon: bool,
    allowed_magnitude: bool,
    duplicate: bool,
    historical_deviation: float | None,
    direction_sign: float,
    intensity: float,
    quant_checked: bool,
) -> str | None:
    """命中即拒绝。公司名只检查模型输出，不检查新闻原文。"""
    if (
        not allowed_event
        or not allowed_sector
        or not allowed_direction
        or not allowed_horizon
        or not allowed_magnitude
        or not summary.strip()
        or not chain.strip()
        or not 0.0 <= confidence <= 1.0
        or not math_ok(confidence)
    ):
        return "missing_field"
    if not has_alpha_potential:
        return "no_alpha"
    if direction == "neutral":
        return "neutral"
    if company_in_model_output(summary, chain, logic, risk):
        return "company_in_output"
    if duplicate:
        return "duplicate_news"
    if (
        quant_checked
        and historical_deviation is not None
        and historical_deviation * direction_sign < CONFLICT_LIMIT
    ):
        return "direction_conflicts_with_print"
    if intensity < MIN_INTENSITY:
        return "low_intensity"
    return None


def math_ok(confidence: float) -> bool:
    return confidence == confidence
