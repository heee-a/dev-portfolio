"""TUI 仪表盘数据加载测试。"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software" / "tui_dashboard"))

from dashboard import load_pm, load_weather  # noqa: E402


def test_load_weather():
    wx = load_weather()
    assert wx["city"].nunique() == 18
    assert len(wx) == 39456


def test_load_pm():
    pm = load_pm()
    assert pm is not None and pm["city"].nunique() == 17
