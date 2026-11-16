from datetime import date, datetime, time

from event_alpha.events import fetch_live, news_from_cls_row, news_from_em_row
from event_alpha.parsing import DeepSeekParser, extract_json
from event_alpha.screening import screen_card


def test_cls_row_combines_date_and_time():
    item = news_from_cls_row(
        {
            "标题": "行业新闻",
            "内容": "国家级产业规划明确加大对电力设备的购置补贴。",
            "发布日期": date(2026, 11, 16),
            "发布时间": time(9, 30, 0),
        }
    )
    assert item is not None
    assert item.source == "cls_telegraph"
    assert item.news_time == datetime(2026, 11, 16, 9, 30, 0)


def test_eastmoney_row_keeps_summary():
    item = news_from_em_row(
        {
            "标题": "宏观",
            "摘要": "国家统计局公布制造业 PMI 为 49.3。",
            "发布时间": "2026-11-16 09:05:00",
        }
    )
    assert item is not None
    assert item.source == "eastmoney_flash"
    assert "PMI" in item.content


def test_live_fetch_falls_back_when_primary_fails(monkeypatch):
    import event_alpha.events as events

    monkeypatch.setattr(events, "fetch_cls", lambda limit=20: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(
        events,
        "fetch_eastmoney",
        lambda limit=20: news_from_em_row(
            {
                "标题": "备源",
                "摘要": "东财快讯正文长度已经超过十五个字。",
                "发布时间": "2026-11-16 10:00:00",
            }
        )
        and [
            news_from_em_row(
                {
                    "标题": "备源",
                    "摘要": "东财快讯正文长度已经超过十五个字。",
                    "发布时间": "2026-11-16 10:00:00",
                }
            )
        ],
    )
    items = fetch_live()
    assert items[0].source == "eastmoney_flash"


def test_direction_conflict_and_company_output():
    common = dict(
        has_alpha_potential=True,
        event_type="macro",
        sector="机械设备",
        direction="positive",
        horizon="short_1_5",
        magnitude_bucket="mid",
        confidence=0.8,
        summary="制造业景气偏弱",
        chain="订单预期下降",
        logic="逻辑说明",
        risk="风险说明",
        allowed_sector=True,
        allowed_event=True,
        allowed_direction=True,
        allowed_horizon=True,
        allowed_magnitude=True,
        duplicate=False,
        historical_deviation=-2.0,
        direction_sign=1.0,
        intensity=0.6,
        quant_checked=True,
    )
    assert screen_card(**common) == "direction_conflicts_with_print"
    common["logic"] = "贵州茅台股份将受益"
    common["historical_deviation"] = -0.1
    assert screen_card(**common) == "company_in_output"


def test_deepseek_json_is_read_without_network():
    payload = {
        "event_summary": "补贴提升设备需求",
        "impact_chain": "订单改善",
        "event_type": "policy",
        "magnitude_bucket": "mid",
        "signal_confidence": 0.6,
        "has_alpha_potential": True,
        "items": [{"sector": "电力设备", "direction": "positive", "horizon": "mid_5_20"}],
    }

    def transport(**_kwargs):
        return "```json\n" + __import__("json").dumps(payload, ensure_ascii=False) + "\n```"

    event = DeepSeekParser("test-key", transport=transport).parse("任意新闻正文超过十五个字。")
    assert event is not None
    assert event.items[0].sector == "电力设备"
    assert extract_json(transport())["event_type"] == "policy"
