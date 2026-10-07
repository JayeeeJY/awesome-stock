"""Ephemeral, all-synthetic data and identity for the local Community demo."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

from awesome_stock.api import CommunityApi, LegacyReadAdapter
from awesome_stock.api.contracts import ApiResponse, problem_from_exception
from awesome_stock.core.ledger import CostMethod, Trade, calculate_position
from awesome_stock.core.portfolio import PositionValue, aggregate_portfolio
from awesome_stock.security.access import WorkspaceGrant
from awesome_stock.security.auth import UserRecord, make_password_credential
from awesome_stock.security.sessions import InMemorySessionRepository, SessionService


WORKSPACE_ID = "community-demo"
ACCOUNT_ID = "synthetic-core"
DEMO_USERNAME = "demo@awesome.local"
DAY_CHANGES = {
    "ALPH": Decimal("2.8"),
    "BETA": Decimal("1.3"),
    "GAMMA": Decimal("-1.9"),
    "DELTA": Decimal("0.7"),
    "EPSLN": Decimal("1.1"),
    "ZETA": Decimal("0.4"),
    "THETA": Decimal("-0.6"),
    "IOTA": Decimal("0.9"),
    "KAPPA": Decimal("1.2"),
    "LAMBDA": Decimal("2.0"),
}
QUOTES = {
    "ALPH": Decimal("150"),
    "BETA": Decimal("90"),
    "GAMMA": Decimal("150"),
    "DELTA": Decimal("200"),
    "EPSLN": Decimal("180"),
    "ZETA": Decimal("110"),
    "THETA": Decimal("90"),
    "IOTA": Decimal("100"),
    "KAPPA": Decimal("100"),
    "LAMBDA": Decimal("100"),
}
NAMES = {
    "ALPH": "Alpha Systems",
    "BETA": "Beta Works",
    "GAMMA": "Gamma Labs",
    "DELTA": "Delta Industries",
    "EPSLN": "Epsilon Health",
    "ZETA": "Zeta Consumer",
    "THETA": "Theta Energy",
    "IOTA": "Iota Finance",
    "KAPPA": "Kappa Materials",
    "LAMBDA": "Lambda Compute",
}
POSITIONS = (
    ("ALPH", "306", "110.62"),
    ("BETA", "420", "75.82"),
    ("GAMMA", "198", "142.32"),
    ("DELTA", "126", "178.41"),
    ("EPSLN", "120", "154.77"),
    ("ZETA", "180", "100.18"),
    ("THETA", "180", "88.15"),
    ("IOTA", "138", "90.09"),
    ("KAPPA", "111", "87.57"),
    ("LAMBDA", "60", "74.68"),
)
CASH = Decimal("42900")


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(Decimal("0.01")))


def _percent(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(Decimal("0.01")))


def synthetic_rows() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "workspace_id": WORKSPACE_ID,
            "account_id": ACCOUNT_ID,
            "symbol": symbol,
            "currency": "USD",
            "source": "synthetic-demo",
            "external_id": f"opening-{index:02d}",
            "executed_at": f"2026-01-{index + 1:02d}T14:30:00Z",
            "side": "buy",
            "quantity": quantity,
            "price": cost,
            "fee": "0",
            "sequence": index,
        }
        for index, (symbol, quantity, cost) in enumerate(POSITIONS)
    )


@dataclass(frozen=True)
class DemoIdentity:
    username: str
    password: str


class DemoRuntime:
    """One-process demo state with random credentials and no persistence."""

    def __init__(self, *, allowed_origins: frozenset[str]) -> None:
        password = secrets.token_urlsafe(18)
        self.identity = DemoIdentity(DEMO_USERNAME, password)
        self._user = UserRecord(
            "synthetic-user",
            DEMO_USERNAME,
            make_password_credential(password, salt=secrets.token_bytes(16)),
        )
        self.grant = WorkspaceGrant(
            self._user.user_id,
            WORKSPACE_ID,
            "owner",
            frozenset({ACCOUNT_ID}),
        )
        self._rows = synthetic_rows()
        self.sessions = SessionService(
            InMemorySessionRepository(),
            clock=lambda: datetime.now(timezone.utc),
            token_factory=lambda: secrets.token_urlsafe(32),
            is_user_active=lambda user_id: user_id == self._user.user_id,
            access_lifetime=timedelta(minutes=15),
            refresh_lifetime=timedelta(hours=8),
        )
        self.api = CommunityApi(
            sessions=self.sessions,
            user_lookup=lambda username: self._user if username == self._user.username else None,
            legacy=LegacyReadAdapter(lambda _workspace, _accounts: self._rows),
            clock=lambda: datetime.now(timezone.utc),
            csrf_factory=lambda: secrets.token_urlsafe(32),
            allowed_origins=allowed_origins,
        )

    def bootstrap(self) -> dict[str, object]:
        return {
            "mode": "synthetic_demo",
            "username": self.identity.username,
            "password": self.identity.password,
            "credential_lifetime": "until_process_restart",
            "persistence": False,
        }

    def session_status(self, access_token: str, *, request_id: object = None) -> ApiResponse:
        try:
            user_id = self.sessions.validate_access(access_token)
            return ApiResponse(200, data={"authenticated": True, "user_id": user_id})
        except Exception as error:
            return ApiResponse.failure(problem_from_exception(error, request_id=request_id))

    def portfolio(self, access_token: str, *, request_id: object = None) -> ApiResponse:
        source = self.api.list_legacy_trades(
            access_token=access_token,
            grant=self.grant,
            workspace_id=WORKSPACE_ID,
            request_id=request_id,
        )
        if source.problem is not None:
            return source
        facts = []
        holdings = []
        total_today = Decimal("0")
        for record in source.data["records"]:
            symbol = record["symbol"]
            quote = QUOTES[symbol]
            position = calculate_position(
                (Trade(record["side"], record["quantity"], record["price"], record["fee"]),),
                quote=quote,
                method=CostMethod.AVERAGE,
                currency=record["currency"],
            )
            facts.append(
                PositionValue(
                    account=record["account_id"],
                    currency=position.currency,
                    market_value=position.market_value,
                    open_cost=position.open_cost,
                    realized=position.realized,
                )
            )
            today_percent = DAY_CHANGES[symbol]
            today_amount = position.market_value * today_percent / Decimal("100")
            total_today += today_amount
            holdings.append(
                {
                    "symbol": symbol,
                    "name": NAMES[symbol],
                    "currency": position.currency,
                    "price": _money(quote),
                    "quantity": _money(position.shares),
                    "market_value": _money(position.market_value),
                    "open_cost": _money(position.open_cost),
                    "total_pnl": _money(position.total_pnl),
                    "total_pnl_percent": _percent(position.total_pnl_percent),
                    "today_pnl": _money(today_amount),
                    "today_percent": _percent(today_percent),
                    "account": "合成主账户",
                }
            )
        aggregate = aggregate_portfolio(
            tuple(facts),
            base_currency="USD",
            units_per_base={},
            cash_base=CASH,
        )
        for holding, weight in zip(holdings, aggregate.position_weights_of_holdings):
            holding["weight"] = _percent(None if weight is None else weight * Decimal("100"))
        holdings.sort(key=lambda item: Decimal(item["market_value"]), reverse=True)
        today_rate = None
        if aggregate.net_assets_base:
            today_rate = total_today / aggregate.net_assets_base * Decimal("100")
        summary = {
            "base_currency": aggregate.base_currency,
            "net_assets": _money(aggregate.net_assets_base),
            "today_pnl": _money(total_today),
            "today_percent": _percent(today_rate),
            "total_pnl": _money(aggregate.total_pnl_base),
            "total_pnl_percent": _percent(
                None
                if aggregate.open_cost_base in {None, Decimal("0")}
                else aggregate.total_pnl_base / aggregate.open_cost_base * Decimal("100")
            ),
            "invested_ratio": _percent(
                None if aggregate.invested_ratio is None else aggregate.invested_ratio * Decimal("100")
            ),
            "cash": _money(aggregate.cash_base),
            "cash_ratio": _percent(
                None if aggregate.cash_ratio is None else aggregate.cash_ratio * Decimal("100")
            ),
            "risk_status": "需关注",
            "position_count": len(holdings),
            "valuation_complete": aggregate.valuation_complete,
        }
        return ApiResponse(
            200,
            data={
                "data_status": "synthetic_complete",
                "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "summary": summary,
                "holdings": tuple(holdings),
                "changes": (
                    {"level": "high", "text": "ALPH 仓位仍是组合首要影响因子", "time": "2 小时前"},
                    {"level": "medium", "text": "GAMMA 当日回撤超过合成观察阈值", "time": "4 小时前"},
                    {"level": "low", "text": "现金比例保持在计划区间", "time": "6 小时前"},
                ),
                "actions": (
                    {"priority": "P1", "text": "复核 ALPH 集中度", "asset": "ALPH", "due": "今日"},
                    {"priority": "P1", "text": "检查 GAMMA 回撤条件", "asset": "GAMMA", "due": "今日"},
                    {"priority": "P2", "text": "更新季度研究假设", "asset": "组合", "due": "本周"},
                ),
            },
        )
