from __future__ import annotations

from datetime import date, datetime, time

from event_alpha.models import NewsItem, make_news_id, normalize_text


def news_from_cls_row(row: dict) -> NewsItem | None:
    content = normalize_text(str(row.get("内容") or ""))
    title = normalize_text(str(row.get("标题") or ""))
    if len(content) < 15:
        content = normalize_text(f"{title} {content}")
    if len(content) < 15:
        return None
    news_time = _cls_time(row.get("发布日期"), row.get("发布时间"))
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
    news_time = _parse_clock(str(row.get("发布时间") or ""))
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
    """财联社电报优先。失败或为空时改用东财快讯。"""
    try:
        items = fetch_cls(limit)
        if items:
            return items
    except Exception:
        items = []
    return fetch_eastmoney(limit)


def _cls_time(day_value, clock_value) -> datetime:
    if isinstance(day_value, datetime):
        day = day_value.date()
    elif isinstance(day_value, date):
        day = day_value
    else:
        day = date.today()
    if isinstance(clock_value, datetime):
        clock = clock_value.time()
    elif isinstance(clock_value, time):
        clock = clock_value
    else:
        parsed = _parse_clock(str(clock_value or ""))
        return parsed if day_value in (None, "") else datetime.combine(day, parsed.time())
    return datetime.combine(day, clock)


def _parse_clock(text: str) -> datetime:
    text = text.strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, pattern)
            if pattern == "%H:%M:%S":
                return datetime.combine(date.today(), parsed.time())
            return parsed
        except ValueError:
            continue
    return datetime.now().replace(microsecond=0)
