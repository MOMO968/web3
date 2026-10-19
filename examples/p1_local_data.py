"""Run from repository root: python examples/p1_local_data.py. Entirely synthetic."""

from datetime import datetime
from pathlib import Path

from data import AggregatingProvider, Capabilities, Query, Timeframe
from data.csv_loader import load_csv

provider = load_csv(
    Path(__file__).with_name("synthetic_minutes.csv"),
    capabilities=Capabilities(frozenset({Timeframe.M1})),
    version="synthetic-demo-v1",
)
result = AggregatingProvider(provider).history(
    Query(
        symbol="DEMO",
        timeframe=Timeframe.M5,
        start=datetime.fromisoformat("2024-03-11T09:30:00-04:00"),
        end=datetime.fromisoformat("2024-03-11T09:35:00-04:00"),
        as_of=datetime.fromisoformat("2024-03-11T09:35:00-04:00"),
    )
)
print("SYNTHETIC DATA — not real market prices")
print(f"provider={result.provider} version={result.version} coverage={result.coverage}")
for bar in result.bars:
    print(
        bar.start.isoformat(),
        bar.end.isoformat(),
        (bar.open, bar.high, bar.low, bar.close, bar.volume),
        "complete=",
        bar.complete,
    )
