"""Pure position and profit/loss calculations.

The module intentionally has no environment, network, database, filesystem, or
clock dependency. Inputs and outputs use ``Decimal`` so display formatting can
never alter ledger facts.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable


ZERO = Decimal("0")
HUNDRED = Decimal("100")


class FactValidationError(ValueError):
    """Raised when an input cannot produce trustworthy ledger facts."""


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class CostMethod(str, Enum):
    AVERAGE = "avg"
    FIFO = "fifo"


def as_decimal(value: object, field: str) -> Decimal:
    """Return a finite Decimal or raise a field-specific validation error."""

    if isinstance(value, bool):
        raise FactValidationError(f"{field} must be a finite number")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FactValidationError(f"{field} must be a finite number") from exc
    if not result.is_finite():
        raise FactValidationError(f"{field} must be a finite number")
    return result


@dataclass(frozen=True)
class Trade:
    """One ordered, long-only transaction in its original currency."""

    side: TradeSide | str
    quantity: Decimal | str | int | float
    price: Decimal | str | int | float
    fee: Decimal | str | int | float = ZERO

    def __post_init__(self) -> None:
        try:
            side = self.side if isinstance(self.side, TradeSide) else TradeSide(self.side)
        except ValueError as exc:
            raise FactValidationError("side must be buy or sell") from exc
        quantity = as_decimal(self.quantity, "quantity")
        price = as_decimal(self.price, "price")
        fee = as_decimal(self.fee, "fee")
        if quantity <= ZERO:
            raise FactValidationError("quantity must be greater than zero")
        if price < ZERO:
            raise FactValidationError("price cannot be negative")
        if fee < ZERO:
            raise FactValidationError("fee cannot be negative")
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "fee", fee)


@dataclass(frozen=True)
class PositionFacts:
    """Position facts for one account, symbol, and original currency."""

    currency: str
    shares: Decimal
    open_cost: Decimal
    released_cost: Decimal
    realized: Decimal
    market_value: Decimal | None
    unrealized: Decimal | None
    total_pnl: Decimal | None
    total_pnl_percent: Decimal | None
    cash_delta: Decimal

    @property
    def ratio_available(self) -> bool:
        return self.total_pnl_percent is not None


@dataclass(frozen=True)
class OpeningLot:
    """One immutable FIFO lot captured at a baseline cutoff."""

    quantity: Decimal | str | int | float
    cost: Decimal | str | int | float

    def __post_init__(self) -> None:
        quantity = as_decimal(self.quantity, "lot quantity")
        cost = as_decimal(self.cost, "lot cost")
        if quantity <= ZERO:
            raise FactValidationError("lot quantity must be greater than zero")
        if cost < ZERO:
            raise FactValidationError("lot cost cannot be negative")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "cost", cost)


@dataclass(frozen=True)
class OpeningPosition:
    """Position state that existed before a deterministic rebuild cutoff."""

    shares: Decimal | str | int | float
    open_cost: Decimal | str | int | float
    realized: Decimal | str | int | float = ZERO
    fifo_lots: tuple[OpeningLot, ...] = ()

    def __post_init__(self) -> None:
        shares = as_decimal(self.shares, "opening shares")
        open_cost = as_decimal(self.open_cost, "opening open_cost")
        realized = as_decimal(self.realized, "opening realized")
        lots = tuple(
            item if isinstance(item, OpeningLot) else OpeningLot(**item)
            for item in self.fifo_lots
        )
        if shares < ZERO or open_cost < ZERO:
            raise FactValidationError("opening shares and open_cost cannot be negative")
        if shares == ZERO and open_cost != ZERO:
            raise FactValidationError("closed opening position cannot retain open_cost")
        if lots:
            if sum((item.quantity for item in lots), ZERO) != shares:
                raise FactValidationError("opening FIFO lot quantity must equal opening shares")
            if sum((item.cost for item in lots), ZERO) != open_cost:
                raise FactValidationError("opening FIFO lot cost must equal opening open_cost")
        object.__setattr__(self, "shares", shares)
        object.__setattr__(self, "open_cost", open_cost)
        object.__setattr__(self, "realized", realized)
        object.__setattr__(self, "fifo_lots", lots)


@dataclass(frozen=True)
class ValuationFacts:
    """Valuation facts for a known open quantity and cost basis."""

    market_value: Decimal | None
    unrealized: Decimal | None
    total_pnl: Decimal | None
    total_pnl_percent: Decimal | None


def _validated_currency(currency: str) -> str:
    normalized = currency.strip().upper() if isinstance(currency, str) else ""
    if len(normalized) != 3 or not normalized.isascii() or not normalized.isalpha():
        raise FactValidationError("currency must be a three-letter code")
    return normalized


def value_position(
    *,
    shares: Decimal | str | int | float,
    open_cost: Decimal | str | int | float,
    realized: Decimal | str | int | float = ZERO,
    quote: Decimal | str | int | float | None,
) -> ValuationFacts:
    """Value an open position without inventing a missing quote."""

    normalized_shares = as_decimal(shares, "shares")
    normalized_cost = as_decimal(open_cost, "open_cost")
    normalized_realized = as_decimal(realized, "realized")
    normalized_quote = None if quote is None else as_decimal(quote, "quote")
    if normalized_shares < ZERO or normalized_cost < ZERO:
        raise FactValidationError("shares and open_cost cannot be negative")
    if normalized_quote is not None and normalized_quote < ZERO:
        raise FactValidationError("quote cannot be negative")
    if normalized_shares == ZERO:
        market_value = ZERO
        unrealized = ZERO
        total_pnl = normalized_realized
    elif normalized_quote is None:
        return ValuationFacts(None, None, None, None)
    else:
        market_value = normalized_shares * normalized_quote
        unrealized = market_value - normalized_cost
        total_pnl = normalized_realized + unrealized
    percentage = None if normalized_cost == ZERO else total_pnl / normalized_cost * HUNDRED
    return ValuationFacts(market_value, unrealized, total_pnl, percentage)


def calculate_position(
    trades: Iterable[Trade],
    *,
    quote: Decimal | str | int | float | None,
    method: CostMethod | str,
    currency: str,
    opening: OpeningPosition | None = None,
) -> PositionFacts:
    """Calculate a long-only position using average cost or FIFO.

    Transactions are processed in the supplied ledger order. Selling more than
    the open quantity is rejected instead of silently creating a short position.
    """

    try:
        cost_method = method if isinstance(method, CostMethod) else CostMethod(method)
    except ValueError as exc:
        raise FactValidationError("method must be avg or fifo") from exc
    normalized_currency = _validated_currency(currency)
    current_quote = None if quote is None else as_decimal(quote, "quote")
    if current_quote is not None and current_quote < ZERO:
        raise FactValidationError("quote cannot be negative")

    initial = opening or OpeningPosition(shares=ZERO, open_cost=ZERO)
    shares = initial.shares
    open_cost = initial.open_cost
    released_cost = ZERO
    realized = initial.realized
    cash_delta = ZERO
    if cost_method is CostMethod.FIFO and shares > ZERO and not initial.fifo_lots:
        raise FactValidationError("FIFO opening position requires opening lots")
    fifo_lots: list[list[Decimal]] = [
        [item.quantity, item.cost] for item in initial.fifo_lots
    ]

    for raw_trade in trades:
        trade = raw_trade if isinstance(raw_trade, Trade) else Trade(**raw_trade)
        gross = trade.quantity * trade.price
        if trade.side is TradeSide.BUY:
            total_cost = gross + trade.fee
            shares += trade.quantity
            open_cost += total_cost
            cash_delta -= total_cost
            if cost_method is CostMethod.FIFO:
                fifo_lots.append([trade.quantity, total_cost])
            continue

        if trade.quantity > shares:
            raise FactValidationError("sell quantity exceeds open quantity")
        net_proceeds = gross - trade.fee
        if cost_method is CostMethod.AVERAGE:
            released = open_cost * trade.quantity / shares
        else:
            remaining = trade.quantity
            released = ZERO
            while remaining > ZERO:
                lot_quantity, lot_cost = fifo_lots[0]
                taken = min(remaining, lot_quantity)
                cost_taken = lot_cost * taken / lot_quantity
                released += cost_taken
                lot_quantity -= taken
                lot_cost -= cost_taken
                remaining -= taken
                if lot_quantity == ZERO:
                    fifo_lots.pop(0)
                else:
                    fifo_lots[0] = [lot_quantity, lot_cost]
        shares -= trade.quantity
        open_cost -= released
        released_cost += released
        realized += net_proceeds - released
        cash_delta += net_proceeds

    if shares == ZERO:
        open_cost = ZERO
    valuation = value_position(
        shares=shares,
        open_cost=open_cost,
        realized=realized,
        quote=current_quote,
    )
    return PositionFacts(
        currency=normalized_currency,
        shares=shares,
        open_cost=open_cost,
        released_cost=released_cost,
        realized=realized,
        market_value=valuation.market_value,
        unrealized=valuation.unrealized,
        total_pnl=valuation.total_pnl,
        total_pnl_percent=valuation.total_pnl_percent,
        cash_delta=cash_delta,
    )
