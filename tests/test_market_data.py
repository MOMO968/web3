from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from data import (
    Adjustment,
    AggregatingProvider,
    Bar,
    Capabilities,
    CapabilityError,
    LocalProvider,
    Query,
    Session,
    Timeframe,
    USCalendar,
)

NY = ZoneInfo("America/New_York")
CAL = USCalendar()


def dt(day="2024-03-11", clock="09:30"):
    return datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=NY)


def minute_bars(day="2024-03-11", clock="09:30", count=5, session=Session.REGULAR):
    start = dt(day, clock)
    return tuple(
        Bar(
            "TEST",
            start + timedelta(minutes=i),
            start + timedelta(minutes=i + 1),
            start + timedelta(minutes=i + 1),
            Timeframe.M1,
            session,
            100 + i,
            102 + i,
            99 + i,
            101 + i,
            10 * (i + 1),
        )
        for i in range(count)
    )


def local(bars, *, premarket=False, adjustments=frozenset({Adjustment.RAW}), **kwargs):
    return LocalProvider(
        tuple(bars),
        capabilities=Capabilities(
            frozenset({b.timeframe for b in bars}) or frozenset({Timeframe.M1}),
            premarket=premarket,
            adjustments=adjustments,
        ),
        version="synthetic-v1",
        **kwargs,
    )


def query(start=None, end=None, as_of=None, timeframe=Timeframe.M1, **kwargs):
    return Query(
        "TEST",
        timeframe,
        start or dt(),
        end or dt(clock="09:35"),
        as_of or end or dt(clock="09:35"),
        **kwargs,
    )


@pytest.mark.parametrize(
    "frame,count", [(Timeframe.M5, 5), (Timeframe.M15, 15), (Timeframe.H1, 60)]
)
def test_ohlcv_aggregation_known_values(frame, count):
    bars = minute_bars(count=count)
    result = AggregatingProvider(local(bars)).history(query(end=bars[-1].end, timeframe=frame))
    assert result.complete and result.coverage == 1
    assert len(result.bars) == 1
    bar = result.bars[0]
    assert (bar.open, bar.high, bar.low, bar.close) == (100, 101 + count, 99, 100 + count)
    assert bar.volume == 10 * count * (count + 1) / 2
    assert bar.start == dt() and bar.end == bars[-1].end


def test_hour_boundaries_and_short_final_bar():
    bars = minute_bars(count=390)
    result = AggregatingProvider(local(bars)).history(
        query(end=dt(clock="16:00"), timeframe=Timeframe.H1)
    )
    assert result.complete
    assert [b.start.astimezone(NY).strftime("%H:%M") for b in result.bars] == [
        "09:30",
        "10:30",
        "11:30",
        "12:30",
        "13:30",
        "14:30",
        "15:30",
    ]
    assert result.bars[-1].end - result.bars[-1].start == timedelta(minutes=30)
    assert result.bars[-1].complete  # Scheduled short bucket is not missing data.
    assert sum(b.volume for b in result.bars) == sum(b.volume for b in bars)


def test_early_close_and_dst_and_holidays():
    for day, utc_hour in [
        (date(2024, 3, 8), 14),
        (date(2024, 3, 11), 13),
        (date(2024, 11, 1), 13),
        (date(2024, 11, 4), 14),
    ]:
        opening, _ = CAL.bounds(day, Session.REGULAR)
        assert opening.astimezone(UTC).hour == utc_hour
        assert opening.minute == 30
    assert CAL.bounds(date(2024, 7, 4), Session.REGULAR) is None
    assert CAL.bounds(date(2024, 3, 10), Session.REGULAR) is None
    for day in ("2024-07-03", "2024-11-29", "2024-12-24"):
        bars = minute_bars(day, count=210)
        result = AggregatingProvider(local(bars)).history(
            query(
                start=bars[0].start,
                end=dt(day, "16:00"),
                timeframe=Timeframe.H1,
            )
        )
        assert result.complete and len(result.bars) == 4
        assert result.bars[-1].end == dt(day, "13:00")
    with pytest.raises(ValueError, match="coverage"):
        CAL.bounds(date(2040, 1, 1), Session.REGULAR)


def test_premarket_never_mixes_with_regular():
    pre = minute_bars(clock="09:25", session=Session.PREMARKET)
    regular = minute_bars()
    provider = AggregatingProvider(local(pre + regular, premarket=True))
    for session, opening in [(Session.PREMARKET, "09:25"), (Session.REGULAR, "09:30")]:
        result = provider.history(
            query(
                start=dt(clock="09:25"),
                timeframe=Timeframe.M5,
                session=session,
            )
        )
        assert len(result.bars) == 1
        assert result.bars[0].start == dt(clock=opening)
        assert result.bars[0].session == session
    with pytest.raises(ValueError, match="session"):
        local([replace(regular[0], session=Session.PREMARKET)], premarket=True)
    with pytest.raises(ValueError):
        local(minute_bars("2024-11-29", "13:00", count=1))


