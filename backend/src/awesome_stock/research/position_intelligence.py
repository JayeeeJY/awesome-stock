"""Deterministic position intelligence for Awesome Stock.

The engine translates market facts, portfolio context, and user discipline into
traceable signals. It deliberately does not call an LLM: models may summarize
the result later, but they must not invent the underlying numbers.
"""

from __future__ import annotations

from math import sqrt, isfinite
from datetime import date
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _mean(values: Sequence[float], period: int) -> Optional[float]:
    if period <= 0 or len(values) < period:
        return None
    return mean(values[-period:])


def _ema(values: Sequence[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append((value * alpha) + (result[-1] * (1 - alpha)))
    return result


def _rsi(values: Sequence[float], period: int = 14) -> Optional[float]:
    if len(values) <= period:
        return None
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0) for change in changes[-period:]]
    losses = [max(-change, 0) for change in changes[-period:]]
    average_gain = mean(gains)
    average_loss = mean(losses)
    if average_gain == 0 and average_loss == 0:
        return None
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _atr(candles: Sequence[Dict[str, float]], period: int = 14) -> Optional[float]:
    if len(candles) <= period:
        return None
    true_ranges: List[float] = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous_close = candles[index - 1]["close"]
        true_ranges.append(
            max(
                current["high"] - current["low"],
                abs(current["high"] - previous_close),
                abs(current["low"] - previous_close),
            )
        )
    return mean(true_ranges[-period:])


