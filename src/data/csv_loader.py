"""Strict local CSV adapter; timestamp/correction provenance remains caller-supplied."""

import csv
from datetime import datetime
from pathlib import Path

from data.models import Adjustment, Bar, Session, Timeframe
from data.provider import Capabilities, LocalProvider


def load_csv(
    path: str | Path,
    *,
    capabilities: Capabilities,
    version: str,
    adjustment_as_of: datetime | None = None,
) -> LocalProvider:
    bars = []
    with Path(path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = {
            "symbol",
            "start",
            "end",
            "available_at",
            "timeframe",
            "session",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjustment",
            "complete",
        }
        if not required <= set(reader.fieldnames or ()):
            raise ValueError("Missing OHLCV CSV columns")
        for row in reader:
            try:
                if row["complete"] not in ("true", "false"):
                    raise ValueError("complete must be true/false")
                bars.append(
                    Bar(
                        symbol=row["symbol"],
                        start=datetime.fromisoformat(row["start"]),
                        end=datetime.fromisoformat(row["end"]),
                        available_at=datetime.fromisoformat(row["available_at"]),
                        timeframe=Timeframe(row["timeframe"]),
                        session=Session(row["session"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                        adjustment=Adjustment(row["adjustment"]),
                        complete=row["complete"] == "true",
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError(f"Invalid OHLCV CSV row {reader.line_num}: {exc}") from exc
    return LocalProvider(
        tuple(bars),
        capabilities=capabilities,
        version=version,
        adjustment_as_of=adjustment_as_of,
    )
