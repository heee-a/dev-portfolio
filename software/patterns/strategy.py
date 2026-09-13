"""策略模式：促销定价引擎。

场景：大促期间定价规则频繁变化（直减/折扣/满减/会员价），如果用 if-else
分支，每加一种促销就要改核心函数；策略模式把「算法族」抽成可替换单元。

何时不用：策略数量少且稳定（比如只有两种），枚举分支更直观——不要为了模式而模式。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class PromoStrategy(Protocol):
    """Protocol（结构化子类型）比继承 ABC 更 Pythonic：只要实现discount即可。"""

    def discount(self, original: float) -> float:
        ...


@dataclass(frozen=True)
class FlatOff:
    """直减：立减 amount 元，最多减到 0。"""

    amount: float

    def discount(self, original: float) -> float:
        return max(0.0, original - self.amount)


@dataclass(frozen=True)
class PercentageOff:
    """折扣：rate 为折扣率（0.85 = 85 折）。"""

    rate: float

    def discount(self, original: float) -> float:
        return round(original * self.rate, 2)


@dataclass(frozen=True)
class FullReduction:
    """满减：每满 threshold 减 off（可叠加），如 每满200减30。"""

    threshold: float
    off: float

    def discount(self, original: float) -> float:
        if original < self.threshold:
            return original
        stacks = int(original // self.threshold)
        return max(0.0, original - stacks * self.off)


def checkout_price(original: float, strategy: PromoStrategy) -> float:
    """结算价只依赖策略接口——新增促销方式零修改。"""
    return strategy.discount(original)