def _standard_deviation(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    center = mean(values)
    return sqrt(sum((value - center) ** 2 for value in values) / len(values))


def _round(value: Optional[float], digits: int = 4) -> Optional[float]:
    return round(value, digits) if value is not None else None


def _distance_pct(price: float, level: Optional[float]) -> Optional[float]:
    if not level or level == 0:
        return None
    return ((price - level) / level) * 100


def _nearest_levels(candles: Sequence[Dict[str, float]], price: float) -> Dict[str, Optional[float]]:
    recent = list(candles[-120:])
    supports: List[float] = []
    resistances: List[float] = []
    for index in range(2, len(recent) - 2):
        low = recent[index]["low"]
        high = recent[index]["high"]
        if low == min(item["low"] for item in recent[index - 2 : index + 3]):
            supports.append(low)
        if high == max(item["high"] for item in recent[index - 2 : index + 3]):
            resistances.append(high)

    support_candidates = [level for level in supports if level < price]
    resistance_candidates = [level for level in resistances if level > price]
    if not support_candidates and recent:
        support_candidates = [min(item["low"] for item in recent[-20:])]
    if not resistance_candidates and recent:
        resistance_candidates = [max(item["high"] for item in recent[-20:])]

    return {
        "support": max(support_candidates) if support_candidates else None,
        "resistance": min(resistance_candidates) if resistance_candidates else None,
    }


def _signal(
    code: str,
    category: str,
    severity: str,
    title_zh: str,
    title_en: str,
    evidence: Dict[str, Any],
    action_zh: str,
    action_en: str,
) -> Dict[str, Any]:
    return {
        "code": code,
        "category": category,
        "severity": severity,
        "title": {"zh-CN": title_zh, "en-US": title_en},
        "evidence": evidence,
        "suggested_action": {"zh-CN": action_zh, "en-US": action_en},
    }


class PositionIntelligenceEngine:
    """Calculate an auditable position assessment from normalized facts."""

    framework = "awesome-position-intelligence-v1"

    @staticmethod
    def normalize_candles(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, float]]:
        normalized: List[Dict[str, float]] = []
        dates = set()
        for row in rows:
            # Owner input must contain real OHLCV observations: never synthesize
            # candles from a quote or turn a missing volume into zero.
            if not isinstance(row, dict):
                raise ValueError("daily candle must be an object")
            observed = row.get("trade_date") or row.get("date")
            try:
                if not isinstance(observed, str) or date.fromisoformat(observed).isoformat() != observed:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError("invalid daily candle date") from None
            if observed in dates:
                raise ValueError("duplicate daily candle date")
            values = {key: _number(row.get(key)) for key in ("open", "high", "low", "close", "volume")}
            if any(value is None for value in values.values()):
                raise ValueError("daily candle requires finite OHLCV")
            if any(values[key] <= 0 for key in ("open", "high", "low", "close")) or values["volume"] < 0:
                raise ValueError("invalid daily candle values")
            if not values["low"] <= min(values["open"], values["close"]) <= max(values["open"], values["close"]) <= values["high"]:
                raise ValueError("inconsistent daily candle range")
            dates.add(observed)
            normalized.append({"date": observed, **values})
        normalized.sort(key=lambda item: item["date"])
        return normalized

    def analyze(
        self,
        *,
        ticker: str,
        position: Dict[str, Any],
        history: Iterable[Dict[str, Any]],
        discipline: Optional[Dict[str, Any]] = None,
        thesis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        candles = self.normalize_candles(history)
        closes = [item["close"] for item in candles]
        volumes = [item["volume"] for item in candles]
        current_price = _number(position.get("current_price"))
        if current_price is None and closes:
            current_price = closes[-1]
        average_cost = _number(position.get("avg_cost"))
        weight = _number(position.get("weight")) or 0.0
        signals: List[Dict[str, Any]] = []
        discipline = discipline or {}

        if current_price is None:
            return {
                "framework": self.framework,
                "ticker": ticker,
                "status": "insufficient_data",
                "data_quality": {
                    "history_points": len(candles),
                    "current_price_available": False,
                    "minimum_history_met": len(candles) >= 20,
                },
                "position": position,
                "technical": {},
                "signals": [],
                "decision_summary": {
                    "risk_level": "unknown",
                    "primary_signal": "price_unavailable",
                    "next_step": {
                        "zh-CN": "先补齐有效行情，再生成操作条件。",
                        "en-US": "Restore a valid quote before generating action conditions.",
                    },
                },
            }

        ma_periods = (5, 10, 20, 60, 120, 250)
        moving_averages = {f"ma{period}": _mean(closes, period) for period in ma_periods}
        rsi_14 = _rsi(closes)
        atr_14 = _atr(candles)
        atr_pct = ((atr_14 / current_price) * 100) if atr_14 and current_price else None

        macd_line = None
        macd_signal = None
        macd_histogram = None
        if len(closes) >= 26:
            ema_12 = _ema(closes, 12)
            ema_26 = _ema(closes, 26)
            macd_series = [fast - slow for fast, slow in zip(ema_12, ema_26)]
            signal_series = _ema(macd_series, 9)
            macd_line = macd_series[-1]
            macd_signal = signal_series[-1]
            macd_histogram = macd_line - macd_signal

        bollinger = {"upper": None, "middle": None, "lower": None, "position": None}
        if len(closes) >= 20:
            window = closes[-20:]
            middle = mean(window)
            deviation = _standard_deviation(window)
            upper = middle + (2 * deviation)
            lower = middle - (2 * deviation)
            width = upper - lower
            bollinger = {
                "upper": upper,
                "middle": middle,
                "lower": lower,
                "position": ((current_price - lower) / width) if width else 0.5,
            }

        levels = _nearest_levels(candles, current_price)
        support_distance = _distance_pct(current_price, levels["support"])
        resistance_distance = _distance_pct(levels["resistance"] or 0, current_price)
        cost_distance = _distance_pct(current_price, average_cost)
        volume_average = _mean(volumes, 20)
        volume_ratio = (
            volumes[-1] / volume_average
            if volumes and volume_average and volume_average > 0
            else None
        )

        ma20 = moving_averages["ma20"]
        ma60 = moving_averages["ma60"]
        trend = "insufficient"
        if ma20 is not None and ma60 is not None:
            if current_price > ma20 > ma60:
                trend = "bullish"
            elif current_price < ma20 < ma60:
                trend = "bearish"
            else:
                trend = "range"

        warning_weight = _number(discipline.get("warning_position_weight")) or 0.20
        max_weight = _number(discipline.get("max_position_weight")) or 0.30
        if weight >= max_weight:
            signals.append(
                _signal(
                    "position_above_limit",
                    "discipline",
                    "critical",
                    "仓位超过纪律上限",
                    "Position exceeds discipline limit",
                    {"weight": _round(weight), "limit": _round(max_weight)},
                    "暂停增持，先确认减仓条件或重新设定并记录仓位纪律。",
                    "Pause additions and confirm trim conditions or explicitly revise the position rule.",
                )
            )
        elif weight >= warning_weight:
            signals.append(
                _signal(
                    "position_concentrated",
                    "discipline",
                    "watch",
                    "仓位集中度偏高",
                    "Position concentration is elevated",
                    {"weight": _round(weight), "warning": _round(warning_weight)},
                    "新增风险前先评估组合集中度，不把上涨当作自动增持理由。",
                    "Review concentration before adding risk; price strength alone is not an add signal.",
                )
            )

        if rsi_14 is not None and rsi_14 >= 70:
            signals.append(
                _signal(
                    "rsi_overbought",
                    "momentum",
                    "watch",
                    "RSI 进入超买区",
                    "RSI is overbought",
                    {"rsi14": _round(rsi_14, 2)},
                    "避免追涨；等待回落、横盘消化或成交量继续确认。",
                    "Avoid chasing; wait for a pullback, consolidation, or stronger volume confirmation.",
                )
            )
        elif rsi_14 is not None and rsi_14 <= 30:
            signals.append(
                _signal(
                    "rsi_oversold",
                    "momentum",
                    "watch",
                    "RSI 进入超卖区",
                    "RSI is oversold",
                    {"rsi14": _round(rsi_14, 2)},
                    "超卖不等于见底，等待支撑、量价或趋势止跌信号后再行动。",
                    "Oversold is not a bottom; wait for support, volume-price, or trend stabilization.",
                )
            )

        proximity = max(2.0, (atr_pct or 0) * 0.75)
        if support_distance is not None and 0 <= support_distance <= proximity:
            signals.append(
                _signal(
                    "near_support",
                    "price_structure",
                    "info",
                    "价格接近短期支撑位",
                    "Price is near short-term support",
                    {
                        "support": _round(levels["support"]),
                        "distance_pct": _round(support_distance, 2),
                    },
                    "观察支撑是否被有效守住；只有止跌确认后才评估增持。",
                    "Watch whether support holds; evaluate adding only after stabilization confirms.",
                )
            )
        if resistance_distance is not None and 0 <= resistance_distance <= proximity:
            signals.append(
                _signal(
                    "near_resistance",
                    "price_structure",
                    "watch",
                    "价格接近短期压力位",
                    "Price is near short-term resistance",
                    {
                        "resistance": _round(levels["resistance"]),
                        "distance_pct": _round(resistance_distance, 2),
                    },
                    "观察放量突破或冲高回落；未确认突破前不把压力位当作新起点。",
                    "Watch for a volume-backed breakout or rejection; do not assume resistance has cleared.",
                )
            )

        if cost_distance is not None and cost_distance <= -10:
            signals.append(
                _signal(
                    "below_cost_line",
                    "position",
                    "watch",
                    "价格明显低于持仓成本",
                    "Price is materially below cost",
                    {"cost_distance_pct": _round(cost_distance, 2), "average_cost": _round(average_cost)},
                    "先检查买入逻辑是否仍成立，不因摊低成本而机械补仓。",
                    "Revalidate the thesis before acting; do not average down mechanically.",
                )
            )

        if trend == "bearish":
            signals.append(
                _signal(
                    "trend_bearish",
                    "trend",
                    "watch",
                    "中短期趋势偏弱",
                    "Short-to-medium trend is weak",
                    {"price": _round(current_price), "ma20": _round(ma20), "ma60": _round(ma60)},
                    "将增持条件提高到重新站上关键均线或趋势转强。",
                    "Require a reclaim of key moving averages or a trend turn before adding.",
                )
            )
        elif trend == "bullish" and macd_histogram is not None and macd_histogram > 0:
            signals.append(
                _signal(
                    "trend_confirmed",
                    "trend",
                    "info",
                    "趋势与动能暂时同向",
                    "Trend and momentum are aligned",
                    {"price": _round(current_price), "ma20": _round(ma20), "macd_histogram": _round(macd_histogram)},
                    "保持观察，并用成本线、压力位和仓位纪律约束追涨冲动。",
                    "Maintain observation and use cost, resistance, and position discipline to constrain chasing.",
                )
            )

        if position.get("latest_news_sentiment") == "negative":
            signals.append(
                _signal(
                    "negative_news",
                    "event",
                    "watch",
                    "近期新闻情绪偏负面",
                    "Recent news sentiment is negative",
                    {"category": position.get("latest_news_category")},
                    "核对事件是否改变原有投资逻辑，并记录验证结论。",
                    "Check whether the event changes the thesis and record the conclusion.",
                )
            )
        if position.get("earnings_status") in {"critical", "watch"}:
            signals.append(
                _signal(
                    "earnings_window",
                    "event",
                    "watch",
                    "财报窗口临近",
                    "Earnings window is approaching",
                    {"days_to_earnings": position.get("days_to_earnings")},
                    "提前写下预期、关键验证指标和财报后行动条件。",
                    "Write down expectations, validation metrics, and post-earnings action conditions.",
                )
            )

        severity_rank = {"critical": 3, "watch": 2, "info": 1}
        signals.sort(key=lambda item: severity_rank.get(item["severity"], 0), reverse=True)
        primary = signals[0]["code"] if signals else "no_material_signal"
        risk_level = "critical" if any(item["severity"] == "critical" for item in signals) else (
            "watch" if any(item["severity"] == "watch" for item in signals) else "normal"
        )

        return {
            "framework": self.framework,
            "ticker": ticker,
            "status": "ready" if len(candles) >= 20 else "partial",
            "data_quality": {
                "history_points": len(candles),
                "current_price_available": True,
                "minimum_history_met": len(candles) >= 20,
                "full_trend_history_met": len(candles) >= 60,
            },
            "position": {
                **position,
                "cost_distance_pct": _round(cost_distance, 2),
            },
            "technical": {
                "trend": trend,
                "moving_averages": {key: _round(value) for key, value in moving_averages.items()},
                "rsi14": _round(rsi_14, 2),
                "macd": {
                    "line": _round(macd_line),
                    "signal": _round(macd_signal),
                    "histogram": _round(macd_histogram),
                },
                "bollinger": {key: _round(value) for key, value in bollinger.items()},
                "atr14": _round(atr_14),
                "atr_pct": _round(atr_pct, 2),
                "volume_ratio20": _round(volume_ratio, 2),
                "support": _round(levels["support"]),
                "support_distance_pct": _round(support_distance, 2),
                "resistance": _round(levels["resistance"]),
                "resistance_distance_pct": _round(resistance_distance, 2),
            },
            "discipline": {
                "warning_position_weight": warning_weight,
                "max_position_weight": max_weight,
                "thesis_status": (thesis or {}).get("status"),
                "thesis_confidence": (thesis or {}).get("confidence"),
            },
            "signals": signals,
            "decision_summary": {
                "risk_level": risk_level,
                "primary_signal": primary,
                "next_step": (
                    signals[0]["suggested_action"]
                    if signals
                    else {
                        "zh-CN": "暂无需要立即处理的强信号，按既定纪律继续观察。",
                        "en-US": "No strong signal requires immediate action; continue observing under the existing discipline.",
                    }
                ),
            },
        }


position_intelligence_engine = PositionIntelligenceEngine()
