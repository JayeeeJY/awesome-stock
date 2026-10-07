from awesome_stock.research.position_intelligence import PositionIntelligenceEngine


def _candles(count: int = 90, *, start: float = 80.0, step: float = 1.0):
    rows = []
    for index in range(count):
        close = start + (index * step)
        rows.append(
            {
                "trade_date": f"2026-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
                "open": close - 0.4,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000 + (index * 10_000),
            }
        )
    return rows


def test_position_intelligence_is_deterministic_and_discipline_first():
    engine = PositionIntelligenceEngine()
    report = engine.analyze(
        ticker="BABA",
        position={
            "current_price": 169.0,
            "avg_cost": 120.0,
            "weight": 0.34,
            "shares": 1000,
        },
        history=_candles(),
        discipline={
            "warning_position_weight": 0.20,
            "max_position_weight": 0.30,
        },
    )

    codes = {signal["code"] for signal in report["signals"]}
    assert report["framework"] == "awesome-position-intelligence-v1"
    assert report["status"] == "ready"
    assert report["decision_summary"]["risk_level"] == "critical"
    assert report["decision_summary"]["primary_signal"] == "position_above_limit"
    assert "position_above_limit" in codes
    assert "rsi_overbought" in codes
    assert report["technical"]["trend"] == "bullish"
    assert report["position"]["cost_distance_pct"] == 40.83


def test_position_intelligence_reports_missing_price_honestly():
    report = PositionIntelligenceEngine().analyze(
        ticker="MSFT",
        position={"current_price": None, "avg_cost": 410, "weight": 0.1},
        history=[],
    )

    assert report["status"] == "insufficient_data"
    assert report["technical"] == {}
    assert report["signals"] == []
    assert report["decision_summary"]["risk_level"] == "unknown"


def test_position_intelligence_output_keeps_bilingual_actions():
    report = PositionIntelligenceEngine().analyze(
        ticker="NVDA",
        position={"current_price": 169.0, "avg_cost": 120.0, "weight": 0.25},
        history=_candles(),
    )

    assert report["signals"]
    for signal in report["signals"]:
        assert signal["title"]["zh-CN"]
        assert signal["title"]["en-US"]
        assert signal["suggested_action"]["zh-CN"]
        assert signal["suggested_action"]["en-US"]


import pytest
import json

@pytest.mark.parametrize('change',[
    {'close':float('nan')},{'high':float('inf')},{'low':-1},
    {'volume':None},{'volume':-1},{'open':None},{'high':1},
    {'trade_date':'2026-02-30'}, {'trade_date':'not-a-date'},
])
def test_rejects_invalid_or_fabricated_candles(change):
    rows=_candles(1);rows[0].update(change)
    with pytest.raises(ValueError):PositionIntelligenceEngine().normalize_candles(rows)


def test_rejects_quote_only_and_duplicate_dates():
    engine=PositionIntelligenceEngine()
    with pytest.raises(ValueError):engine.normalize_candles([{'date':'2026-01-01','price':100}])
    row=_candles(1)[0]
    with pytest.raises(ValueError):engine.normalize_candles([row,row])


def test_complete_history_is_order_independent_and_json_finite():
    engine=PositionIntelligenceEngine();args=dict(ticker='TEST',position={'current_price':169,'avg_cost':120,'weight':.34})
    expected=engine.analyze(history=_candles(),**args)
    assert engine.analyze(history=list(reversed(_candles())),**args)==expected
    json.dumps(expected,allow_nan=False)
    assert expected['technical']['moving_averages']['ma250'] is None


def test_short_history_does_not_invent_rsi_or_trend():
    result=PositionIntelligenceEngine().analyze(ticker='TEST',position={'current_price':80,'weight':.1},history=_candles(1))
    assert result['technical']['rsi14'] is None
    assert result['technical']['trend']=='insufficient'
    assert not result['data_quality']['minimum_history_met']


def test_boolean_values_are_not_market_numbers():
    row=_candles(1)[0];row['volume']=True
    with pytest.raises(ValueError):PositionIntelligenceEngine().normalize_candles([row])


@pytest.mark.parametrize('step,expected',[(0,None),(1,100),(-.5,0)])
def test_rsi_flat_and_one_direction_windows(step,expected):
    rows=_candles(90,start=100,step=step)
    report=PositionIntelligenceEngine().analyze(ticker='TEST',position={'current_price':rows[-1]['close'],'weight':.1},history=rows)
    assert report['technical']['rsi14']==expected
    if step==0:
        assert not any(signal['code'] in {'rsi_overbought','rsi_oversold'} for signal in report['signals'])
