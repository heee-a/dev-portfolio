"""责任链模式：订单风控审批。

场景：一笔订单依次经过 规则校验 -> 额度检查 -> 人工复核名单。每个节点
「通过则放行、不通过则拦截」，节点顺序与组合随时可调——链式结构替代
一长串 if。

变体说明：纯责任链（一个节点处理后即终止）与本例的「逐节点放行」是
两种流派，面试时说清自己实现的是哪一种。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Order:
    order_id: str
    user_id: str
    amount: float
    is_blacklisted: bool = False


@dataclass
class Decision:
    approved: bool
    rejected_by: str = ""
    reason: str = ""
    trail: list[str] = field(default_factory=list)


class Handler:
    """节点处理语义：本节点校验 -> 通过则把累积中的 Decision 传给后继。
    trail（审核轨迹）在链上逐节点累积，最终调用方拿到完整审批记录。"""

    def __init__(self, successor: "Handler | None" = None):
        self.successor = successor

    def handle(self, order: Order, decision: Decision | None = None) -> Decision:
        decision = decision or Decision(True, trail=[])
        result = self._check(order)
        decision.trail.extend(result.trail)
        if not result.approved:
            decision.approved = False
            decision.rejected_by = result.rejected_by
            decision.reason = result.reason
            return decision
        if self.successor:
            return self.successor.handle(order, decision)
        return decision

    def _check(self, order: Order) -> Decision:
        raise NotImplementedError


class BlacklistCheck(Handler):
    def _check(self, order: Order) -> Decision:
        if order.is_blacklisted:
            return Decision(False, type(self).__name__, "黑名单用户",
                            trail=["黑名单拦截"])
        return Decision(True, trail=["黑名单通过"])


class AmountLimit(Handler):
    def __init__(self, max_amount: float, successor: "Handler | None" = None):
        super().__init__(successor)
        self.max_amount = max_amount

    def _check(self, order: Order) -> Decision:
        if order.amount > self.max_amount:
            return Decision(False, type(self).__name__,
                            f"金额 {order.amount} 超限 {self.max_amount}",
                            trail=[f"额度校验拦截(>{self.max_amount})"])
        return Decision(True, trail=[f"额度校验通过(<= {self.max_amount})"])


def build_chain(max_amount: float = 10000) -> Handler:
    """组装链：黑名单 -> 额度。链的形状由业务在组合根决定。"""
    return BlacklistCheck(AmountLimit(max_amount))
