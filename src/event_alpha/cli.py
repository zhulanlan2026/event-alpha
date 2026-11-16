from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from event_alpha.auxdata import AkshareAux, FixtureAux
from event_alpha.constituents import AkshareConstituents
from event_alpha.events import fetch_live
from event_alpha.library import FactorLibrary
from event_alpha.models import NewsItem, make_news_id
from event_alpha.parsing import FIXTURE_EVENTS, DeepSeekParser, FixtureParser, parser_from_env
from event_alpha.pipeline import Pipeline

FIXTURE_TIME = datetime(2026, 11, 16, 9, 0, 0)


def fixture_news_items() -> list[NewsItem]:
    items = []
    for content in FIXTURE_EVENTS:
        items.append(
            NewsItem(
                news_id=make_news_id("fixture", FIXTURE_TIME, content),
                news_time=FIXTURE_TIME,
                title=content,
                content=content,
                source="fixture",
            )
        )
    return items


class _LiveAux:
    def __init__(self):
        self.inner = AkshareAux()

    def fetch(self, content, event_type, sector, news_day):
        try:
            return self.inner.fetch(content, event_type, sector, news_day)
        except Exception:
            from event_alpha.models import RawSeries

            return RawSeries(kind="none")


class _ModelLogic:
    def __init__(self, parser: DeepSeekParser):
        self.parser = parser

    def write_logic(self, payload: dict) -> tuple[str, str]:
        try:
            return self.parser.write_logic(payload)
        except Exception:
            from event_alpha.logic import template_logic

            return template_logic(
                summary=payload["event_summary"],
                chain=payload["impact_chain"],
                sector=payload["sector"],
                sector_l2=payload.get("sector_l2"),
                direction=payload["direction"],
                data_note=payload["data_note"],
                trend=payload.get("sector_trend_before_news"),
            )


def build_pipeline(live: bool, out_dir: Path, limit: int = 8) -> tuple[Pipeline, list[NewsItem]]:
    library = FactorLibrary(out_dir)
    if live:
        parser = parser_from_env()
        if parser is None:
            raise SystemExit("实时新闻需要 event-alpha/.env 里的 DEEPSEEK_API_KEY。样例请去掉 --live。")
        pipeline = Pipeline(
            parser,
            _LiveAux(),
            library,
            logic_writer=_ModelLogic(parser),
            constituents=AkshareConstituents(),
        )
        return pipeline, fetch_live(limit)
    pipeline = Pipeline(FixtureParser(), FixtureAux(), library)
    sample = next(
        item
        for item in fixture_news_items()
        if item.content == "国家级产业规划明确加大对电力设备的购置补贴。"
    )
    return pipeline, [sample]


def load_project_env() -> None:
    roots = [Path.cwd(), Path(__file__).resolve().parents[2]]
    for root in roots:
        _load_env_file(root / ".env")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def format_card(card) -> str:
    window = "有效" if card.is_active else "已过期"
    sector = card.sector if not card.sector_l2 else f"{card.sector}/{card.sector_l2}"
    if card.status == "pending_verify":
        return (
            f"{card.result_kind} 入库 {card.news_time} 至 {card.valid_until} {window} "
            f"{sector} {card.direction} {card.signed_score:+.4f} "
            f"{card.data_note} 成份{len(card.constituents)}/{card.constituent_note} {card.factor_name}"
        )
    return f"{card.result_kind} 拒绝 {card.news_time} {window} {sector} {card.reject_reason} {card.factor_name}"


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="事件 Alpha 候选因子")
    parser.add_argument("--live", action="store_true", help="拉取财联社电报和带发布时间的公告")
    parser.add_argument("--limit", type=int, default=8, help="电报和公告各自最多取多少条")
    parser.add_argument("--out", default="out", help="候选库目录")
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    pipeline, news_items = build_pipeline(args.live, out_dir, args.limit)
    cards = pipeline.run(news_items)
    print(f"处理新闻 {len(news_items)} 条，产出卡片 {len(cards)} 张，入库 {pipeline.library.candidate_count()} 张")
    for card in cards:
        print(format_card(card))
    print(f"候选库 {out_dir / 'candidates.jsonl'}")
    return 0
