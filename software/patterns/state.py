"""状态模式：订单状态机。

场景：订单在 待支付 -> 已支付 -> 已发货 -> 已完成 之间流转，每个状态
允许的操作不同（待支付才能支付、已支付才能发货）。用「状态对象」取代
满屏 `if status == ...`，非法流转直接抛错——业务规则一目了然。
"""

from __future__ import annotations

from dataclasses import dataclass, field


class IllegalTransition(Exception):
    pass


@dataclass
class OrderFSM:
    """有限状态机：转移表驱动，新增状态只需注册新 State。"""

    order_id: str
    state: str = "待支付"
    events: list[str] = field(default_factory=list)

    # 转移表：当前状态 -> {事件: 下一状态}
    TRANSITIONS: dict = field(default_factory=lambda: {
        "待支付": {"支付": "已支付", "取消": "已取消"},
        "已支付": {"发货": "已发货", "退款": "已退款"},
        "已发货": {"签收": "已完成"},
        "已完成": {},
        "已取消": {},
        "已退款": {},
    })

    def fire(self, event: str) -> str:
        transitions = self.TRANSITIONS[self.state]
        if event not in transitions:
            raise IllegalTransition(
                f"订单 {self.order_id} 在「{self.state}」状态不允许 {event!r}"
                f"（允许: {list(transitions)}）")
        self.state = transitions[event]
        self.events.append(event)
        return self.state
