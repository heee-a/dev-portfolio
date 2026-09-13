"""观察者模式：库存变化预警。

场景：库存低于安全线时，需要同时通知「采购系统」和「运营钉钉群」，
以后可能再加「短信」。主题（被观察者）不关心谁订阅了它——解耦的核心。

何时不用：事件链有明确先后依赖时，用管道/责任链而不是广播。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class InventoryAlert:
    sku: str
    current: int
    safety_stock: int

    @property
    def message(self) -> str:
        return f"[预警] {self.sku} 库存 {self.current} 已低于安全线 {self.safety_stock}"


class InventorySubject:
    """主题：库存台账。订阅者收到 InventoryAlert 事件。"""

    def __init__(self, safety_stock: int = 10):
        self.safety_stock = safety_stock
        self._subscribers: list[Callable[[InventoryAlert], None]] = []
        self._stock: dict[str, int] = {}

    def subscribe(self, fn: Callable[[InventoryAlert], None]) -> None:
        self._subscribers.append(fn)

    def receive(self, sku: str, qty: int) -> None:
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def ship(self, sku: str, qty: int) -> list[InventoryAlert]:
        """出货并触发预警。返回触发的预警列表（便于测试）。"""
        self._stock[sku] = self._stock.get(sku, 0) - qty
        fired = []
        if self._stock[sku] < self.safety_stock:
            alert = InventoryAlert(sku, self._stock[sku], self.safety_stock)
            for fn in self._subscribers:
                fn(alert)                 # 生产上这里应是异步/消息队列
            fired.append(alert)
        return fired


@dataclass
class PurchaseNotifier:
    """采购系统订阅者：记录触发的补货请求。"""

    requested: list[str] = field(default_factory=list)

    def __call__(self, alert: InventoryAlert) -> None:
        self.requested.append(f"补货单:{alert.sku}x{alert.safety_stock * 2}")
