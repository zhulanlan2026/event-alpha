from datetime import date

import pytest

from event_alpha.scoring import futures_deviation, pmi_deviation, score_event, sector_trend_text


def test_pmi_deviation_uses_fifty_and_ignores_zero_std():
    deviation = pmi_deviation(49.3, [50.0] * 12)
    assert deviation == pytest.approx(-0.07)


def test_sector_trend_stays_out_of_the_score():
    scored = score_event(
        event_type="policy",
        direction="positive",
        confidence=0.8,
        magnitude_bucket="strong",
        sector_in_commodity_map=False,
        historical_deviation=None,
        deviation_basis=None,
    )
    assert scored["signed_score"] == pytest.approx(0.72)
    assert scored["data_note"] == "qualitative_only"
    assert "新闻前" not in scored["factor_expr"]


def test_missing_mapped_commodity_caps_intensity():
    scored = score_event(
        event_type="supply",
        direction="positive",
        confidence=0.8,
        magnitude_bucket="strong",
        sector_in_commodity_map=True,
        historical_deviation=None,
        deviation_basis=None,
    )
    assert scored["intensity"] == pytest.approx(0.45)
    assert scored["data_note"] == "quantitative_missing"


def test_futures_bar_on_news_day_is_excluded():
    news_day = date(2026, 11, 16)
    from event_alpha.auxdata import closes_before

    closes = closes_before(
        [
            (date(2026, 11, 13), 10.0),
            (date(2026, 11, 14), 11.0),
            (date(2026, 11, 16), 99.0),
        ],
        news_day,
    )
    assert closes == [10.0, 11.0]
    assert futures_deviation(closes) is None


def test_sector_trend_uses_prior_closes_only():
    assert sector_trend_text([100.0, 101.0, 102.0, 101.0, 103.0]) == "新闻前5个交易日涨跌 +3.00%"
