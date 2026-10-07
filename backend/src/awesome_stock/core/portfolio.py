"""Pure base-currency portfolio aggregation."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from .ledger import FactValidationError, ZERO, as_decimal


@dataclass(frozen=True)
class PositionValue:
    """Valuation inputs for one account position in its original currency."""

    account: str
    currency: str
    market_value: Decimal | str | int | float
    open_cost: Decimal | str | int | float
    realized: Decimal | str | int | float = ZERO

    def __post_init__(self) -> None:
        account = self.account.strip() if isinstance(self.account, str) else ""
        currency = _currency(self.currency, "currency")
        if not account:
            raise FactValidationError("account is required")
        market_value = as_decimal(self.market_value, "market_value")
        open_cost = as_decimal(self.open_cost, "open_cost")
        realized = as_decimal(self.realized, "realized")
        if market_value < ZERO or open_cost < ZERO:
            raise FactValidationError("market_value and open_cost cannot be negative")
        object.__setattr__(self, "account", account)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "market_value", market_value)
        object.__setattr__(self, "open_cost", open_cost)
        object.__setattr__(self, "realized", realized)


@dataclass(frozen=True)
class PortfolioFacts:
    """Complete base-currency totals, or explicit unknown values."""

    base_currency: str
    holdings_value_base: Decimal | None
    open_cost_base: Decimal | None
    unrealized_base: Decimal | None
    realized_base: Decimal | None
    total_pnl_base: Decimal | None
    cash_base: Decimal | None
    net_assets_base: Decimal | None
    invested_ratio: Decimal | None
    cash_ratio: Decimal | None
    position_weights_of_holdings: tuple[Decimal | None, ...]
    valuation_complete: bool


def _currency(value: str, field: str) -> str:
    normalized = value.strip().upper() if isinstance(value, str) else ""
    if len(normalized) != 3 or not normalized.isascii() or not normalized.isalpha():
        raise FactValidationError(f"{field} must be a three-letter code")
    return normalized


def convert_to_base(
    amount: Decimal | str | int | float,
    *,
    currency: str,
    base_currency: str,
    units_per_base: Mapping[str, Decimal | str | int | float],
) -> Decimal | None:
    """Convert using `currency units per one base-currency unit`.

    A missing rate returns ``None``. It never substitutes a live rate, 1.0, or
    zero. The base currency always converts at exactly one.
    """

    value = as_decimal(amount, "amount")
    source = _currency(currency, "currency")
    base = _currency(base_currency, "base_currency")
    if source == base:
        return value
    raw_rate = units_per_base.get(source)
    if raw_rate is None:
        return None
    rate = as_decimal(raw_rate, f"units_per_base[{source}]")
    if rate <= ZERO:
        raise FactValidationError("exchange rate must be greater than zero")
    return value / rate


def aggregate_portfolio(
    positions: Sequence[PositionValue],
    *,
    base_currency: str,
    units_per_base: Mapping[str, Decimal | str | int | float],
    cash_base: Decimal | str | int | float | None,
) -> PortfolioFacts:
    """Aggregate positions only when every required conversion is known."""

    base = _currency(base_currency, "base_currency")
    normalized_positions = tuple(
        item if isinstance(item, PositionValue) else PositionValue(**item) for item in positions
    )
    converted: list[tuple[Decimal, Decimal, Decimal]] = []
    for position in normalized_positions:
        market_value = convert_to_base(
            position.market_value,
            currency=position.currency,
            base_currency=base,
            units_per_base=units_per_base,
        )
        open_cost = convert_to_base(
            position.open_cost,
            currency=position.currency,
            base_currency=base,
            units_per_base=units_per_base,
        )
        realized = convert_to_base(
            position.realized,
            currency=position.currency,
            base_currency=base,
            units_per_base=units_per_base,
        )
        if market_value is None or open_cost is None or realized is None:
            return PortfolioFacts(
                base_currency=base,
                holdings_value_base=None,
                open_cost_base=None,
                unrealized_base=None,
                realized_base=None,
                total_pnl_base=None,
                cash_base=None if cash_base is None else as_decimal(cash_base, "cash_base"),
                net_assets_base=None,
                invested_ratio=None,
                cash_ratio=None,
                position_weights_of_holdings=tuple(None for _ in normalized_positions),
                valuation_complete=False,
            )
        converted.append((market_value, open_cost, realized))

    holdings = sum((item[0] for item in converted), ZERO)
    open_cost = sum((item[1] for item in converted), ZERO)
    unrealized = holdings - open_cost
    realized = sum((item[2] for item in converted), ZERO)
    total_pnl = unrealized + realized
    weights = tuple(None if holdings == ZERO else item[0] / holdings for item in converted)

    normalized_cash = None if cash_base is None else as_decimal(cash_base, "cash_base")
    if normalized_cash is None:
        net_assets = None
        invested_ratio = None
        cash_ratio = None
    else:
        net_assets = holdings + normalized_cash
        if net_assets == ZERO:
            invested_ratio = None
            cash_ratio = None
        else:
            invested_ratio = holdings / net_assets
            cash_ratio = normalized_cash / net_assets

    return PortfolioFacts(
        base_currency=base,
        holdings_value_base=holdings,
        open_cost_base=open_cost,
        unrealized_base=unrealized,
        realized_base=realized,
        total_pnl_base=total_pnl,
        cash_base=normalized_cash,
        net_assets_base=net_assets,
        invested_ratio=invested_ratio,
        cash_ratio=cash_ratio,
        position_weights_of_holdings=weights,
        valuation_complete=True,
    )
