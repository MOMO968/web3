"""XNYS sessions; 04:00 premarket is an explicit engineering convention."""

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as xcals

from data.models import Bar, Query, Session, Timeframe

NY = ZoneInfo("America/New_York")


@lru_cache(maxsize=1)
def _calendar():
    # Explicit bounded coverage; do not silently extrapolate exchange holidays.
    return xcals.get_calendar("XNYS", start="1990-01-01", end="2035-12-31")


class USCalendar:
    name = "XNYS"

    @staticmethod
    @lru_cache(maxsize=8192)
    def bounds(day: date, session: Session) -> tuple[datetime, datetime] | None:
        if not date(1990, 1, 1) <= day <= date(2035, 12, 31):
            raise ValueError("XNYS calendar coverage is 1990-2035")
        calendar = _calendar()
        if day < calendar.first_session.date() or day > calendar.last_session.date():
            return None
        if not calendar.is_session(day.isoformat()):
            return None
        opening = calendar.session_open(day.isoformat()).to_pydatetime().astimezone(NY)
        closing = calendar.session_close(day.isoformat()).to_pydatetime().astimezone(NY)
        if session == Session.PREMARKET:
            return datetime.combine(day, time(4), NY), opening
        return opening, closing

    def intervals(self, query: Query) -> tuple[tuple[datetime, datetime], ...]:
        """Only full requested intervals whose scheduled ends are known at as_of."""
        day = query.start.astimezone(NY).date()
        last = (query.end.astimezone(NY) - timedelta(microseconds=1)).date()
        result = []
        while day <= last:
            bounds = self.bounds(day, query.session)
            if bounds:
                start, closing = bounds
                step = (
                    closing - start
                    if query.timeframe == Timeframe.D1
                    else timedelta(minutes=query.timeframe.minutes)
                )
                while start < closing:
                    end = min(start + step, closing)
                    if start >= query.start and end <= query.end and end <= query.as_of:
                        result.append((start, end))
                    start = end
            day += timedelta(days=1)
        return tuple(result)

    def validate_bar(self, bar: Bar) -> None:
        bounds = self.bounds(bar.start.astimezone(NY).date(), bar.session)
        if not bounds:
            raise ValueError("Bar on non-trading day")
        opening, closing = bounds
        if not opening <= bar.start < bar.end <= closing:
            raise ValueError("Bar crosses session boundaries")
        if bar.timeframe == Timeframe.D1:
            if (bar.start, bar.end) != bounds or bar.session != Session.REGULAR:
                raise ValueError("Daily bar must span exactly the regular session")
        else:
            step = timedelta(minutes=bar.timeframe.minutes)
            if (bar.start - opening) % step or bar.end != min(bar.start + step, closing):
                raise ValueError("Bar is not session-anchored")
