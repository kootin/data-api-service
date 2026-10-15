import math

from app import schemas


def returns_summary(symbol: str, prices: list[schemas.PriceOut]) -> schemas.ReturnsOut:
    closes = [float(p.close) for p in prices]
    if len(closes) < 2:
        raise ValueError("need at least two prices")
    rets = [b / a - 1 for a, b in zip(closes, closes[1:], strict=False)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
    peak, mdd = closes[0], 0.0
    for c in closes:
        peak = max(peak, c)
        mdd = min(mdd, c / peak - 1)
    return schemas.ReturnsOut(
        symbol=symbol,
        start=prices[0].price_date,
        end=prices[-1].price_date,
        observations=len(closes),
        total_return_pct=round((closes[-1] / closes[0] - 1) * 100, 4),
        annualised_volatility_pct=round(math.sqrt(var) * math.sqrt(252) * 100, 4),
        max_drawdown_pct=round(mdd * 100, 4),
    )
