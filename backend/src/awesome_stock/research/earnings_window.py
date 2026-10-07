"""Native approximate earnings window, not an announced event date."""
from datetime import date,datetime,timedelta
from typing import Any,Optional,Dict

def _parse_report_period(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        cleaned = str(value).strip().replace("-", "")
        if len(cleaned) != 8 or not cleaned.isdigit():
            return None
        return datetime.strptime(cleaned, "%Y%m%d").date()
    except Exception:
        return None

def _format_report_label(period_end: Optional[date]) -> Optional[str]:
    if not period_end:
        return None
    quarter = ((period_end.month - 1) // 3) + 1
    return f"{period_end.year}Q{quarter}"

def _advance_quarter(period_end: date) -> date:
    month_map = {
        3: (period_end.year, 6, 30),
        6: (period_end.year, 9, 30),
        9: (period_end.year, 12, 31),
        12: (period_end.year + 1, 3, 31),
    }
    target = month_map.get(period_end.month)
    if target:
        return date(*target)
    quarter = ((period_end.month - 1) // 3) + 1
    quarter_end_month = quarter * 3
    if quarter_end_month == 12:
        return date(period_end.year + 1, 3, 31)
    end_map = {3: 31, 6: 30, 9: 30, 12: 31}
    return date(period_end.year, quarter_end_month + 3, end_map[quarter_end_month + 3])

def _estimate_earnings_due_date(market: str, period_end: date) -> date:
    if market == "CN":
        if period_end.month == 3:
            return date(period_end.year, 4, 30)
        if period_end.month == 6:
            return date(period_end.year, 8, 31)
        if period_end.month == 9:
            return date(period_end.year, 10, 31)
        return date(period_end.year + 1, 4, 30)
    if period_end.month == 12:
        return period_end + timedelta(days=75)
    return period_end + timedelta(days=45)

def _previous_quarter_end(today: date) -> date:
    current_quarter = ((today.month - 1) // 3) + 1
    if current_quarter == 1:
        return date(today.year - 1, 12, 31)
    if current_quarter == 2:
        return date(today.year, 3, 31)
    if current_quarter == 3:
        return date(today.year, 6, 30)
    return date(today.year, 9, 30)

def _build_earnings_reminder(
    market: str,
    latest_report_period: Any = None,
    latest_report_type: Optional[str] = None,
    *, evaluated_on: date,
) -> Dict[str, Any]:
    today = evaluated_on
    latest_period_end = _parse_report_period(latest_report_period)
    candidate_period = _advance_quarter(latest_period_end) if latest_period_end else _previous_quarter_end(today)
    due_date = _estimate_earnings_due_date(market, candidate_period)
    while due_date < today:
        candidate_period = _advance_quarter(candidate_period)
        due_date = _estimate_earnings_due_date(market, candidate_period)

    days_to_earnings = (due_date - today).days
    if days_to_earnings <= 7:
        status = "critical"
        status_text = "财报窗口临近"
    elif days_to_earnings <= 21:
        status = "watch"
        status_text = "建议提前关注财报"
    else:
        status = "normal"
        status_text = "暂未进入财报临近窗口"

    return {
        "latest_report_period": latest_period_end.isoformat() if latest_period_end else None,
        "latest_report_label": _format_report_label(latest_period_end),
        "latest_report_type": latest_report_type,
        "next_report_period": candidate_period.isoformat(),
        "next_report_label": _format_report_label(candidate_period),
        "estimated_next_earnings_date": due_date.isoformat(),
        "days_to_earnings": days_to_earnings,
        "earnings_status": status,
        "earnings_status_text": status_text,
        "is_estimated": True,
    }