def test_as_of_excludes_open_and_delayed_bars():
    bars = minute_bars(count=10)
    provider = AggregatingProvider(local(bars))
    result = provider.history(
        query(end=dt(clock="09:40"), as_of=dt(clock="09:34"), timeframe=Timeframe.M5)
    )
    assert not result.bars and not result.complete
    result = provider.history(
        query(end=dt(clock="09:40"), as_of=dt(clock="09:35"), timeframe=Timeframe.M5)
    )
    assert len(result.bars) == 1 and result.bars[0].close == 105
    delayed = replace(bars[4], available_at=dt(clock="10:00"))
    provider = AggregatingProvider(local(bars[:4] + (delayed,) + bars[5:]))
    result = provider.history(query(timeframe=Timeframe.M5))
    assert result.bars[0].complete is False and result.coverage == 0
    assert result.bars[0].close == 104
    ready = provider.history(query(timeframe=Timeframe.M5, as_of=dt(clock="10:00")))
    assert ready.complete and ready.bars[0].close == 105
    assert ready.bars[0].available_at == dt(clock="10:00")


def test_missing_data_not_filled_or_marked_complete():
    bars = minute_bars(count=15)
    provider = AggregatingProvider(local(bars[:2] + bars[3:5] + bars[10:]))
    result = provider.history(query(end=dt(clock="09:45"), timeframe=Timeframe.M5))
    assert len(result.bars) == 2
    assert result.missing == (dt(clock="09:35"),)
    assert not result.bars[0].complete and result.bars[1].complete
    assert result.coverage == pytest.approx(1 / 3)
    assert not result.complete
    empty = local(()).history(query())
    assert len(empty.missing) == 5 and empty.coverage == 0


def test_source_incomplete_and_half_open_ranges():
    bars = minute_bars()
    result = local([replace(bars[0], complete=False)] + list(bars[1:])).history(query())
    assert not result.complete and result.coverage == 0.8
    assert len(local(bars).history(query(end=dt(clock="09:31"))).bars) == 1
    # Never return a bar that extends beyond the requested end, even if as_of is later.
    result = AggregatingProvider(local(bars)).history(
        query(
            end=dt(clock="09:34"),
            as_of=dt(clock="10:00"),
            timeframe=Timeframe.M5,
        )
    )
    assert not result.bars and result.coverage is None


@pytest.mark.parametrize(
    "changes",
    [
        {"close": None},
        {"high": float("nan")},
        {"low": 0},
        {"volume": -1},
        {"open": 200},
        {"volume": float("inf")},
        {"symbol": "test"},
        {"start": datetime(2024, 3, 11, 9, 30)},
        {"end": dt()},
        {"available_at": dt()},
        {"start": dt().replace(second=1)},
    ],
)
def test_invalid_ohlcv_rejected(changes):
    with pytest.raises(ValueError):
        replace(minute_bars()[0], **changes)


def test_duplicates_misalignment_and_capabilities():
    bars = minute_bars()
    with pytest.raises(ValueError, match="Duplicate"):
        local(bars + (bars[0],))
    with pytest.raises(ValueError, match="session-anchored"):
        local([replace(bars[0], timeframe=Timeframe.M5)])
    provider = local(bars)
    assert provider.capabilities.historical_minutes
    for method in (provider.metadata, provider.corporate_actions):
        with pytest.raises(CapabilityError):
            method("TEST", dt())
    with pytest.raises(CapabilityError, match="PREMARKET_UNAVAILABLE"):
        provider.history(query(session=Session.PREMARKET))
    with pytest.raises(CapabilityError, match="TIMEFRAME_UNAVAILABLE"):
        provider.history(query(timeframe=Timeframe.D1))
    with pytest.raises(CapabilityError, match="ADJUSTMENT_UNAVAILABLE"):
        provider.history(query(adjustment=Adjustment.SPLIT))


def test_adjusted_snapshot_cannot_leak_future_adjustment():
    bars = tuple(replace(b, adjustment=Adjustment.SPLIT) for b in minute_bars())
    caps = frozenset({Adjustment.SPLIT})
    with pytest.raises(ValueError, match="adjustment_as_of"):
        local(bars, adjustments=caps)
    provider = local(bars, adjustments=caps, adjustment_as_of=dt(clock="10:00"))
    with pytest.raises(CapabilityError, match="POINT_IN_TIME"):
        provider.history(query(adjustment=Adjustment.SPLIT))
    result = provider.history(query(adjustment=Adjustment.SPLIT, as_of=dt(clock="10:00")))
    assert result.complete and result.adjustment_as_of == dt(clock="10:00")


