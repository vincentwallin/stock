```python
import plotly.graph_objects as go
import pandas as pd


def candlestick_chart(data, symbol):
    if data.empty:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name=symbol
        )
    )

    fig.update_layout(
        title=f"{symbol} – Candlestick",
        xaxis_title="Tid",
        yaxis_title="Pris",
        template="plotly_dark",
        height=550,
        xaxis_rangeslider_visible=False
    )

    return fig


def volume_chart(data):
    if data.empty:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["Volume"],
            name="Volym"
        )
    )

    fig.update_layout(
        title="Volym",
        xaxis_title="Tid",
        yaxis_title="Volym",
        template="plotly_dark",
        height=250
    )

    return fig


def portfolio_value_chart(history):
    if not history:
        return None

    df = pd.DataFrame(history)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["value"],
            mode="lines",
            name="Portföljvärde"
        )
    )

    fig.update_layout(
        title="Portföljens utveckling",
        xaxis_title="Tid",
        yaxis_title="Värde (kr)",
        template="plotly_dark",
        height=400
    )

    return fig


def allocation_chart(portfolio, prices):
    labels = []
    values = []

    for symbol, holding in portfolio["holdings"].items():
        price = prices.get(symbol)

        if price is None:
            continue

        value = price * holding["shares"]

        if value > 0:
            labels.append(symbol)
            values.append(value)

    if portfolio["cash"] > 0:
        labels.append("Kontanter")
        values.append(portfolio["cash"])

    if not values:
        return None

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45
            )
        ]
    )

    fig.update_layout(
        title="Tillgångsfördelning",
        template="plotly_dark",
        height=400
    )

    return fig


def pnl_chart(transactions):
    sells = [
        transaction
        for transaction in transactions
        if transaction["side"] == "SELL"
    ]

    if not sells:
        return None

    df = pd.DataFrame(sells)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["timestamp"],
            y=df["pnl"],
            name="P&L"
        )
    )

    fig.update_layout(
        title="Realiserad P&L",
        xaxis_title="Tid",
        yaxis_title="P&L (kr)",
        template="plotly_dark",
        height=350
    )

    return fig
```
