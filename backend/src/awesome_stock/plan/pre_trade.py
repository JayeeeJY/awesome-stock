"""Pre-trade impact checks that never create or execute an order."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .allocation import HUNDRED, PlanValidationError, decimal_value


@dataclass(frozen=True)
class TradeCheck:
    code: str
    status: str
    label: str
    detail: str


@dataclass(frozen=True)
class TradeImpact:
    symbol: str
    side: str
    quantity: Decimal
    current_quantity: Decimal
    price: Decimal
    fee: Decimal
    gross_value: Decimal
    post_cash: Decimal
    post_quantity: Decimal
    post_position_value: Decimal
    post_weight_percent: Optional[Decimal]
    estimated_net_assets: Optional[Decimal]
    currency: str
    base_currency: str
    fx_rate_to_base: Optional[Decimal]
    status: str
    checks: tuple[TradeCheck, ...]


def check_trade(
    *,
    symbol: str,
    side: str,
    quantity: object,
    price: object,
    fee: object,
    current_quantity: object,
    current_position_value: object,
    available_cash: object,
    net_assets: object,
    max_position_percent: object = Decimal("25"),
    currency: str = "USD",
    base_currency: str = "USD",
    fx_rate_to_base: object | None = None,
) -> TradeImpact:
    if not isinstance(symbol, str) or not symbol.strip():
        raise PlanValidationError("symbol is required")
    normalized_side = side.strip().lower() if isinstance(side, str) else ""
    if normalized_side not in {"buy", "sell"}:
        raise PlanValidationError("side must be buy or sell")
    qty = decimal_value(quantity, "quantity", minimum=Decimal("0.000001"))
    trade_price = decimal_value(price, "price", minimum=Decimal("0.01"))
    trade_fee = decimal_value(fee, "fee")
    current_qty = decimal_value(current_quantity, "current_quantity")
    current_value = decimal_value(current_position_value, "current_position_value")
    cash = decimal_value(available_cash, "available_cash")
    assets = decimal_value(net_assets, "net_assets", minimum=Decimal("0.01"))
    limit = decimal_value(max_position_percent, "max_position_percent", minimum=Decimal("0.01"))
    if limit > HUNDRED:
        raise PlanValidationError("max_position_percent cannot exceed 100")

    native_currency = str(currency or "").strip().upper()
    normalized_base = str(base_currency or "").strip().upper()
    if len(native_currency) != 3 or len(normalized_base) != 3:
        raise PlanValidationError("currency and base_currency must be three-letter codes")
    if native_currency == normalized_base:
        fx_rate = Decimal("1")
    elif fx_rate_to_base is None:
        fx_rate = None
    else:
        fx_rate = decimal_value(
            fx_rate_to_base,
            "fx_rate_to_base",
            minimum=Decimal("0.000000000001"),
        )

    gross = qty * trade_price
    quantity_blocked = normalized_side == "sell" and qty > current_qty
    if normalized_side == "buy":
        post_cash = cash - gross - trade_fee
        post_quantity = current_qty + qty
        post_position = current_value + gross
    else:
        post_cash = cash + gross - trade_fee
        post_quantity = max(Decimal("0"), current_qty - qty)
        removed = Decimal("0") if current_qty == 0 else current_value * min(qty, current_qty) / current_qty
        post_position = max(Decimal("0"), current_value - removed)
    post_assets = None if fx_rate is None else assets - trade_fee * fx_rate
    post_position_base = None if fx_rate is None else post_position * fx_rate
    post_weight = (
        None
        if post_assets is None or post_position_base is None
        else Decimal("0") if post_assets <= 0
        else post_position_base / post_assets * HUNDRED
    )

    checks = []
    if fx_rate is None:
        checks.append(TradeCheck("fx", "block", "汇率覆盖", "缺少明确汇率，不能形成基准币组合结论"))
    else:
        checks.append(TradeCheck("fx", "pass", "汇率覆盖", "交易币种与基准币换算明确"))
    if normalized_side == "buy" and post_cash < 0:
        checks.append(TradeCheck("cash", "block", "现金覆盖", "预计现金不足，不能形成可执行草案"))
    else:
        checks.append(TradeCheck("cash", "pass", "现金覆盖", "预计现金保持非负"))
    if quantity_blocked:
        checks.append(TradeCheck("quantity", "block", "持仓数量", "卖出数量超过当前持仓"))
    else:
        checks.append(TradeCheck("quantity", "pass", "持仓数量", "数量在当前合成持仓范围内"))
    if post_weight is None:
        checks.append(TradeCheck("concentration", "block", "仓位上限", "缺少汇率，无法计算交易后仓位"))
    elif normalized_side == "buy" and post_weight > limit:
        checks.append(TradeCheck("concentration", "block", "仓位上限", "预计仓位超过当前规则上限"))
    elif post_weight > limit:
        checks.append(TradeCheck("concentration", "warn", "仓位上限", "交易后仓位仍高于规则线，但方向正在降低暴露"))
    else:
        checks.append(TradeCheck("concentration", "pass", "仓位上限", "预计仓位未超过规则上限"))
    fee_ratio = trade_fee / gross * HUNDRED
    checks.append(
        TradeCheck(
            "fee",
            "warn" if fee_ratio > Decimal("1") else "pass",
            "费用影响",
            "费用超过成交金额 1%" if fee_ratio > Decimal("1") else "费用占比未超过 1%",
        )
    )
    status = "blocked" if any(item.status == "block" for item in checks) else "warning" if any(item.status == "warn" for item in checks) else "passed"
    return TradeImpact(
        symbol.strip().upper(),
        normalized_side,
        qty,
        current_qty,
        trade_price,
        trade_fee,
        gross,
        post_cash,
        post_quantity,
        post_position,
        post_weight,
        post_assets,
        native_currency,
        normalized_base,
        fx_rate,
        status,
        tuple(checks),
    )