def test_utc_and_new_york_queries_return_identical_data():
    provider = local(minute_bars())
    q = query()
    utc = replace(
        q, start=q.start.astimezone(UTC), end=q.end.astimezone(UTC), as_of=q.as_of.astimezone(UTC)
    )
    assert provider.history(q).bars == provider.history(utc).bars
    assert provider.history(q).expected == provider.history(utc).expected


def test_mutating_future_prices_does_not_change_past_results():
    bars = minute_bars(count=10)
    changed = bars[:5] + tuple(replace(b, high=10000, close=9999) for b in bars[5:])
    q = query(end=dt(clock="09:40"), as_of=dt(clock="09:35"), timeframe=Timeframe.M5)
    assert AggregatingProvider(local(bars)).history(q) == AggregatingProvider(
        local(changed)
    ).history(q)


def test_overnight_queries_do_not_join_sessions():
    friday = minute_bars("2024-03-08", "15:55")
    monday = minute_bars("2024-03-11")
    result = AggregatingProvider(local(friday + monday)).history(
        query(
            start=friday[0].start,
            end=monday[-1].end,
            timeframe=Timeframe.M5,
        )
    )
    assert result.complete and len(result.bars) == 2
    assert [b.end for b in result.bars] == [friday[-1].end, monday[-1].end]
    holiday = local(()).history(query(start=dt("2024-07-04"), end=dt("2024-07-04", "16:00")))
    assert not holiday.complete and holiday.coverage is None and not holiday.missing
    assert CAL.bounds(date(1990, 1, 1), Session.REGULAR) is None


def test_local_snapshot_csv_and_bad_input(tmp_path):
    from pathlib import Path

    from data.csv_loader import load_csv

    caps = Capabilities(frozenset({Timeframe.M1}))
    path = Path(__file__).resolve().parents[1] / "examples" / "synthetic_minutes.csv"
    provider = load_csv(path, capabilities=caps, version="csv-fixture")
    result = AggregatingProvider(provider).history(
        replace(query(timeframe=Timeframe.M5), symbol="DEMO")
    )
    assert result.complete
    b = result.bars[0]
    assert (b.open, b.high, b.low, b.close, b.volume) == (100, 106, 99, 105, 150)
    invalid = tmp_path / "bad.csv"
    invalid.write_text(path.read_text().replace(",raw,true", ",raw,yes"))
    with pytest.raises(ValueError, match="CSV row 2"):
        load_csv(invalid, capabilities=caps, version="invalid")
    invalid.write_text("symbol,open\nTEST,1\n")
    with pytest.raises(ValueError, match="columns"):
        load_csv(invalid, capabilities=caps, version="invalid")


def test_result_contract_rejects_future_or_mismatched_rows():
    bars = minute_bars()
    result = local(bars).history(query())
    with pytest.raises(ValueError, match="point-in-time"):
        replace(result, bars=(replace(bars[0], available_at=dt(clock="10:00")),) + bars[1:])
    with pytest.raises(ValueError, match="point-in-time"):
        replace(result, bars=(replace(bars[0], symbol="OTHER"),) + bars[1:])
    with pytest.raises(ValueError, match="inconsistent"):
        replace(result, missing=(bars[0].start,))
    with pytest.raises(ValueError):
        query(start=dt(clock="10:00"), end=dt())
    with pytest.raises(ValueError):
        query(timeframe=Timeframe.D1, session=Session.PREMARKET)


def test_unsupported_provider_capabilities_are_not_claimed():
    with pytest.raises(CapabilityError, match="no actions"):
        LocalProvider(
            (),
            capabilities=Capabilities(frozenset({Timeframe.M1}), corporate_actions=True),
            version="test",
        )
    with pytest.raises(CapabilityError, match="requires historical"):
        AggregatingProvider(
            LocalProvider((), capabilities=Capabilities(frozenset({Timeframe.D1})), version="test")
        )
    with pytest.raises(ValueError):
        replace(minute_bars()[0], complete="true")
    with pytest.raises(ValueError):
        replace(minute_bars()[0], close=True)


def test_exclusive_end_at_calendar_coverage_boundary():
    q = query(
        start=dt("2035-12-31"), end=dt("2036-01-01", "00:00"), as_of=dt("2036-01-01", "00:00")
    )
    intervals = CAL.intervals(q)
    assert len(intervals) == 390
    assert intervals[-1][1] == dt("2035-12-31", "16:00")
