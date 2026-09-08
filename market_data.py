```python
import yfinance as yf
import pandas as pd
import numpy as np


def search_stocks(query, limit=15):
    """
    Söker efter aktier, ETF:er, index osv.
    """
    query = query.strip()

    if not query:
        return []

    try:
        search = yf.Search(query)
        quotes = search.quotes

        results = []

        for quote in quotes[:limit]:
            symbol = quote.get("symbol", "")
            name = quote.get("longname") or quote.get("shortname") or symbol

            if symbol:
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "exchange": quote.get("exchange", "")
                })

        return results

    except Exception:
        return []


def get_current_price(symbol):
    """
    Hämtar senaste tillgängliga pris.
    """
    try:
        ticker = yf.Ticker(symbol)

        info = ticker.fast_info

        price = info.get("last_price")

        if price is not None and not np.isnan(price):
            return float(price)

    except Exception:
        pass

    try:
        history = yf.download(
            symbol,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=False
        )

        if not history.empty:
            close = history["Close"]

            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            return float(close.dropna().iloc[-1])

    except Exception:
        pass

    return None


def get_bid_ask(symbol):
    """
    Hämtar/simulerar bid och ask.

    Yahoo Finance ger inte alltid bid/ask.
    Därför används ett litet simulerat spread om riktiga
    bid/ask-värden saknas.
    """
    price = get_current_price(symbol)

    if price is None:
        return None, None, None

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info

        bid = info.get("bid")
        ask = info.get("ask")

        if bid and ask:
            return float(bid), float(ask), float(ask - bid)

    except Exception:
        pass

    spread_percent = 0.0005

    bid = price * (1 - spread_percent)
    ask = price * (1 + spread_percent)

    return bid, ask, ask - bid


def get_stock_data(symbol, period="1d", interval="5m"):
    """
    Hämtar OHLC + volym.
    """

    try:
        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False
        )

        if data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close", "Volume"]

        for column in required:
            if column not in data.columns:
                data[column] = np.nan

        data = data[required].copy()

        data.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

        return data

    except Exception:
        return pd.DataFrame()


def get_market_indices():
    """
    Hämtar stora marknadsindex.
    """

    indices = {
        "OMXS30": "^OMX",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "DAX": "^GDAXI"
    }

    result = []

    for name, symbol in indices.items():
        price = get_current_price(symbol)

        if price is None:
            continue

        try:
            history = yf.download(
                symbol,
                period="2d",
                interval="1d",
                progress=False,
                auto_adjust=False
            )

            if len(history) >= 2:
                close = history["Close"]

                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                previous = float(close.iloc[-2])
                change = price - previous
                change_percent = (change / previous) * 100
            else:
                change = 0
                change_percent = 0

        except Exception:
            change = 0
            change_percent = 0

        result.append({
            "name": name,
            "symbol": symbol,
            "price": price,
            "change": change,
            "change_percent": change_percent
        })

    return result


def get_multiple_prices(symbols):
    """
    Hämtar priser för flera aktier.
    """

    prices = {}

    for symbol in symbols:
        price = get_current_price(symbol)

        if price is not None:
            prices[symbol] = price

    return prices
```
