"""适配器模式 + 模板方法模式：支付渠道统一与 ETL 流程骨架。

适配器：第三方支付渠道接口各异（方法名/参数/返回结构），适配器把它们
统一成内部规范接口——业务代码只依赖内部规范。
模板方法：ETL 的骨架（抽取->转换->加载）固定，每种数据源只实现三个钩子。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


# ---------- 适配器 ----------
@dataclass
class PaymentResult:
    ok: bool
    channel: str
    trade_no: str
    raw: dict


class PaymentGateway(ABC):
    """内部统一规范：业务代码只认这个接口。"""

    channel: str = ""

    @abstractmethod
    def pay(self, order_id: str, amount_cents: int) -> PaymentResult: ...


class AlipaySDK:
    """模拟第三方：方法名/金额单位/返回结构都和内部规范不一样。"""

    def create_pay(self, out_biz_no: str, money_yuan: float) -> dict:
        return {"success": "Y", "tradeNo": f"ALI-{out_biz_no}", "money": money_yuan}


class WechatSDK:
    def unified_order(self, body: str, total_fee: int) -> dict:
        return {"return_code": "SUCCESS",
                "prepay_id": f"WX-{body}", "fee": total_fee}


class AlipayAdapter(PaymentGateway):
    channel = "alipay"

    def __init__(self, sdk: AlipaySDK | None = None):
        self.sdk = sdk or AlipaySDK()

    def pay(self, order_id: str, amount_cents: int) -> PaymentResult:
        raw = self.sdk.create_pay(order_id, amount_cents / 100)
        return PaymentResult(raw["success"] == "Y", self.channel,
                             raw["tradeNo"], raw)


class WechatAdapter(PaymentGateway):
    channel = "wechat"

    def __init__(self, sdk: WechatSDK | None = None):
        self.sdk = sdk or WechatSDK()

    def pay(self, order_id: str, amount_cents: int) -> PaymentResult:
        raw = self.sdk.unified_order(order_id, amount_cents)
        ok = raw["return_code"] == "SUCCESS"
        return PaymentResult(ok, self.channel, raw.get("prepay_id", ""), raw)


def pay_with(gateway: PaymentGateway, order_id: str, amount_cents: int) -> PaymentResult:
    return gateway.pay(order_id, amount_cents)


# ---------- 模板方法 ----------
class EtlJob(ABC):
    """ETL 骨架：run() 固定流程，子类只填 extract/transform/load 三个钩子。"""

    name = "etl"

    def run(self) -> dict:
        raw = self.extract()
        rows = [self.transform(r) for r in raw]
        self.load(rows)
        return {"job": self.name, "rows": len(rows)}

    @abstractmethod
    def extract(self) -> list[dict]: ...

    @abstractmethod
    def transform(self, row: dict) -> dict: ...

    @abstractmethod
    def load(self, rows: list[dict]) -> None: ...


class CsvToWarehouse(EtlJob):
    """具体实现：CSV 行 -> 规整字典 -> 目标表（演示用内存表）。"""

    name = "csv_to_warehouse"

    def __init__(self, raw_rows: list[dict]):
        self.warehouse: list[dict] = []
        self._raw = raw_rows

    def extract(self) -> list[dict]:
        return self._raw

    def transform(self, row: dict) -> dict:
        return {"sku": row["sku"].strip().upper(),
                "qty": int(row["qty"])}

    def load(self, rows: list[dict]) -> None:
        self.warehouse.extend(rows)
