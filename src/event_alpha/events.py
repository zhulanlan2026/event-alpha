from __future__ import annotations

from datetime import date, datetime, time

from event_alpha.models import NewsItem, make_news_id, normalize_text
from event_alpha.notices import fetch_timed_notices, parse_clock


def news_from_cls_row(row: dict) -> NewsItem | None:
    content = normalize_text(str(row.get("内容") or ""))
    title = normalize_text(str(row.get("标题") or ""))
    if len(content) < 15:
        content = normalize_text(f"{title} {content}")
    if len(content) < 15:
        return None
    news_time = _cls_time(row.get("发布日期"), row.get("发布时间"))
    if news_time is None:
        return None
    return NewsItem(
        news_id=make_news_id("cls_telegraph", news_time, content),
        news_time=news_time,
        title=title,
        content=content,
        source="cls_telegraph",
    )


def news_from_em_row(row: dict) -> NewsItem | None:
    title = normalize_text(str(row.get("标题") or ""))
    content = normalize_text(str(row.get("摘要") or title))
    if len(content) < 15:
        content = normalize_text(f"{title} {content}")
    if len(content) < 15:
        return None
    news_time = parse_clock(str(row.get("发布时间") or ""))
    if news_time is None:
        return None
    return NewsItem(
        news_id=make_news_id("eastmoney_flash", news_time, content),
        news_time=news_time,
        title=title,
        content=content,
        source="eastmoney_flash",
    )


def fetch_cls(limit: int = 20) -> list[NewsItem]:
    import akshare as ak

    frame = ak.stock_news_global_cls("全部")
    items = []
    for record in frame.to_dict(orient="records"):
        item = news_from_cls_row(record)
        if item is not None:
            items.append(item)
        if len(items) >= limit:
            break
    return items


def fetch_eastmoney(limit: int = 20) -> list[NewsItem]:
    import akshare as ak

    frame = ak.stock_news_global_em()
    items = []
    for record in frame.to_dict(orient="records"):
        item = news_from_em_row(record)
        if item is not None:
            items.append(item)
        if len(items) >= limit:
            break
    return items


def fetch_live(limit: int = 20) -> list[NewsItem]:
    """财联社电报优先，失败时用东财快讯。两类都要有日期和钟点。公告另附带真实发布时间。"""
    try:
        items = fetch_cls(limit)
    except Exception:
        items = []
    if not items:
        try:
            items = fetch_eastmoney(limit)
        except Exception:
            items = []
    try:
        items.extend(fetch_timed_notices(limit))
    except Exception:
        pass
    return items


def _cls_time(day_value, clock_value) -> datetime | None:
    if isinstance(day_value, datetime):
        day = day_value.date()
    elif isinstance(day_value, date):
        day = day_value
    else:
        return None
    if isinstance(clock_value, datetime):
        clock = clock_value.time()
    elif isinstance(clock_value, time):
        clock = clock_value
    else:
        return parse_clock(str(clock_value or ""))
    return datetime.combine(day, clock)
