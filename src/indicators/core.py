"""Engineering indicator definitions; not attributed to Martin's original parameters."""

from collections.abc import Sequence
from enum import StrEnum
from math import isfinite
from numbers import Integral

from data.models import Adjustment, Bar, DataResult, Session, Timeframe


class EMAClass(StrEnum):
    LEAD = "Lead"
    MEDIOCRE = "Mediocre"
    LAG = "Lag"
    UNKNOWN = "Unknown"


def _period(period: int) -> None:
    if isinstance(period, bool) or not isinstance(period, Integral) or period < 1:
        raise ValueError("period must be a positive integer")


def _value(value: float | None) -> bool:
    if value is None:
        return False
    try:
        if isinstance(value, bool) or not isfinite(value) or value <= 0:
            raise ValueError("Expected finite positive prices or explicit None")
    except TypeError as exc:
        raise ValueError("Expected numeric input or explicit None") from exc
    return True


def ema(values: Sequence[float | None], period: int) -> list[float | None]:
    """SMA seed after period consecutive values, alpha=2/(period+1); gaps reset state."""
    _period(period)
    result = []
    seed = []
    previous = None
    for value in values:
        if not _value(value):
            seed, previous = [], None
            result.append(None)
            continue
        if previous is None:
            seed.append(value)
            if len(seed) == period:
                previous = sum(seed) / period
        else:
            previous += 2 / (period + 1) * (value - previous)
        result.append(previous)
    return result


def adr(bars: Sequence[Bar | None], period: int) -> list[float | None]:
    """Mean 100*(high/low-1) over period consecutive complete regular daily bars."""
    _period(period)
    _daily_bars(bars)
    window = []
    result = []
    for bar in bars:
        if bar is None or not bar.complete:
            window = []
        else:
            window.append(100 * (bar.high / bar.low - 1))
            window = window[-period:]
        result.append(sum(window) / period if len(window) == period else None)
    return result


def dollar_volume(bars: Sequence[Bar | None]) -> list[float | None]:
    """Close * reported share volume (USD); a proxy, not exact traded notional."""
    _daily_bars(bars)
    return [
        b.close * b.volume
        if b is not None and b.complete and b.adjustment == Adjustment.RAW
        else None
        for b in bars
    ]


def classify_ema(ema9: float | None, ema21: float | None, ema50: float | None) -> EMAClass:
    values = (ema9, ema21, ema50)
    if any(v is None for v in values):
        return EMAClass.UNKNOWN
    for value in values:
        _value(value)
    if len(set(values)) < 3:
        return EMAClass.UNKNOWN
    if ema9 > ema21 > ema50:
        return EMAClass.LEAD
    if ema9 < ema21 < ema50:
        return EMAClass.LAG
    return EMAClass.MEDIOCRE


def _daily_bars(bars: Sequence[Bar | None]) -> None:
    present = [b for b in bars if b is not None]
    if any(b.timeframe != Timeframe.D1 or b.session != Session.REGULAR for b in present):
        raise ValueError("Complete regular daily-bar inputs required")
    if len({(b.symbol, b.adjustment, b.currency) for b in present}) > 1:
        raise ValueError("Do not mix symbols or adjustment bases")
    if any(a.start >= b.start for a, b in zip(present, present[1:], strict=False)):
        raise ValueError("Daily bars must be unique and ascending")


def daily_slots(data: DataResult) -> list[Bar | None]:
    """Preserve calendar gaps. Never compact missing dates into a shorter lookback."""
    if data.query.timeframe != Timeframe.D1 or data.query.session != Session.REGULAR:
        raise ValueError("Daily query result required")
    _daily_bars(data.bars)
    by_start = {b.start: b for b in data.bars}
    return [by_start.get(start) for start, _ in data.expected]


def relative_strength(asset: DataResult, benchmark: DataResult, period: int) -> list[float | None]:
    """100*((asset_t/asset_t-n)/(benchmark_t/benchmark_t-n)-1); n+1 aligned slots."""
    _period(period)
    if asset.query.as_of != benchmark.query.as_of:
        raise ValueError("Asset and explicit benchmark must share as_of")
    if asset.query.adjustment != benchmark.query.adjustment:
        raise ValueError("Asset/benchmark adjustment bases must match")
    if asset.query.symbol == benchmark.query.symbol:
        raise ValueError("Explicit distinct benchmark required")
    assets = daily_slots(asset)
    bench_slots = daily_slots(benchmark)
    bench = dict(zip((start for start, _ in benchmark.expected), bench_slots, strict=True))
    aligned = [bench.get(start) for start, _ in asset.expected]
    result = []
    for i in range(len(assets)):
        aa = assets[max(0, i - period) : i + 1]
        bb = aligned[max(0, i - period) : i + 1]
        if i < period or any(b is None or not b.complete for b in aa + bb):
            result.append(None)
        else:
            result.append(100 * ((aa[-1].close / aa[0].close) / (bb[-1].close / bb[0].close) - 1))
    return result


def daily_indicators(
    data: DataResult, *, adr_period: int, ema_periods: tuple[int, ...] = (9, 21, 50, 150)
) -> dict:
    """Calendar-aligned vectors, None for gaps/warmup; no signal or scanner decision."""
    slots = daily_slots(data)
    closes = [b.close if b is not None and b.complete else None for b in slots]
    emas = {period: ema(closes, period) for period in set(ema_periods) | {9, 21, 50}}
    return {
        "starts": tuple(start for start, _ in data.expected),
        "as_of": data.query.as_of,
        "adjustment": data.query.adjustment,
        "provider": data.provider,
        "data_version": data.version,
        "parameters": {"adr_period": adr_period, "ema_periods": tuple(sorted(emas))},
        "dollar_volume_basis": "raw close * shares; unavailable for adjusted bars",
        "ema": emas,
        "adr_percent": adr(slots, adr_period),
        "dollar_volume": dollar_volume(slots),
        "ema_class": [classify_ema(*v) for v in zip(emas[9], emas[21], emas[50], strict=True)],
        "evidence_level": "APPROXIMATION",
    }
