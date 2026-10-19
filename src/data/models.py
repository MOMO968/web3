"""Immutable OHLCV contracts. Timestamps are aware; intervals are [start, end)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "60m"
    D1 = "1d"

    @property
    def minutes(self) -> int:
        return {self.M1: 1, self.M5: 5, self.M15: 15, self.H1: 60}[self]


class Session(StrEnum):
    PREMARKET = "premarket"
    REGULAR = "regular"


class Adjustment(StrEnum):
    RAW = "raw"
    SPLIT = "split_adjusted"
    TOTAL_RETURN = "total_return_adjusted"


def aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime required")


@dataclass(frozen=True)
class Bar:
    symbol: str
    start: datetime
    end: datetime
    available_at: datetime
    timeframe: Timeframe
    session: Session
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjustment: Adjustment = Adjustment.RAW
    complete: bool = True
    trading_timezone: str = "America/New_York"
    currency: str = "USD"

    def __post_init__(self) -> None:
        for timestamp in (self.start, self.end, self.available_at):
            aware(timestamp)
        if not self.symbol or self.symbol != self.symbol.strip().upper():
            raise ValueError("Use a non-empty uppercase symbol")
        if not isinstance(self.timeframe, Timeframe) or not isinstance(self.session, Session):
            raise ValueError("Explicit timeframe/session enums required")
        if not isinstance(self.adjustment, Adjustment):
            raise ValueError("Explicit adjustment enum required")
        if self.end <= self.start or self.available_at < self.end:
            raise ValueError("Bar must end before it becomes available")
        if self.start.second or self.start.microsecond or self.end.second or self.end.microsecond:
            raise ValueError("Bar boundaries must be minute aligned")
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be a boolean")
        prices = (self.open, self.high, self.low, self.close)
        try:
            valid = all(not isinstance(p, bool) and isfinite(p) and p > 0 for p in prices)
            valid = (
                valid
                and not isinstance(self.volume, bool)
                and isfinite(self.volume)
                and self.volume >= 0
            )
        except TypeError as exc:
            raise ValueError("Missing/non-numeric OHLCV") from exc
        if (
            not valid
            or not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high
        ):
            raise ValueError("Invalid/non-finite OHLCV or price ordering")
        if self.currency != "USD" or self.trading_timezone != "America/New_York":
            raise ValueError("P1 supports USD US equities in America/New_York only")


@dataclass(frozen=True)
class Query:
    symbol: str
    timeframe: Timeframe
    start: datetime
    end: datetime
    as_of: datetime
    session: Session = Session.REGULAR
    adjustment: Adjustment = Adjustment.RAW

    def __post_init__(self) -> None:
        for timestamp in (self.start, self.end, self.as_of):
            aware(timestamp)
        if self.start >= self.end:
            raise ValueError("Query must have a positive half-open range")
        if not self.symbol or self.symbol != self.symbol.strip().upper():
            raise ValueError("Use a non-empty uppercase symbol")
        if not isinstance(self.timeframe, Timeframe) or not isinstance(self.session, Session):
            raise ValueError("Explicit timeframe/session enums required")
        if not isinstance(self.adjustment, Adjustment):
            raise ValueError("Explicit adjustment enum required")
        if self.timeframe == Timeframe.D1 and self.session != Session.REGULAR:
            raise ValueError("Daily bars cover regular sessions only")


@dataclass(frozen=True)
class DataResult:
    query: Query
    bars: tuple[Bar, ...]
    expected: tuple[tuple[datetime, datetime], ...]
    missing: tuple[datetime, ...]
    issues: tuple[str, ...]
    provider: str
    version: str
    # Conservative known-at cutoff for adjusted data; never silently assume point-in-time.
    adjustment_as_of: datetime | None = None

    def __post_init__(self) -> None:
        if not self.provider or not self.version:
            raise ValueError("Provider and data version required")
        starts = [start for start, _ in self.expected]
        if starts != sorted(set(starts)):
            raise ValueError("Expected intervals must be unique and ascending")
        for start, end in self.expected:
            aware(start)
            aware(end)
            if not self.query.start <= start < end <= min(self.query.end, self.query.as_of):
                raise ValueError("Expected interval outside query/as_of")
        intervals = set(self.expected)
        bar_starts = [b.start for b in self.bars]
        if bar_starts != sorted(set(bar_starts)):
            raise ValueError("Result bars must be unique and ascending")
        for bar in self.bars:
            if (
                (bar.start, bar.end) not in intervals
                or bar.available_at > self.query.as_of
                or (bar.symbol, bar.timeframe, bar.session, bar.adjustment)
                != (
                    self.query.symbol,
                    self.query.timeframe,
                    self.query.session,
                    self.query.adjustment,
                )
            ):
                raise ValueError("Result bar violates query or point-in-time contract")
        if self.missing != tuple(t for t in starts if t not in set(bar_starts)):
            raise ValueError("Missing interval metadata is inconsistent")
        if self.query.adjustment != Adjustment.RAW:
            if self.adjustment_as_of is None:
                raise ValueError("Adjusted result requires known-at cutoff")
            aware(self.adjustment_as_of)
            if self.adjustment_as_of > self.query.as_of:
                raise ValueError("Future adjustment cutoff")

    @property
    def complete(self) -> bool:
        return (
            bool(self.expected)
            and not self.issues
            and not self.missing
            and all(b.complete for b in self.bars)
        )

    @property
    def coverage(self) -> float | None:
        if not self.expected:
            return None
        return sum(b.complete for b in self.bars) / len(self.expected)
