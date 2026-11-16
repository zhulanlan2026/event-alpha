from datetime import date, datetime
import json

import pytest

from event_alpha.auxdata import FixtureAux
from event_alpha.cli import fixture_news_items
from event_alpha.constituents import SW_INDEX_CODES, AkshareConstituents, select_constituents
from event_alpha.sectors import SW_INDUSTRIES
from event_alpha.handoff import VALUE_RULE
from event_alpha.library import FactorLibrary
from event_alpha.parsing import FIXTURE_EVENTS, FixtureParser
from event_alpha.pipeline import Pipeline
from dataclasses import replace


def run(tmp_path):
    library = FactorLibrary(tmp_path)
    cards = Pipeline(FixtureParser(), FixtureAux(), library).run(fixture_news_items())
    return cards, library


def test_passed_card_hands_midstream_a_factor_definition(tmp_path):
    cards, _library = run(tmp_path)
    policy = cards[0]
    assert policy.value_rule == VALUE_RULE
    assert policy.constituent_note == "样例"
    assert policy.constituent_basis == "sample"
    assert policy.constituents == [
        {"code": "SAMPLE1", "name": "样例成份甲", "in_level2": False},
        {"code": "SAMPLE2", "name": "样例成份乙", "in_level2": False},
    ]
    record = json.loads((tmp_path / "factors" / f"{policy.factor_name}.json").read_text(encoding="utf-8"))
    assert record["名称"] == policy.factor_name
    assert record["逻辑"] == policy.factor_logic
    assert record["表达式"] == policy.factor_expr
    assert record["适用赛道"] == "电力设备"
    assert record["二级行业"] is None
    assert record["持仓周期"] == "5至20日"
    assert record["赋值规则"] == VALUE_RULE
    assert record["成份股"] == policy.constituents
    assert record["状态"] == "pending_verify"


def test_rejected_card_does_not_become_a_factor_file(tmp_path):
    cards, _library = run(tmp_path)
    noise = next(card for card in cards if card.reject_reason == "no_alpha")
    assert noise.constituents == []
    assert noise.constituent_note == "未入库"
    assert noise.value_rule == ""
    names = {path.stem for path in (tmp_path / "factors").glob("*.json")}
    assert noise.factor_name not in names
    assert len(names) == 3


def test_level_two_marks_a_subset_and_keeps_the_same_score(tmp_path):
    content = "国家级产业规划明确加大对电力设备的购置补贴。"
    news = next(item for item in fixture_news_items() if item.content == content)
    source = FIXTURE_EVENTS[content]

    class Parser:
        def parse(self, _content):
            return replace(source, items=[replace(source.items[0], sector_l2="光伏设备")])

    cards = Pipeline(Parser(), FixtureAux(), FactorLibrary(tmp_path)).run([news])
    card = cards[0]
    assert card.signed_score == pytest.approx(0.72)
    assert card.sector_l2 == "光伏设备"
    assert [row["in_level2"] for row in card.constituents] == [False, True]
    record = json.loads((tmp_path / "factors" / f"{card.factor_name}.json").read_text(encoding="utf-8"))
    assert record["二级行业"] == "光伏设备"


def test_published_index_codes_cover_every_level_one():
    assert SW_INDEX_CODES["电力设备"] == "801730"
    assert SW_INDEX_CODES["光伏设备"] == "801735"
    assert all(name in SW_INDEX_CODES for name in SW_INDUSTRIES)


def test_component_rows_drop_stocks_added_after_the_news():
    rows = select_constituents(
        [
            {"code": "600089.SH", "name": "特变电工", "entered": date(2020, 1, 1)},
            {"code": "1", "name": "后进", "entered": date(2026, 12, 1)},
        ],
        news_day=date(2026, 11, 16),
        level2_codes={"600089"},
    )
    assert rows == [{"code": "600089", "name": "特变电工", "in_level2": True}]


def test_missing_component_fetch_does_not_invent_stocks():
    def loader(_symbol):
        raise RuntimeError("down")

    source = AkshareConstituents(loader=loader, codes={"电力设备": "801730"})
    rows, note, basis = source.lookup("电力设备", None, date(2026, 11, 16))
    assert rows == []
    assert note == "missing"
    assert basis == "current_sw_index_entered_by_news_day"


def test_level_two_without_a_published_index_keeps_the_level_one_basket():
    def loader(symbol):
        assert symbol == "801730"
        return [{"code": "600089", "name": "特变电工", "entered": date(2020, 1, 1)}]

    source = AkshareConstituents(loader=loader, codes={"电力设备": "801730"})
    rows, note, _basis = source.lookup("电力设备", "光伏设备", date(2026, 11, 16))
    assert note == "level2_missing"
    assert rows == [{"code": "600089", "name": "特变电工", "in_level2": False}]


def test_level_two_members_are_flagged_inside_the_level_one_basket():
    def loader(symbol):
        tables = {
            "801730": [
                {"code": "600089", "name": "特变电工", "entered": date(2020, 1, 1)},
                {"code": "300274", "name": "阳光电源", "entered": date(2020, 1, 1)},
            ],
            "801735": [
                {"code": "300274", "name": "阳光电源", "entered": date(2020, 1, 1)},
            ],
        }
        return tables[symbol]

    source = AkshareConstituents(
        loader=loader,
        codes={"电力设备": "801730", "光伏设备": "801735"},
    )
    rows, note, basis = source.lookup("电力设备", "光伏设备", datetime(2026, 11, 16).date())
    assert note == "ok"
    assert basis == "current_sw_index_entered_by_news_day"
    assert {row["code"]: row["in_level2"] for row in rows} == {"600089": False, "300274": True}
