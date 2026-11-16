from event_alpha.parsing import PARSE_PROMPT, parsed_event_from_dict
from event_alpha.sectors import SW_INDUSTRIES, SW_LEVEL2, canonical_sector_l2


def test_level_two_list_covers_each_level_one():
    assert len(SW_LEVEL2) == 134
    assert set(SW_LEVEL2.values()) == set(SW_INDUSTRIES)
    assert SW_LEVEL2["光伏设备"] == "电力设备"
    assert SW_LEVEL2["工业金属"] == "有色金属"
    assert SW_LEVEL2["白酒Ⅱ"] == "食品饮料"


def test_level_two_is_kept_only_when_it_belongs_to_the_level_one():
    assert canonical_sector_l2("电力设备", "光伏设备") == "光伏设备"
    assert canonical_sector_l2("电力设备", "  光伏设备 ") == "光伏设备"
    assert canonical_sector_l2("食品饮料", "白酒") == "白酒Ⅱ"
    assert canonical_sector_l2("食品饮料", "白酒Ⅱ") == "白酒Ⅱ"
    assert canonical_sector_l2("电力设备", "") is None
    assert canonical_sector_l2("电力设备", None) is None
    assert canonical_sector_l2("电力设备", "工业金属") is None
    assert canonical_sector_l2("电力设备", "白酒") is None
    assert canonical_sector_l2("电力设备", "不存在的行业") is None


def test_parser_drops_a_level_two_outside_its_level_one():
    event = parsed_event_from_dict(_payload("电力设备", "工业金属"))
    assert event.items[0].sector == "电力设备"
    assert event.items[0].sector_l2 is None


def test_parser_keeps_an_explicit_level_two():
    event = parsed_event_from_dict(_payload("电力设备", "光伏设备"))
    assert event.items[0].sector_l2 == "光伏设备"


def test_parse_prompt_fills_level_two_only_when_the_news_names_it():
    assert "sector_l2" in PARSE_PROMPT
    assert "不得根据一级猜测二级" in PARSE_PROMPT


def test_parser_leaves_level_two_empty_when_the_field_is_absent():
    payload = _payload("电力设备", "光伏设备")
    del payload["items"][0]["sector_l2"]
    event = parsed_event_from_dict(payload)
    assert event.items[0].sector_l2 is None


def _payload(sector: str, sector_l2: str) -> dict:
    return {
        "event_summary": "补贴提升设备需求",
        "impact_chain": "订单改善",
        "event_type": "policy",
        "magnitude_bucket": "mid",
        "signal_confidence": 0.6,
        "has_alpha_potential": True,
        "items": [
            {
                "sector": sector,
                "sector_l2": sector_l2,
                "direction": "positive",
                "horizon": "mid_5_20",
            }
        ],
    }
