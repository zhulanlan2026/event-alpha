import json
from datetime import datetime

import pytest

from event_alpha.auxdata import FixtureAux
from event_alpha.cli import fixture_news_items
from event_alpha.library import FactorLibrary
from event_alpha.models import NewsItem, make_news_id
from event_alpha.parsing import FIXTURE_EVENTS, FixtureParser
from event_alpha.pipeline import Pipeline
from event_alpha.sectors import SW_INDUSTRIES


def run(tmp_path):
    library = FactorLibrary(tmp_path)
    cards = Pipeline(FixtureParser(), FixtureAux(), library).run(fixture_news_items())
    return cards, library


def test_four_fixtures_follow_the_revision(tmp_path):
    cards, library = run(tmp_path)
    assert [card.sector for card in cards] == ["电力设备", "有色金属", "综合", "机械设备"]

    policy, supply, noise, macro = cards
    assert policy.status == "pending_verify"
    assert policy.signed_score == pytest.approx(0.72)
    assert policy.data_note == "qualitative_only"
    assert policy.consensus_surprise is None
    assert "超预期" not in policy.factor_logic + policy.risk_note

    assert supply.status == "pending_verify"
    assert supply.data_note == "quantitative_missing"
    assert supply.intensity == pytest.approx(0.45)

    assert noise.status is None
    assert noise.reject_reason == "no_alpha"

    assert macro.status == "pending_verify"
    assert macro.event_type == "macro"
    assert macro.deviation_basis == "pmi_vs_50_and_trailing_12"
    assert macro.historical_deviation == pytest.approx(-0.07)
    assert macro.consensus_surprise is None
    assert macro.signed_score == pytest.approx(-0.3065)
    assert "超预期" not in macro.factor_logic + macro.risk_note
    assert "+3.00%" not in macro.factor_expr
    assert "+3.00%" in macro.risk_note

    stored = [
        json.loads(line)
        for line in (tmp_path / "candidates.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(stored) == 3
    assert "reject_reason" not in stored[0]
    assert library.candidate_count() == 3


def test_second_run_does_not_append_again(tmp_path):
    _, library = run(tmp_path)
    again = Pipeline(FixtureParser(), FixtureAux(), library).run(fixture_news_items())
    assert again == []
    assert library.candidate_count() == 3


def test_raw_company_words_do_not_reject_a_sector_event(tmp_path):
    content = "某某股份发布的行业减产通知已经超过十五个字，用于检查原文。"
    news = NewsItem(
        news_id=make_news_id("fixture", datetime(2026, 11, 16, 9, 0, 0), content),
        news_time=datetime(2026, 11, 16, 9, 0, 0),
        title=content,
        content=content,
        source="fixture",
    )

    class Parser:
        def parse(self, _content):
            event = FIXTURE_EVENTS["国内主要铜冶炼企业宣布联合减产。"]
            return event

    cards = Pipeline(Parser(), FixtureAux(), FactorLibrary(tmp_path)).run([news])
    assert cards[0].status == "pending_verify"
    assert cards[0].reject_reason is None


def test_short_text_is_dropped(tmp_path):
    content = "太短"
    news = NewsItem(
        news_id="short",
        news_time=datetime(2026, 11, 16, 9, 0, 0),
        title=content,
        content=content,
        source="fixture",
    )
    cards = Pipeline(FixtureParser(), FixtureAux(), FactorLibrary(tmp_path)).run([news])
    assert cards == []


def test_sector_list_is_the_shenwan_level_one_set():
    assert len(SW_INDUSTRIES) == 31
    assert "电力设备" in SW_INDUSTRIES
    assert "有色金属" in SW_INDUSTRIES
