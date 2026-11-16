from __future__ import annotations

from datetime import datetime, timedelta

VALID_DAYS = {"short_1_5": 5, "mid_5_20": 20}


def validity_window(news_time: datetime, horizon: str, now: datetime) -> tuple[datetime | None, bool]:
    """有效期从新闻的日期和时间起算。短期 5 天，中期 20 天。"""
    days = VALID_DAYS.get(horizon)
    if days is None:
        return None, False
    until = news_time + timedelta(days=days)
    return until, now <= until
