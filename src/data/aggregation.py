"""Session-anchored 1m -> 5m/15m/60m aggregation, without future/open buckets."""

from dataclasses import replace

from data.calendar import USCalendar
from data.models import Bar, DataResult, Query, Timeframe
from data.provider import Capabilities, CapabilityError, MarketDataProvider


class AggregatingProvider(MarketDataProvider):
    def __init__(self, source: MarketDataProvider, calendar: USCalendar | None = None):
        if Timeframe.M1 not in source.capabilities.timeframes:
            raise CapabilityError("Aggregation requires historical 1m bars")
        self.source = source
        self.calendar = calendar or USCalendar()

    @property
    def capabilities(self) -> Capabilities:
        return replace(
            self.source.capabilities,
            timeframes=self.source.capabilities.timeframes
            | frozenset({Timeframe.M5, Timeframe.M15, Timeframe.H1}),
            # Actions/metadata are not implemented by this adapter.
            corporate_actions=False,
            historical_metadata=False,
        )

    def history(self, query: Query) -> DataResult:
        if query.timeframe not in (Timeframe.M5, Timeframe.M15, Timeframe.H1):
            return self.source.history(query)
        expected = self.calendar.intervals(query)
        raw = self.source.history(replace(query, timeframe=Timeframe.M1))
        by_start = {b.start: b for b in raw.bars}
        bars = []
        for start, end in expected:
            minute_query = replace(query, timeframe=Timeframe.M1, start=start, end=end)
            minutes = self.calendar.intervals(minute_query)
            children = [by_start[t] for t, _ in minutes if t in by_start]
            if not children:
                continue
            bars.append(
                Bar(
                    symbol=query.symbol,
                    start=start,
                    end=end,
                    available_at=max(end, *(b.available_at for b in children)),
                    timeframe=query.timeframe,
                    session=query.session,
                    open=children[0].open,
                    high=max(b.high for b in children),
                    low=min(b.low for b in children),
                    close=children[-1].close,
                    volume=sum(b.volume for b in children),
                    adjustment=query.adjustment,
                    complete=len(children) == len(minutes) and all(b.complete for b in children),
                )
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
            issues.append("INCOMPLETE_CONSTITUENTS")
        return DataResult(
            query,
            tuple(bars),
            expected,
            missing,
            tuple(issues),
            f"aggregate({raw.provider})",
            raw.version,
            raw.adjustment_as_of,
        )
