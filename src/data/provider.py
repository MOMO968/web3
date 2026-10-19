"""Replaceable provider contract and immutable local snapshots; no network/vendor binding."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from data.calendar import USCalendar
from data.models import Adjustment, Bar, DataResult, Query, Session, Timeframe, aware


class CapabilityError(ValueError):
    """Provider cannot satisfy the requested data contract."""


@dataclass(frozen=True)
class Capabilities:
    timeframes: frozenset[Timeframe]
    premarket: bool = False
    corporate_actions: bool = False
    historical_metadata: bool = False
    adjustments: frozenset[Adjustment] = frozenset({Adjustment.RAW})

    @property
    def historical_minutes(self) -> bool:
        return Timeframe.M1 in self.timeframes


class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> Capabilities:
        """Declare native or synthesized intervals, never imply unavailable coverage."""

    @abstractmethod
    def history(self, query: Query) -> DataResult:
        """Return only closed bars available by query.as_of, with explicit gaps/provenance."""

    def corporate_actions(self, symbol: str, as_of: datetime):
        raise CapabilityError("CORPORATE_ACTIONS_UNAVAILABLE")

    def metadata(self, symbol: str, as_of: datetime):
        raise CapabilityError("HISTORICAL_METADATA_UNAVAILABLE")


class LocalProvider(MarketDataProvider):
    def __init__(
        self,
        bars: tuple[Bar, ...],
        *,
        capabilities: Capabilities,
        version: str,
        calendar: USCalendar | None = None,
        adjustment_as_of: datetime | None = None,
    ):
        if not version:
            raise ValueError("Snapshot version required")
        if adjustment_as_of is not None:
            aware(adjustment_as_of)
        if capabilities.corporate_actions or capabilities.historical_metadata:
            raise CapabilityError("Local OHLCV snapshot has no actions or metadata adapter")
        self._capabilities = capabilities
        self.calendar = calendar or USCalendar()
        self.version = version
        self.adjustment_as_of = adjustment_as_of
        self.bars = tuple(sorted(bars, key=lambda b: (b.symbol, b.start)))
        seen = set()
        for bar in self.bars:
            self.calendar.validate_bar(bar)
            key = (bar.symbol, bar.start, bar.timeframe, bar.session, bar.adjustment)
            if key in seen:
                raise ValueError("Duplicate bar/revisions require separate snapshots")
            seen.add(key)
            if bar.timeframe not in capabilities.timeframes:
                raise CapabilityError("Snapshot contradicts declared timeframes")
            if bar.session == Session.PREMARKET and not capabilities.premarket:
                raise CapabilityError("Snapshot contradicts premarket capability")
            if bar.adjustment not in capabilities.adjustments:
                raise CapabilityError("Snapshot contradicts adjustment capability")
            if bar.adjustment != Adjustment.RAW and adjustment_as_of is None:
                raise ValueError("Adjusted snapshots require adjustment_as_of")

    @property
    def capabilities(self) -> Capabilities:
        return self._capabilities

    def history(self, query: Query) -> DataResult:
        caps = self.capabilities
        if query.timeframe not in caps.timeframes:
            raise CapabilityError("TIMEFRAME_UNAVAILABLE")
        if query.session == Session.PREMARKET and not caps.premarket:
            raise CapabilityError("PREMARKET_UNAVAILABLE")
        if query.adjustment not in caps.adjustments:
            raise CapabilityError("ADJUSTMENT_UNAVAILABLE")
        if query.adjustment != Adjustment.RAW and (
            self.adjustment_as_of is None or self.adjustment_as_of > query.as_of
        ):
            raise CapabilityError("POINT_IN_TIME_ADJUSTMENTS_UNAVAILABLE")
        expected = self.calendar.intervals(query)
        intervals = set(expected)
        bars = tuple(
            bar
            for bar in self.bars
            if bar.symbol == query.symbol
            and bar.timeframe == query.timeframe
            and bar.session == query.session
            and bar.adjustment == query.adjustment
            and (bar.start, bar.end) in intervals
            and bar.available_at <= query.as_of
        )
        present = {b.start for b in bars}
        missing = tuple(start for start, _ in expected if start not in present)
        issues = []
        if query.end > query.as_of:
            issues.append("REQUEST_EXTENDS_BEYOND_AS_OF")
        if not expected:
            issues.append("NO_COMPLETED_INTERVALS")
        if missing:
            issues.append("MISSING_OR_NOT_YET_AVAILABLE")
        if any(not b.complete for b in bars):
            issues.append("INCOMPLETE_SOURCE_BARS")
        return DataResult(
            query,
            bars,
            expected,
            missing,
            tuple(issues),
            "local",
            self.version,
            self.adjustment_as_of if query.adjustment != Adjustment.RAW else None,
        )
