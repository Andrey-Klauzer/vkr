
PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "USD/RUB": "RUB=X",
    "EUR/RUB": "EURRUB=X",
}

PAIR_CONTEXT = {
    "EUR/USD": ["DX-Y.NYB", "HYG"],
    "GBP/USD": ["DX-Y.NYB", "HYG"],
    "USD/JPY": ["^N225", "^TNX"],
    "USD/CHF": ["GC=F", "LQD"],
    "AUD/USD": ["^TNX", "^GSPC"],
    "USD/CAD": ["DX-Y.NYB", "BZ=F"],
    "NZD/USD": ["^TNX", "^GSPC"],
    "EUR/GBP": ["NG=F", "BZ=F"],
    "USD/RUB": ["DX-Y.NYB", "GC=F"],
    "EUR/RUB": ["^STOXX50E", "NG=F"],
}


def all_tickers() -> list[str]:
    out = list(PAIRS.values())
    for ctx in PAIR_CONTEXT.values():
        out.extend(ctx)
    return sorted(set(out))
