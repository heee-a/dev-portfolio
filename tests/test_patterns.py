"""patterns 全量测试：每个模式都有「行为 + 设计意图」两层断言。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "software"))

import pytest

from patterns.adapter_template import (AlipayAdapter, CsvToWarehouse,
                                       WechatAdapter, pay_with)
from patterns.chain_of_responsibility import Order, build_chain
from patterns.decorator_singleton import ConfigCenter, flaky_task
from patterns.factory_builder import QueryBuilder, make_exporter, register_format
from patterns.observer import InventorySubject, PurchaseNotifier
from patterns.state import IllegalTransition, OrderFSM
from patterns.strategy import FullReduction, FlatOff, PercentageOff, checkout_price


# ---------------- 策略 ----------------
def test_promo_strategies():
    assert checkout_price(100, FlatOff(30)) == 70.0
    assert checkout_price(100, FlatOff(200)) == 0.0          # 最多减到 0
    assert checkout_price(100, PercentageOff(0.85)) == 85.0
    assert checkout_price(450, FullReduction(200, 30)) == 390  # 450/200=2 档，减 60
    assert checkout_price(150, FullReduction(200, 30)) == 150


# ---------------- 观察者 ----------------
def test_observer_alerts():
    subject = InventorySubject(safety_stock=10)
    notifier = PurchaseNotifier()
    log = []
    subject.subscribe(notifier)
    subject.subscribe(lambda a: log.append(a.message))
    subject.receive("SKU-1", 15)
    fired = subject.ship("SKU-1", 8)                # 15 - 8 = 7 < 10 -> 触发
    assert len(fired) == 1 and fired[0].current == 7
    assert notifier.requested == ["补货单:SKU-1x20"]
    assert log == ["[预警] SKU-1 库存 7 已低于安全线 10"]
    fired = subject.ship("SKU-1", 1)                # 6 仍低于安全线 -> 再次触发
    assert len(fired) == 1 and fired[0].current == 6


# ---------------- 责任链 ----------------
def test_chain_approves_clean_order():
    order = Order("O1", "U1", 500)
    decision = build_chain(10000).handle(order)
    assert decision.approved and len(decision.trail) == 2


def test_chain_rejects_blacklist_first():
    order = Order("O2", "U2", 500, is_blacklisted=True)
    decision = build_chain(10000).handle(order)
    assert not decision.approved and decision.rejected_by == "BlacklistCheck"


def test_chain_rejects_amount():
    order = Order("O3", "U3", 20000)
    decision = build_chain(10000).handle(order)
    assert not decision.approved and "超限" in decision.reason


# ---------------- 状态机 ----------------
def test_order_fsm_happy_path():
    o = OrderFSM("O9")
    for event in ("支付", "发货", "签收"):
        o.fire(event)
    assert o.state == "已完成" and o.events == ["支付", "发货", "签收"]


def test_order_fsm_illegal_transition():
    o = OrderFSM("O10")
    with pytest.raises(IllegalTransition, match="不允许 '发货'"):
        o.fire("发货")                              # 待支付不能直接发货


# ---------------- 工厂 + 建造者 ----------------
def test_factory_exporters():
    rows = [{"name": "a", "qty": 1}, {"name": "b", "qty": 2}]
    assert make_exporter("csv").export(rows).splitlines()[0] == "name,qty"
    assert '"name": "a"' in make_exporter("json").export(rows)
    with pytest.raises(ValueError, match="未知格式"):
        make_exporter("pdf")


def test_factory_open_for_extension():
    @register_format("raw")
    class RawExporter:
        def export(self, rows):
            return repr(rows)
    # 注册即用，工厂函数未做任何修改（开闭原则）
    assert make_exporter("raw").export([{"x": 1}]) == "[{'x': 1}]"


def test_query_builder():
    q = (QueryBuilder("orders").select("id", "amount")
         .where("amount", ">", 100).where("status", "=", "paid")
         .order_desc("amount").limit(5).build())
    sql = q.to_sql()
    assert sql == ("SELECT id, amount FROM orders "
                   "WHERE amount > 100 AND status = 'paid' "
                   "ORDER BY amount DESC LIMIT 5")


# ---------------- 装饰器 + 单例 ----------------
def test_retry_decorator():
    flaky_task.calls = 0
    assert flaky_task(fail_times=2) == "ok"          # 前两次失败，第三次成功
    assert flaky_task.calls == 3
    flaky_task.calls = 0
    with pytest.raises(ConnectionError):
        flaky_task(fail_times=99)                    # 重试耗尽后异常上抛


def test_singleton_identity_and_reset():
    ConfigCenter._reset()
    a = ConfigCenter()
    b = ConfigCenter()
    assert a is b                                    # 同一实例
    a.load({"env": "prod"})
    assert b.get("env") == "prod"
    ConfigCenter._reset()
    with pytest.raises(RuntimeError, match="尚未加载"):
        ConfigCenter().get("env")


# ---------------- 适配器 + 模板方法 ----------------
def test_adapters_unify_third_parties():
    for gateway in (AlipayAdapter(), WechatAdapter()):
        r = pay_with(gateway, "ORDER-1", 9900)
        assert r.ok and r.trade_no and r.channel     # 统一结构，业务无感知


def test_template_method_etl():
    job = CsvToWarehouse([{"sku": " abc ", "qty": "2"}, {"sku": "def", "qty": "3"}])
    result = job.run()
    assert result == {"job": "csv_to_warehouse", "rows": 2}
    assert job.warehouse == [{"sku": "ABC", "qty": 2}, {"sku": "DEF", "qty": 3}]
