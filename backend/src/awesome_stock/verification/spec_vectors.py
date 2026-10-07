"""Approved synthetic arithmetic expectations for independent shadow checks.

These examples contain no user holdings, provider responses, credentials, or
legacy application output. They describe the public calculation contract that
the independent implementation must satisfy before any real-data comparison is
even considered.
"""

LEDGER_VECTORS = (
    {
        "id": "LED-AVG",
        "method": "avg",
        "currency": "USD",
        "trades": (
            {"side": "buy", "quantity": "10", "price": "100", "fee": "2"},
            {"side": "buy", "quantity": "10", "price": "120", "fee": "2"},
            {"side": "sell", "quantity": "5", "price": "130", "fee": "1"},
        ),
        "quote": "140",
        "expected": {
            "shares": "15", "open_cost": "1653", "released_cost": "551",
            "realized": "98", "market_value": "2100", "unrealized": "447",
            "total_pnl": "545", "cash_delta": "-1555", "ratio_available": True,
        },
    },
    {
        "id": "LED-FIFO",
        "method": "fifo",
        "currency": "USD",
        "trades": (
            {"side": "buy", "quantity": "10", "price": "100", "fee": "2"},
            {"side": "buy", "quantity": "10", "price": "120", "fee": "2"},
            {"side": "sell", "quantity": "5", "price": "130", "fee": "1"},
        ),
        "quote": "140",
        "expected": {
            "shares": "15", "open_cost": "1703", "released_cost": "501",
            "realized": "148", "market_value": "2100", "unrealized": "397",
            "total_pnl": "545", "cash_delta": "-1555", "ratio_available": True,
        },
    },
    {
        "id": "LED-CLOSED",
        "method": "avg",
        "currency": "USD",
        "trades": (
            {"side": "buy", "quantity": "10", "price": "100", "fee": "2"},
            {"side": "sell", "quantity": "10", "price": "110", "fee": "2"},
        ),
        "quote": "110",
        "expected": {
            "shares": "0", "open_cost": "0", "released_cost": "1002",
            "realized": "96", "market_value": "0", "unrealized": "0",
            "total_pnl": "96", "cash_delta": "96", "ratio_available": False,
        },
    },
    {
        "id": "LED-FRACTION",
        "method": "avg",
        "currency": "USD",
        "trades": (
            {"side": "buy", "quantity": "0.8", "price": "36.5", "fee": "0.2"},
            {"side": "sell", "quantity": "0.3", "price": "40", "fee": "0.1"},
        ),
        "quote": "42",
        "expected": {
            "shares": "0.5", "open_cost": "18.375", "released_cost": "11.025",
            "realized": "0.875", "market_value": "21", "unrealized": "2.625",
            "total_pnl": "3.5", "cash_delta": "-17.5", "ratio_available": True,
        },
    },
    {
        "id": "LED-LOSS",
        "method": "avg",
        "currency": "USD",
        "trades": (
            {"side": "buy", "quantity": "10", "price": "100", "fee": "2"},
        ),
        "quote": "80",
        "expected": {
            "shares": "10", "open_cost": "1002", "released_cost": "0",
            "realized": "0", "market_value": "800", "unrealized": "-202",
            "total_pnl": "-202", "cash_delta": "-1002", "ratio_available": True,
        },
    },
)

MIXED_CURRENCY_VECTOR = {
    "id": "LED-FX-CASH",
    "base_currency": "USD",
    "hkd_per_usd": "7.8",
    "positions": (
        {"account": "DEMO-USD", "currency": "USD", "market_value": "1000", "open_cost": "900", "realized": "50"},
        {"account": "DEMO-HKD", "currency": "HKD", "market_value": "7800", "open_cost": "7020", "realized": "390"},
    ),
    "cash_usd": "500",
    "expected": {
        "holdings_value_base": "2000", "open_cost_base": "1800",
        "unrealized_base": "200", "realized_base": "100", "total_pnl_base": "300",
        "net_assets_base": "2500", "invested_ratio": "0.8", "cash_ratio": "0.2",
        "position_weight_of_holdings": "0.5",
    },
}

MISSINGNESS_VECTORS = (
    {
        "id": "LED-NO-CASH",
        "holdings_value_base": "2000",
        "cash": None,
        "expected": {
            "expected_net_assets_base": None,
            "expected_cash_ratio": None,
            "expected_invested_ratio": None,
        },
    },
    {
        "id": "LED-NO-FX",
        "currency": "HKD",
        "market_value": "7800",
        "rate": None,
        "expected": {
            "expected_market_value_base": None,
            "expected_valuation_complete": False,
        },
    },
    {
        "id": "LED-NO-QUOTE",
        "shares": "10",
        "open_cost": "1002",
        "quote": None,
        "expected": {
            "expected_market_value": None,
            "expected_unrealized": None,
        },
    },
)

VECTOR_COUNT = len(LEDGER_VECTORS) + 1 + len(MISSINGNESS_VECTORS)
