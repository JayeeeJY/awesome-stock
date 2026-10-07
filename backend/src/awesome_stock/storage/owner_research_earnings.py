"""Source-backed estimated window shared by research contexts."""
from datetime import date
from . import owner_company as company
from awesome_stock.research.earnings_window import _build_earnings_reminder


def calculate(db,symbol,evaluated_on):
    today=date.fromisoformat(evaluated_on)
    source=company.latest(db,symbol)
    period=source['company'].get('latest_quarter') if source else None
    earnings_window=None
    if period and period<=evaluated_on:
        estimate=_build_earnings_reminder(source['market'],period,evaluated_on=today)
        earnings_window={**estimate,'source_evidence':source,'evaluated_on':evaluated_on,'confirmed':False,'formula':'native-quarter-window-owner-v1','notice':'依据最近财季按原版固定间隔推算，并滚动至尚未过去的窗口；非公司公告日期，不是交易日历或已发生事件。实际日期、非自然季度财年及来源是否仍有效需另行核对。'}
    return earnings_window
