"""Normalize supplied labels/scores using the native classifier, never article text."""
from decimal import Decimal
import re


def supplied(ticker):
    label=ticker.get('ticker_sentiment_label')
    if label is not None and (not isinstance(label,str) or len(label)>100):raise ValueError('invalid sentiment label')
    score=ticker.get('ticker_sentiment_score')
    if score is not None:
        if not isinstance(score,str) or not re.fullmatch(r'-?(?:0|1)(?:\.[0-9]{1,16})?',score) or not -1<=Decimal(score)<=1:raise ValueError('invalid sentiment score')
    raw=(label or '').strip().lower()
    if raw in {'positive','bullish','somewhat-bullish','正面','正向','利好'}:normalized='positive'
    elif raw in {'negative','bearish','somewhat-bearish','负面','负向','利空'}:normalized='negative'
    elif raw in {'neutral','中性','mixed'}:normalized='neutral'
    elif score is not None:normalized='positive' if Decimal(score)>Decimal('.15') else 'negative' if Decimal(score)<Decimal('-.15') else 'neutral'
    else:normalized=None
    return {'label':label,'score':score,'normalized':normalized,'basis':'supplier_ticker_label_then_score_native_mapping','verified':False}
