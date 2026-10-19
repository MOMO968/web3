"""Smoke checks for installed package discovery, not trading behavior."""

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module_name",
    ["data", "indicators", "scanner", "strategies", "risk", "backtest"],
)
def test_installed_module_resolves_to_this_project(module_name):
    module = importlib.import_module(module_name)
    expected_path = Path(__file__).resolve().parents[1] / "src" / module_name / "__init__.py"

    assert module.__file__ is not None
    assert Path(module.__file__).resolve() == expected_path
