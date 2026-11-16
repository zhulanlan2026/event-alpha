from __future__ import annotations

from event_alpha.auxdata import aux_for_card
from event_alpha.library import FactorLibrary
from event_alpha.logic import template_logic
from event_alpha.models import FactorCard, NewsItem, normalize_text
from event_alpha.parsing import enums_ok
from event_alpha.scoring import score_event
from event_alpha.screening import screen_card
from event_alpha.sectors import COMMODITY_SYMBOLS, HORIZON_LABELS


class Pipeline:
    def __init__(self, parser, aux, library: FactorLibrary, logic_writer=None):
        self.parser = parser
        self.aux = aux
        self.library = library
        self.logic_writer = logic_writer

    def run(self, news_items: list[NewsItem]) -> list[FactorCard]:
        cards: list[FactorCard] = []
        for news in news_items:
            if len(normalize_text(news.content)) < 15:
                continue
            if self.library.news_done(news.news_id):
                continue
            try:
                parsed = self.parser.parse(news.content)
            except Exception:
                parsed = None
            if parsed is None or not parsed.items:
                self.library.mark_news(news.news_id)
                continue
            for item in parsed.items:
                cards.append(self._card(news, parsed, item))
            self.library.mark_news(news.news_id)
        return cards

    def _card(self, news: NewsItem, parsed, item) -> FactorCard:
        raw = self.aux.fetch(news.content, parsed.event_type, item.sector, news.news_time.date())
        context = aux_for_card(raw, parsed, item, news.news_time.date())
        in_map = item.sector in COMMODITY_SYMBOLS
        scored = score_event(
            event_type=parsed.event_type,
            direction=item.direction if item.direction in {"positive", "negative", "neutral"} else "neutral",
            confidence=parsed.signal_confidence,
            magnitude_bucket=parsed.magnitude_bucket
            if parsed.magnitude_bucket in {"weak", "mid", "strong"}
            else "weak",
            sector_in_commodity_map=in_map,
            historical_deviation=context.historical_deviation,
            deviation_basis=context.deviation_basis,
        )
        if self.logic_writer is not None:
            try:
                logic, risk = self.logic_writer.write_logic(
                    {
                        "event_summary": parsed.event_summary,
                        "impact_chain": parsed.impact_chain,
                        "sector": item.sector,
                        "direction": item.direction,
                        "data_note": scored["data_note"],
                        "sector_trend_before_news": context.sector_trend_before_news,
                        "signed_score": scored["signed_score"],
                        "consensus_surprise": None,
                    }
                )
            except Exception:
                logic, risk = template_logic(
                    summary=parsed.event_summary,
                    chain=parsed.impact_chain,
                    sector=item.sector,
                    direction=item.direction
                    if item.direction in {"positive", "negative", "neutral"}
                    else "neutral",
                    data_note=scored["data_note"],
                    trend=context.sector_trend_before_news,
                )
        else:
            logic, risk = template_logic(
                summary=parsed.event_summary,
                chain=parsed.impact_chain,
                sector=item.sector,
                direction=item.direction if item.direction in {"positive", "negative", "neutral"} else "neutral",
                data_note=scored["data_note"],
                trend=context.sector_trend_before_news,
            )
        flags = enums_ok(
            parsed.event_type,
            item.direction,
            item.horizon,
            parsed.magnitude_bucket,
            item.sector,
        )
        quant_checked = parsed.event_type == "macro" or (
            parsed.event_type == "supply" and in_map and context.historical_deviation is not None
        )
        reason = screen_card(
            has_alpha_potential=parsed.has_alpha_potential,
            event_type=parsed.event_type,
            sector=item.sector,
            direction=item.direction,
            horizon=item.horizon,
            magnitude_bucket=parsed.magnitude_bucket,
            confidence=parsed.signal_confidence,
            summary=parsed.event_summary,
            chain=parsed.impact_chain,
            logic=logic,
            risk=risk,
            duplicate=self.library.pair_done(news.news_id, item.sector),
            historical_deviation=context.historical_deviation,
            direction_sign=scored["direction_sign"],
            intensity=scored["intensity"],
            quant_checked=quant_checked,
            **flags,
        )
        passed = reason is None
        factor_name = f"{parsed.event_type}_{item.sector}_{item.direction}_{news.news_id[:8]}"
        card = FactorCard(
            news_id=news.news_id,
            news_time=news.news_time.isoformat(timespec="seconds"),
            news_source=news.source,
            event_summary=parsed.event_summary,
            impact_chain=parsed.impact_chain,
            event_type=parsed.event_type,
            sector=item.sector,
            direction=item.direction,
            horizon=item.horizon,
            holding_period=HORIZON_LABELS.get(item.horizon, ""),
            magnitude_bucket=parsed.magnitude_bucket,
            signal_confidence=parsed.signal_confidence,
            historical_deviation=context.historical_deviation,
            deviation_basis=context.deviation_basis,
            consensus_surprise=None,
            sector_trend_before_news=context.sector_trend_before_news,
            data_note=scored["data_note"],
            factor_name=factor_name,
            factor_logic=logic,
            risk_note=risk,
            factor_expr=scored["factor_expr"],
            intensity=scored["intensity"],
            signed_score=scored["signed_score"],
            status="pending_verify" if passed else None,
            reject_reason=reason,
        )
        if passed:
            self.library.append_candidate(card)
        self.library.mark_card(news.news_id, item.sector, reason, factor_name)
        return card
