from dataclasses import replace
from datetime import date

import pytest

from data import Bar, Capabilities, LocalProvider, Query, Session, Timeframe, USCalendar
from indicators import (
    EMAClass,
    adr,
    classify_ema,
    daily_indicators,
    dollar_volume,
    ema,
    relative_strength,
)

CAL = USCalendar()


def days(prices=(10, 12, 15), symbol="TEST"):
    result = []
    for day, price in zip((4, 5, 6, 7, 8), prices, strict=False):
        start, end = CAL.bounds(date(2024, 3, day), Session.REGULAR)
        result.append(
            Bar(
                symbol,
                start,
                end,
                end,
                Timeframe.D1,
                Session.REGULAR,
                price,
                price * 1.2,
                price,
                price,
                100,
            )
        )
    return tuple(result)


def history(bars, *, start=None, end=None, as_of=None, symbol="TEST"):
    provider = LocalProvider(
        tuple(bars),
        capabilities=Capabilities(frozenset({Timeframe.D1})),
        version="indicator-fixture",
    )
    return provider.history(
        Query(
            symbol, Timeframe.D1, start or bars[0].start, end or bars[-1].end, as_of or bars[-1].end
        )
    )


@pytest.mark.parametrize("period", [9, 21, 50, 150])
def test_ema_periods_seed_and_known_recurrence(period):
    result = ema(list(range(1, period + 2)), period)
    assert result[: period - 1] == [None] * (period - 1)
    assert result[period - 1] == (period + 1) / 2
    assert result[period] == pytest.approx((period + 1) / 2 + 1)


def test_ema_exact_values_prefix_invariance_and_gap_warmup():
    assert ema([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4]
    assert ema([1, 2, 3, None, 4, 5, 6], 3) == [None, None, 2, None, None, None, 5]
    assert ema([1, 2, 3, 4, 10000], 3)[:4] == ema([1, 2, 3, 4], 3)
    assert ema([], 3) == []


@pytest.mark.parametrize("period", [0, -1, 2.5, True])
def test_invalid_windows(period):
    with pytest.raises(ValueError):
        ema([1, 2], period)
    with pytest.raises(ValueError):
        adr([], period)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0, -1, "missing"])
def test_invalid_indicator_input(bad):
    with pytest.raises(ValueError):
        ema([1, bad], 2)


def test_adr_numerical_definition_and_gaps():
    a, b, c = days()
    b = replace(b, high=18)  # (18/12-1)*100 = 50%; first day = 20%.
    assert adr([a, b, c], 2) == pytest.approx([None, 35, 35], nan_ok=True)
    assert adr([a, None, c], 2) == [None, None, None]
    assert adr([a, replace(b, complete=False), c], 2) == [None, None, None]
    assert dollar_volume([a, None, c]) == [1000, None, 1500]


@pytest.mark.parametrize(
    "values,expected",
    [
        ((3, 2, 1), EMAClass.LEAD),
        ((1, 2, 3), EMAClass.LAG),
        ((2, 3, 1), EMAClass.MEDIOCRE),
        ((2, 1, 3), EMAClass.MEDIOCRE),
        ((1, 1, 2), EMAClass.UNKNOWN),
        ((2, 1, 2), EMAClass.UNKNOWN),
        ((None, 2, 1), EMAClass.UNKNOWN),
    ],
)
def test_daily_ema_classes(values, expected):
    assert classify_ema(*values) == expected


def test_daily_pipeline_retains_missing_session_and_resets_indicators():
    bars = days((10, 12, 15, 18, 20))
    result = history(bars[:1] + bars[2:])
    assert len(result.missing) == 1
    indicators = daily_indicators(result, adr_period=2, ema_periods=(2,))
    assert indicators["ema"][2] == [None, None, None, 16.5, pytest.approx(18.8333333333)]
    assert indicators["adr_percent"][:3] == [None, None, None]
    assert indicators["ema_class"] == [EMAClass.UNKNOWN] * 5
    assert indicators["evidence_level"] == "APPROXIMATION"


def test_relative_strength_known_returns_and_missing_benchmark():
    asset = history(days((100, 110, 120)))
    qqq = history(days((100, 105, 110), "QQQ"), symbol="QQQ")
    result = relative_strength(asset, qqq, 2)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(100 * (1.2 / 1.1 - 1))
    qqq_bars = days((100, 105, 110), "QQQ")
    missing = history((qqq_bars[0], qqq_bars[2]), symbol="QQQ")
    assert relative_strength(asset, missing, 2) == [None, None, None]
    with pytest.raises(ValueError, match="as_of"):
        relative_strength(asset, history(qqq_bars, symbol="QQQ", as_of=qqq_bars[1].end), 2)


def test_daily_bar_never_available_before_close():
    bars = days()
    result = history(bars, as_of=bars[-1].start)
    assert len(result.bars) == 2
    assert all(b.end <= result.query.as_of for b in result.bars)
    before = daily_indicators(result, adr_period=2)
    changed = bars[:2] + (replace(bars[-1], high=1000, close=1000),)
    assert daily_indicators(history(changed, as_of=bars[-1].start), adr_period=2) == before


def test_daily_inputs_reject_order_symbol_and_timeframe_mixing():
    a, b, _ = days()
    for invalid in (
        [b, a],
        [a, a],
        [a, replace(b, symbol="OTHER")],
        [replace(a, timeframe=Timeframe.M1)],
    ):
        with pytest.raises(ValueError):
            adr(invalid, 2)


def test_adjusted_dollar_volume_not_mixed_with_raw_share_volume():
    from data import Adjustment

    bars = days()
    assert dollar_volume([replace(bars[0], adjustment=Adjustment.SPLIT)]) == [None]
    with pytest.raises(ValueError, match="adjustment bases"):
        adr([bars[0], replace(bars[1], adjustment=Adjustment.SPLIT)], 2)


def test_daily_ema_class_after_actual_50_day_warmup():
    from datetime import timedelta

    bars = []
    day = date(2024, 1, 2)
    while len(bars) < 51:
        bounds = CAL.bounds(day, Session.REGULAR)
        if bounds:
            start, end = bounds
            price = 100 + len(bars)
            bars.append(
                Bar(
                    "TEST",
                    start,
                    end,
                    end,
                    Timeframe.D1,
                    Session.REGULAR,
                    price,
                    price + 1,
                    price - 1,
                    price,
                    100,
                )
            )
        day += timedelta(days=1)
    result = daily_indicators(history(bars), adr_period=3)
    assert result["ema_class"][:49] == [EMAClass.UNKNOWN] * 49
    assert result["ema_class"][49:] == [EMAClass.LEAD, EMAClass.LEAD]
    assert result["ema"][150] == [None] * 51


def test_rs_explicit_benchmark_and_adjustment_contracts():
    from data import Adjustment

    asset = history(days())
    with pytest.raises(ValueError, match="distinct benchmark"):
        relative_strength(asset, asset, 2)
    qqq = history(days((100, 105, 110), "QQQ"), symbol="QQQ")
    adjusted = replace(
        qqq,
        query=replace(qqq.query, adjustment=Adjustment.SPLIT),
        bars=tuple(replace(b, adjustment=Adjustment.SPLIT) for b in qqq.bars),
        adjustment_as_of=qqq.query.as_of,
    )
    with pytest.raises(ValueError, match="adjustment bases"):
        relative_strength(asset, adjusted, 2)
