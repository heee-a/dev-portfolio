"""TUI 终端仪表盘：用 rich 渲染真实采集数据的终端可视化面板。

数据来自 data-portfolio（气象）与 ml-bench（空气质量）的真实采集快照。
运行:
    python dashboard.py              # 渲染一次
    python dashboard.py --watch 5    # 每 5 秒刷新（模拟实时面板）
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from rich import box
from rich.bar import Bar
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

C = Console()


def load_weather() -> pd.DataFrame:
    return pd.read_csv(DATA / "weather_daily.csv", parse_dates=["date"])


def load_pm() -> pd.DataFrame | None:
    p = DATA / "pm_daily.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None


def kpi_panel(wx: pd.DataFrame, pm: pd.DataFrame | None) -> Panel:
    grid = Table.grid(padding=(0, 3))
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row("[b]城市数[/b]", f"{wx['city'].nunique()} 城")
    grid.add_row("[b]气象天数[/b]", f"{len(wx):,} 天")
    grid.add_row("[b]时间范围[/b]", f"{wx['date'].min():%Y-%m-%d} ~ {wx['date'].max():%Y-%m-%d}")
    if pm is not None:
        grid.add_row("[b]PM2.5 记录[/b]", f"{len(pm):,} 城市-日")
        grid.add_row("[b]PM2.5 总体均值[/b]", f"{pm['pm25'].mean():.1f} µg/m³")
    return Panel(grid, title="数据概览", box=box.ROUNDED, expand=False)


def ranking_table(wx: pd.DataFrame) -> Panel:
    annual = (wx.groupby("city")["tmean"].mean().sort_values(ascending=False)
              .head(10).round(1))
    table = Table(title="年均温 Top10（℃）", box=box.SIMPLE_HEAD)
    table.add_column("城市")
    table.add_column("年均温", justify="right")
    table.add_column("相对最暖城市", justify="left")
    top = annual.max()
    for city, v in annual.items():
        table.add_row(str(city), f"{v:.1f}",
                      Bar(size=20, begin=0, end=max(1, round(v / top * 20)),
                          color="cyan"))
    return Panel(table, box=box.ROUNDED)


def pm_table(pm: pd.DataFrame | None) -> Panel:
    if pm is None:
        return Panel(Text("缺少 pm_daily.csv"), title="空气质量", box=box.ROUNDED)
    annual = (pm.groupby(["city", "group"])["pm25"].mean()
              .sort_values(ascending=False).head(8).round(1))
    table = Table(title="年均 PM2.5 Top8（µg/m³）", box=box.SIMPLE_HEAD)
    table.add_column("城市")
    table.add_column("分组")
    table.add_column("年均", justify="right")
    table.add_column("相对最重", justify="left")
    top = annual.max()
    for (city, group), v in annual.items():
        color = "red" if v > 60 else "yellow" if v > 35 else "green"
        table.add_row(str(city), str(group), f"{v:.1f}",
                      Bar(size=20, begin=0, end=max(1, round(v / top * 20)),
                          color=color))
    return Panel(table, box=box.ROUNDED)


def monthly_bars(wx: pd.DataFrame, city: str = "北京") -> Panel:
    m = (wx[wx["city"] == city].groupby(wx["date"].dt.month)["tmean"].mean())
    grid = Table.grid(padding=(0, 1))
    grid.add_column()
    grid.add_column()
    for month, temp in m.items():
        bar = Bar(size=28, begin=0,
                  end=max(1, round((temp - m.min() + 1) / (m.max() - m.min() + 1) * 28)),
                  color="magenta")
        grid.add_row(f"{month:>2}月 {temp:>6.1f}℃", bar)
    return Panel(grid, title=f"{city} 月均温季节曲线", box=box.ROUNDED)


def render() -> None:
    wx = load_weather()
    pm = load_pm()
    layout = Layout()
    layout.split_column(Layout(name="top", ratio=1), Layout(name="bottom", ratio=1))
    layout["top"].split_row(Layout(name="kpi"), Layout(name="rank"))
    layout["bottom"].split_row(Layout(name="pm"), Layout(name="season"))
    layout["top"]["kpi"].update(kpi_panel(wx, pm))
    layout["top"]["rank"].update(ranking_table(wx))
    layout["bottom"]["pm"].update(pm_table(pm))
    layout["bottom"]["season"].update(monthly_bars(wx))
    C.print(layout)


def main() -> None:
    ap = argparse.ArgumentParser(description="终端数据仪表盘（rich）")
    ap.add_argument("--watch", type=int, default=0, help="N 秒刷新一次（0=渲染一次）")
    args = ap.parse_args()
    if args.watch <= 0:
        render()
        return
    import time

    while True:
        C.clear()
        render()
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
