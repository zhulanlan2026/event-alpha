from __future__ import annotations

import re
from datetime import datetime

from event_alpha.models import NewsItem, make_news_id, normalize_text

_CLOCK = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?::\d+)?")


def parse_clock(text: str) -> datetime | None:
    """只接受同时带日期和钟点的文本。缺任何一段都返回空，不用当前时间填。"""
    matched = _CLOCK.search(text.strip())
    if matched is None:
        return None
    return datetime.strptime(f"{matched.group(1)} {matched.group(2)}", "%Y-%m-%d %H:%M:%S")


def news_from_notice_item(item: dict) -> NewsItem | None:
    """东财公告。AKShare 的表格只留公告日期，真正的钟点在同一条记录的 display_time。"""
    clock = parse_clock(str(item.get("display_time") or ""))
    if clock is None:
        return None
    code = _a_share_code(item.get("codes") or [])
    column = (item.get("columns") or [{}])[0]
    stock_code = str(code.get("stock_code") or "")
    art_code = str(item.get("art_code") or "")
    title = normalize_text(str(item.get("title") or ""))
    if not stock_code or not art_code or len(title) < 4:
        return None
    notice_type = str(column.get("column_name") or "")
    name = str(code.get("short_name") or "")
    announcement = {
        "code": stock_code,
        "name": name,
        "title": title,
        "notice_type": notice_type,
        "notice_date": str(item.get("notice_date") or ""),
        "display_time": clock.isoformat(timespec="seconds"),
        "url": f"https://data.eastmoney.com/notices/detail/{stock_code}/{art_code}.html",
    }
    content = f"{title}。公告类型：{notice_type}。证券代码 {stock_code}。"
    return NewsItem(
        news_id=make_news_id("eastmoney_notice", clock, art_code),
        news_time=clock,
        title=title,
        content=content,
        source="eastmoney_notice",
        announcement=announcement,
    )


def fetch_timed_notices(limit: int = 20) -> list[NewsItem]:
    """只取最新一页重大事项和资产重组。没有 display_time 的不进入。"""
    items: list[NewsItem] = []
    seen: set[str] = set()
    for node in ("5", "6"):
        for raw in _latest_notice_page(node, limit):
            item = news_from_notice_item(raw)
            if item is None or item.news_id in seen:
                continue
            seen.add(item.news_id)
            items.append(item)
            if len(items) >= limit:
                return items
    return items


def _a_share_code(codes: list[dict]) -> dict:
    for entry in codes:
        if str(entry.get("ann_type") or "").startswith("A"):
            return entry
    return codes[0] if codes else {}


def _latest_notice_page(node: str, limit: int) -> list[dict]:
    from akshare.utils import http

    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    params = {
        "sr": "-1",
        "page_size": str(max(1, min(limit, 50))),
        "page_index": "1",
        "ann_type": "A",
        "client_source": "web",
        "f_node": node,
        "s_node": "0",
    }
    payload = http.get(url, params=params).json()
    return list(payload["data"]["list"])
