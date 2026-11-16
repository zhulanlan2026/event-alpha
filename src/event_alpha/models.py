from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def make_news_id(source: str, news_time: datetime, content: str) -> str:
    raw = f"{source}|{news_time.isoformat()}|{normalize_text(content)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


@dataclass
class NewsItem:
    news_id: str
    news_time: datetime
    title: str
    content: str
    source: str
    announcement: dict | None = None


@dataclass
class SectorImpact:
    sector: str
    direction: str
    horizon: str
    sector_l2: str | None = None


@dataclass
class ParsedEvent:
    event_summary: str
    impact_chain: str
    event_type: str
    magnitude_bucket: str
    signal_confidence: float
    has_alpha_potential: bool
    items: list[SectorImpact]


@dataclass
class RawSeries:
    """代码取到的数值。kind 为 pmi、level、futures 或 none。"""

    kind: str = "none"
    values: list[float] | None = None
    dates: list[datetime] | None = None
    sector_closes: list[float] | None = None
    series_name: str | None = None


@dataclass
class AuxContext:
    historical_deviation: float | None = None
    deviation_basis: str | None = None
    sector_trend_before_news: str | None = None
    series_name: str | None = None


@dataclass
class FactorCard:
    news_id: str
    news_time: str
    news_source: str
    event_summary: str
    impact_chain: str
    event_type: str
    sector: str
    sector_l2: str | None
    direction: str
    horizon: str
    holding_period: str
    magnitude_bucket: str
    signal_confidence: float
    historical_deviation: float | None
    deviation_basis: str | None
    consensus_surprise: None
    sector_trend_before_news: str | None
    data_note: str
    factor_name: str
    factor_logic: str
    risk_note: str
    factor_expr: str
    value_rule: str
    constituents: list
    constituent_note: str
    constituent_basis: str
    intensity: float
    signed_score: float
    valid_until: str
    is_active: bool
    announcement: dict | None
    result_kind: str
    status: str | None
    reject_reason: str | None

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("reject_reason")
        return data
