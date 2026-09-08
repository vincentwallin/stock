```python
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
import time

# ============================================================
# INSTÄLLNINGAR
# ============================================================

st.set_page_config(
    page_title="StockTrader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

COMMISSION_RATE = 0.02  # 2 %
DATA_FILE = Path("portfolios.json")


# ============================================================
# MÖRKT UI
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #0b0f14;
        color: #e8edf3;
    }

    section[data-testid="stSidebar"] {
        background-color: #080c11;
        border-right: 1px solid #202832;
    }

    .block-container {
        padding-top: 1.5rem;
        max-width: 1600px;
    }

    div[data-testid="stMetric"] {
        background-color: #111720;
        border: 1px solid #202832;
        border-radius: 10px;
        padding: 15px;
    }

    div[data-testid="stMetricLabel"] {
        color: #8e9aa8;
    }

    div[data-testid="stMetricValue"] {
        color: #f1f5f9;
    }

    .stock-card {
        background-color: #111720;
        border: 1px solid #202832;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 10px;
    }

    .green {
        color: #35d07f;
    }

    .red {
        color: #ff5c6c;
    }

    .gray {
        color: #8e9aa8;
    }

    .trade-box {
        background-color: #111720;
        border: 1px solid #202832;
        border-radius: 12px;
        padding: 20px;
    }

    h1, h2, h3 {
        color: #f1f5f9;
    }

    button {
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATAHANTERING
# ============================================================

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.portfolios, f, indent=4)
    except Exception as e:
        st.error(f"Kunde inte spara data: {e}")


def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "Min portfölj": {
            "starting_balance": 50000.0,
            "balance": 50000.0,
            "holdings": {},
            "transactions": [],
            "performance": [],
            "watchlist": ["AAPL", "NVDA", "TSLA"],
            "created": datetime.now().isoformat()
        }
    }


if "portfolios" not in st.session_state:
    st.session_state.portfolios = load_data()

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = "AAPL"

if "search_results" not in st.session_state:
    st.session_state.search_results = []


# ============================================================
# HÄMTA AKTIEDATA
# ============================================================

@st.cache_data(ttl=20)
def get_stock_data(symbol, period="1d", interval="5m"):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(
            period=period,
            interval=interval,
            auto_adjust=False
        )

        if data.empty:
            return None

        data = data.dropna()

        return data

    except Exception:
        return None


@st.cache_data(ttl=60)
def get_stock_info(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return {
            "name": info.get("longName", symbol),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "sector": info.get("sector", ""),
        }

    except Exception:
        return {
            "name": symbol,
            "currency": "",
            "exchange": "",
            "sector": ""
        }


def get_current_price(symbol):
    data = get_stock_data(symbol, "1d", "1m")

    if data is None or data.empty:
        return None

    return float(data["Close"].iloc[-1])


# ============================================================
# SÖK AKTIER
# ============================================================

@st.cache_data(ttl=300)
def search_stocks(query):
    try:
        search = yf.Search(query)
        quotes = search.quotes

        results = []

        for quote in quotes[:10]:
            symbol = quote.get("symbol")
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


# ============================================================
# PORTFÖLJ
# ============================================================

def current_portfolio():
    name = st.session_state.selected_portfolio
    return st.session_state.portfolios[name]


def portfolio_value(portfolio):
    value = portfolio["balance"]

    for symbol, holding in portfolio["holdings"].items():
        price = get_current_price(symbol)

        if price is not None:
            value += holding["shares"] * price

    return value


def holdings_value(portfolio):
    total = 0

    for symbol, holding in portfolio["holdings"].items():
        price = get_current_price(symbol)

        if price is not None:
            total += holding["shares"] * price

    return total


def total_pnl(portfolio):
    value = portfolio_value(portfolio)
    starting = portfolio["starting_balance"]

    return value - starting


# ============================================================
# BUY
# ============================================================

def buy_stock(symbol, shares):
    portfolio = current_portfolio()

    if shares <= 0:
        return False, "Antalet aktier måste vara större än 0."

    if int(shares) != shares:
        return False, "Du kan endast köpa hela aktier."

    shares = int(shares)

    price = get_current_price(symbol)

    if price is None:
        return False, "Kunde inte hämta aktuell aktiekurs."

    ask_price = price * 1.0005

    subtotal = ask_price * shares
    commission = subtotal * COMMISSION_RATE
    total_cost = subtotal + commission

    if total_cost > portfolio["balance"]:
        return False, (
            f"Du har inte tillräckligt med pengar. "
            f"Totalkostnad: {total_cost:,.2f} kr"
        )

    portfolio["balance"] -= total_cost

    if symbol not in portfolio["holdings"]:
        portfolio["holdings"][symbol] = {
            "shares": 0,
            "avg_price": 0.0
        }

    holding = portfolio["holdings"][symbol]

    old_shares = holding["shares"]
    old_avg = holding["avg_price"]

    new_shares = old_shares + shares

    if new_shares > 0:
        new_avg = (
            (old_shares * old_avg) +
            (shares * ask_price)
        ) / new_shares
    else:
        new_avg = ask_price

    holding["shares"] = new_shares
    holding["avg_price"] = round(new_avg, 4)

    transaction = {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "type": "Köp",
        "shares": shares,
        "price": round(ask_price, 4),
        "commission": round(commission, 2),
        "total": round(total_cost, 2)
    }

    portfolio["transactions"].append(transaction)

    save_data()

    return True, (
        f"Köpte {shares} {symbol} för "
        f"{total_cost:,.2f} kr."
    )


# ============================================================
# SELL
# ============================================================

def sell_stock(symbol, shares):
    portfolio = current_portfolio()

    if shares <= 0:
        return False, "Antalet aktier måste vara större än 0."

    if int(shares) != shares:
        return False, "Du kan endast sälja hela aktier."

    shares = int(shares)

    if symbol not in portfolio["holdings"]:
        return False, "Du äger inte den här aktien."

    holding = portfolio["holdings"][symbol]

    if shares > holding["shares"]:
        return False, "Du äger inte så många aktier."

    price = get_current_price(symbol)

    if price is None:
        return False, "Kunde inte hämta aktuell aktiekurs."

    bid_price = price * 0.9995

    subtotal = bid_price * shares
    commission = subtotal * COMMISSION_RATE
    received = subtotal - commission

    portfolio["balance"] += received

    holding["shares"] -= shares

    if holding["shares"] <= 0:
        del portfolio["holdings"][symbol]

    transaction = {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "type": "Sälj",
        "shares": shares,
        "price": round(bid_price, 4),
        "commission": round(commission, 2),
        "total": round(received, 2)
    }

    portfolio["transactions"].append(transaction)

    save_data()

    return True, (
        f"Sålde {shares} {symbol} och fick "
        f"{received:,.2f} kr."
    )


# ============================================================
# STOP LOSS / TAKE PROFIT
# ============================================================

def check_orders():
    portfolio = current_portfolio()

    for symbol in list(portfolio["holdings"].keys()):

        holding = portfolio["holdings"][symbol]

        current_price = get_current_price(symbol)

        if current_price is None:
            continue

        stop_loss = holding.get("stop_loss")
        take_profit = holding.get("take_profit")

        if stop_loss is not None and current_price <= stop_loss:

            shares = holding["shares"]

            sell_stock(symbol, shares)

            st.warning(
                f"STOP-LOSS utlöst för {symbol}."
            )

        elif take_profit is not None and current_price >= take_profit:

            shares = holding["shares"]

            sell_stock(symbol, shares)

            st.success(
                f"TAKE-PROFIT utlöst för {symbol}."
            )


# ============================================================
# PORTFÖLJVÄRDE HISTORIK
# ============================================================

def save_performance():
    portfolio = current_portfolio()

    value = portfolio_value(portfolio)

    portfolio["performance"].append({
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "value": round(value, 2)
    })

    # Behåll senaste 5000 mätningar
    portfolio["performance"] = portfolio["performance"][-5000:]

    save_data()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📈 StockTrader")

st.sidebar.markdown("---")

portfolio_names = list(st.session_state.portfolios.keys())

if "selected_portfolio" not in st.session_state:
    st.session_state.selected_portfolio = portfolio_names[0]

selected = st.sidebar.selectbox(
    "Portfölj",
    portfolio_names,
    index=portfolio_names.index(
        st.session_state.selected_portfolio
    )
)

st.session_state.selected_portfolio = selected

st.sidebar.markdown("---")

st.sidebar.subheader("Portföljer")

with st.sidebar.expander("➕ Skapa ny portfölj"):

    new_name = st.text_input(
        "Portföljnamn"
    )

    new_balance = st.number_input(
        "Startkapital (kr)",
        min_value=0.0,
        value=50000.0,
        step=1000.0
    )

    if st.button("Skapa portfölj", use_container_width=True):

        if not new_name.strip():
            st.error("Ange ett namn.")

        elif new_name in st.session_state.portfolios:
            st.error("Den portföljen finns redan.")

        else:

            st.session_state.portfolios[new_name] = {
                "starting_balance": new_balance,
                "balance": new_balance,
                "holdings": {},
                "transactions": [],
                "performance": [],
                "watchlist": [],
                "created": datetime.now().isoformat()
            }

            st.session_state.selected_portfolio = new_name

            save_data()

            st.success("Portfölj skapad.")
            st.rerun()


with st.sidebar.expander("⚙️ Portföljinställningar"):

    if st.button(
        "Återställ denna portfölj",
        use_container_width=True
    ):

        portfolio = current_portfolio()

        portfolio["balance"] = portfolio["starting_balance"]
        portfolio["holdings"] = {}
        portfolio["transactions"] = []
        portfolio["performance"] = []

        save_data()

        st.success("Portföljen återställd.")
        st.rerun()


# ============================================================
# WATCHLIST
# ============================================================

st.sidebar.markdown("---")
st.sidebar.subheader("⭐ Bevakningslista")

portfolio = current_portfolio()

for symbol in portfolio["watchlist"]:

    price = get_current_price(symbol)

    if price is not None:

        col1, col2 = st.sidebar.columns([2, 1])

        with col1:
            if st.button(
                symbol,
                key=f"watch_{symbol}",
                use_container_width=True
            ):
                st.session_state.selected_stock = symbol
                st.rerun()

        with col2:
            st.write(f"{price:.2f}")


watch_add = st.sidebar.text_input(
    "Lägg till aktie",
    placeholder="t.ex. TSLA"
)

if st.sidebar.button(
    "Lägg till",
    use_container_width=True
):

    symbol = watch_add.upper().strip()

    if symbol and symbol not in portfolio["watchlist"]:

        portfolio["watchlist"].append(symbol)

        save_data()

        st.rerun()


# ============================================================
# HEADER
# ============================================================

st.title("📈 StockTrader")

st.caption(
    "Aktiesimulator med riktiga marknadsdata • "
    "2 % courtage • Ingen riktig order skickas"
)

# ============================================================
# MARKNADS-TICKER
# ============================================================

ticker_symbols = [
    "^OMX",
    "^GSPC",
    "^IXIC",
    "^DJI"
]

ticker_names = [
    "OMXS",
    "S&P 500",
    "NASDAQ",
    "DOW JONES"
]

ticker_cols = st.columns(4)

for col, symbol, name in zip(
    ticker_cols,
    ticker_symbols,
    ticker_names
):

    data = get_stock_data(
        symbol,
        "5d",
        "1d"
    )

    if data is not None and not data.empty:

        current = float(data["Close"].iloc[-1])

        if len(data) > 1:
            previous = float(data["Close"].iloc[-2])
            change = current - previous
            percent = (change / previous) * 100
        else:
            change = 0
            percent = 0

        col.metric(
            name,
            f"{current:,.2f}",
            f"{percent:+.2f}%"
        )


# ============================================================
# PORTFÖLJ-METRICS
# ============================================================

st.markdown("---")

p_value = portfolio_value(portfolio)
cash = portfolio["balance"]
stocks_value = holdings_value(portfolio)
pnl = p_value - portfolio["starting_balance"]

pnl_percent = (
    (pnl / portfolio["starting_balance"]) * 100
    if portfolio["starting_balance"] > 0
    else 0
)

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Portföljvärde",
    f"{p_value:,.2f} kr"
)

m2.metric(
    "Kontanter",
    f"{cash:,.2f} kr"
)

m3.metric(
    "Aktier",
    f"{stocks_value:,.2f} kr"
)

m4.metric(
    "Total P/L",
    f"{pnl:,.2f} kr",
    f"{pnl_percent:+.2f}%"
)


# ============================================================
# AKTIESÖKNING
# ============================================================

st.markdown("---")

st.subheader("🔎 Sök efter aktie")

search_col1, search_col2 = st.columns([4, 1])

with search_col1:

    search_query = st.text_input(
        "Sök",
        placeholder="Sök på aktienamn eller ticker, t.ex. Nvidia, Volvo, Apple...",
        label_visibility="collapsed"
    )

with search_col2:

    search_button = st.button(
        "Sök",
        use_container_width=True
    )


if search_button and search_query:

    results = search_stocks(search_query)

    if results:
        st.session_state.search_results = results
    else:
        st.warning("Inga aktier hittades.")


if st.session_state.search_results:

    st.write("**Sökresultat:**")

    for result in st.session_state.search_results:

        col1, col2, col3 = st.columns([2, 5, 2])

        with col1:
            st.write(f"**{result['symbol']}**")

        with col2:
            st.write(result["name"])

        with col3:

            if st.button(
                "Öppna",
                key=f"open_{result['symbol']}"
            ):

                st.session_state.selected_stock = result["symbol"]
                st.session_state.search_results = []

                st.rerun()


# ============================================================
# VALD AKTIE
# ============================================================

symbol = st.session_state.selected_stock

info = get_stock_info(symbol)

st.markdown("---")

st.header(
    f"{info['name']} ({symbol})"
)

st.caption(
    f"Börs: {info['exchange']} • "
    f"Valuta: {info['currency']}"
)


# ============================================================
# AKTIEPRIS
# ============================================================

stock_data = get_stock_data(
    symbol,
    "1d",
    "1m"
)

if stock_data is None or stock_data.empty:

    st.error(
        "Kunde inte hämta data för denna aktie."
    )

    st.stop()


current_price = float(
    stock_data["Close"].iloc[-1]
)

previous_close = float(
    stock_data["Close"].iloc[0]
)

price_change = current_price - previous_close

price_percent = (
    price_change / previous_close * 100
    if previous_close != 0
    else 0
)

price_col1, price_col2, price_col3, price_col4 = st.columns(4)

price_col1.metric(
    "Senaste kurs",
    f"{current_price:,.2f}"
)

price_col2.metric(
    "Förändring",
    f"{price_change:+,.2f}",
    f"{price_percent:+.2f}%"
)

bid = current_price * 0.9995
ask = current_price * 1.0005

price_col3.metric(
    "Bid",
    f"{bid:,.2f}"
)

price_col4.metric(
    "Ask",
    f"{ask:,.2f}"
)


# ============================================================
# GRAF
# ============================================================

st.markdown("---")

chart_col1, chart_col2 = st.columns([5, 1])

with chart_col1:

    st.subheader("📊 Kursgraf")

with chart_col2:

    timeframe = st.selectbox(
        "Intervall",
        [
            "1 minut",
            "5 minuter",
            "15 minuter",
            "1 timme",
            "1 dag"
        ]
    )


if timeframe == "1 minut":
    period = "1d"
    interval = "1m"

elif timeframe == "5 minuter":
    period = "5d"
    interval = "5m"

elif timeframe == "15 minuter":
    period = "5d"
    interval = "15m"

elif timeframe == "1 timme":
    period = "1mo"
    interval = "1h"

else:
    period = "1y"
    interval = "1d"


chart_data = get_stock_data(
    symbol,
    period,
    interval
)


if chart_data is not None and not chart_data.empty:

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_data.index,
            open=chart_data["Open"],
            high=chart_data["High"],
            low=chart_data["Low"],
            close=chart_data["Close"],
            name=symbol
        )
    )

    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        ),
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#0b0f14",
        plot_bgcolor="#0b0f14"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# TRADING
# ============================================================

st.markdown("---")

trade_col, position_col = st.columns([1, 1])

with trade_col:

    st.subheader("⚡ Handla")

    shares = st.number_input(
        "Antal aktier",
        min_value=1,
        value=1,
        step=1
    )

    estimated_buy = ask * shares
    buy_fee = estimated_buy * COMMISSION_RATE
    buy_total = estimated_buy + buy_fee

    estimated_sell = bid * shares
    sell_fee = estimated_sell * COMMISSION_RATE
    sell_total = estimated_sell - sell_fee

    st.markdown(
        f"""
        **Köp**

        Kurs: `{ask:,.2f} kr`  
        Aktier: `{shares}`  
        Courtage (2 %): `{buy_fee:,.2f} kr`  
        **Totalt: `{buy_total:,.2f} kr`**
        """
    )

    if st.button(
        "🟢 KÖP",
        use_container_width=True
    ):

        success, message = buy_stock(
            symbol,
            shares
        )

        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.markdown("---")

    st.markdown(
        f"""
        **Sälj**

        Kurs: `{bid:,.2f} kr`  
        Aktier: `{shares}`  
        Courtage (2 %): `{sell_fee:,.2f} kr`  
        **Du får: `{sell_total:,.2f} kr`**
        """
    )

    if st.button(
        "🔴 SÄLJ",
        use_container_width=True
    ):

        success, message = sell_stock(
            symbol,
            shares
        )

        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)


# ============================================================
# STOP LOSS / TAKE PROFIT
# ============================================================

with position_col:

    st.subheader("🎯 Riskhantering")

    if symbol in portfolio["holdings"]:

        holding = portfolio["holdings"][symbol]

        owned = holding["shares"]
        avg_price = holding["avg_price"]

        st.metric(
            "Du äger",
            f"{owned} aktier"
        )

        st.metric(
            "Genomsnittligt inköpspris",
            f"{avg_price:,.2f} kr"
        )

        position_pnl = (
            current_price - avg_price
        ) * owned

        position_percent = (
            (current_price - avg_price)
            / avg_price
            * 100
            if avg_price != 0
            else 0
        )

        st.metric(
            "P/L på position",
            f"{position_pnl:,.2f} kr",
            f"{position_percent:+.2f}%"
        )

        st.markdown("---")

        stop_loss = st.number_input(
            "Stop-loss",
            min_value=0.0,
            value=float(
                holding.get("stop_loss") or 0
            ),
            step=0.01
        )

        take_profit = st.number_input(
            "Take-profit",
            min_value=0.0,
            value=float(
                holding.get("take_profit") or 0
            ),
            step=0.01
        )

        if st.button(
            "Spara risknivåer",
            use_container_width=True
        ):

            holding["stop_loss"] = (
                stop_loss if stop_loss > 0 else None
            )

            holding["take_profit"] = (
                take_profit if take_profit > 0 else None
            )

            save_data()

            st.success(
                "Risknivåerna har sparats."
            )
            st.rerun()

    else:

        st.info(
            "Du äger inte denna aktie ännu."
        )


# ============================================================
# PORTFÖLJFÖRDELNING
# ============================================================

st.markdown("---")

allocation_col, performance_col = st.columns(2)

with allocation_col:

    st.subheader("🥧 Tillgångsfördelning")

    labels = ["Kontanter"]
    values = [cash]

    for stock_symbol, holding in portfolio["holdings"].items():

        price = get_current_price(stock_symbol)

        if price is not None:

            value = holding["shares"] * price

            labels.append(stock_symbol)
            values.append(value)

    if sum(values) > 0:

        pie = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.55
                )
            ]
        )

        pie.update_layout(
            template="plotly_dark",
            height=400,
            paper_bgcolor="#0b0f14"
        )

        st.plotly_chart(
            pie,
            use_container_width=True
        )


# ============================================================
# PORTFÖLJUTVECKLING
# ============================================================

with performance_col:

    st.subheader("📈 Portföljutveckling")

    save_performance()

    performance = portfolio["performance"]

    if performance:

        df = pd.DataFrame(performance)

        df["datetime"] = pd.to_datetime(
            df["datetime"]
        )

        line = go.Figure()

        line.add_trace(
            go.Scatter(
                x=df["datetime"],
                y=df["value"],
                mode="lines",
                name="Portföljvärde"
            )
        )

        line.update_layout(
            template="plotly_dark",
            height=400,
            paper_bgcolor="#0b0f14",
            plot_bgcolor="#0b0f14",
            yaxis_title="Värde (kr)",
            xaxis_title=""
        )

        st.plotly_chart(
            line,
            use_container_width=True
        )


# ============================================================
# INNEHAV
# ============================================================

st.markdown("---")

st.subheader("💼 Mina innehav")

if portfolio["holdings"]:

    rows = []

    for stock_symbol, holding in portfolio["holdings"].items():

        price = get_current_price(stock_symbol)

        if price is None:
            continue

        shares_owned = holding["shares"]
        avg_price = holding["avg_price"]

        value = price * shares_owned

        pnl_value = (
            price - avg_price
        ) * shares_owned

        pnl_pct = (
            (price - avg_price)
            / avg_price
            * 100
            if avg_price != 0
            else 0
        )

        rows.append({
            "Aktie": stock_symbol,
            "Antal": shares_owned,
            "Snittpris": f"{avg_price:,.2f} kr",
            "Aktuell kurs": f"{price:,.2f} kr",
            "Värde": f"{value:,.2f} kr",
            "P/L": f"{pnl_value:+,.2f} kr",
            "P/L %": f"{pnl_pct:+.2f}%"
        })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

else:

    st.info(
        "Du har inga aktier i denna portfölj."
    )


# ============================================================
# TRANSAKTIONSLOGG
# ============================================================

st.markdown("---")

st.subheader("📝 Transaktionslogg")

transactions = portfolio["transactions"]

if transactions:

    transaction_df = pd.DataFrame(
        transactions[::-1]
    )

    transaction_df.columns = [
        "Datum/Tid",
        "Aktie",
        "Typ",
        "Antal",
        "Kurs",
        "Courtage",
        "Total"
    ]

    transaction_df["Kurs"] = (
        transaction_df["Kurs"]
        .map(lambda x: f"{x:,.2f} kr")
    )

    transaction_df["Courtage"] = (
        transaction_df["Courtage"]
        .map(lambda x: f"{x:,.2f} kr")
    )

    transaction_df["Total"] = (
        transaction_df["Total"]
        .map(lambda x: f"{x:,.2f} kr")
    )

    st.dataframe(
        transaction_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Inga transaktioner ännu."
    )


# ============================================================
# TRADING-STATISTIK
# ============================================================

st.markdown("---")

st.subheader("📊 Trading-statistik")

transactions = portfolio["transactions"]

buy_transactions = [
    x for x in transactions
    if x["type"] == "Köp"
]

sell_transactions = [
    x for x in transactions
    if x["type"] == "Sälj"
]

total_trades = len(sell_transactions)

realized_pnl = 0
wins = 0
losses = 0

# Enkel FIFO-liknande beräkning
open_positions = {}

for transaction in transactions:

    symbol_t = transaction["symbol"]

    if symbol_t not in open_positions:
        open_positions[symbol_t] = []

    if transaction["type"] == "Köp":

        open_positions[symbol_t].append({
            "shares": transaction["shares"],
            "price": transaction["price"]
        })

    elif transaction["type"] == "Sälj":

        remaining = transaction["shares"]
        sell_price = transaction["price"]

        while remaining > 0 and open_positions[symbol_t]:

            lot = open_positions[symbol_t][0]

            used = min(
                remaining,
                lot["shares"]
            )

            trade_pnl = (
                sell_price - lot["price"]
            ) * used

            realized_pnl += trade_pnl

            if trade_pnl > 0:
                wins += 1

            else:
                losses += 1

            lot["shares"] -= used
            remaining -= used

            if lot["shares"] <= 0:
                open_positions[symbol_t].pop(0)


win_rate = (
    wins / (wins + losses) * 100
    if wins + losses > 0
    else 0
)

s1, s2, s3, s4 = st.columns(4)

s1.metric(
    "Stängda positioner",
    str(total_trades)
)

s2.metric(
    "Win rate",
    f"{win_rate:.2f}%"
)

s3.metric(
    "Realiserad P/L",
    f"{realized_pnl:+,.2f} kr"
)

s4.metric(
    "Totalt antal köp",
    str(len(buy_transactions))
)


# ============================================================
# INFO
# ============================================================

st.markdown("---")

st.caption(
    "StockTrader är en utbildningssimulator. "
    "Marknadsdata hämtas från Yahoo Finance via yfinance. "
    "Inga riktiga köp eller säljorder skickas till börsen. "
    "Marknadsdata kan vara fördröjd beroende på börs och datakälla."
)


# ============================================================
# AUTOMATISK KONTROLL AV STOP-LOSS / TAKE-PROFIT
# ============================================================

try:
    check_orders()
except Exception:
    pass
```

### `requirements.txt`

```text
streamlit>=1.40.0
yfinance>=0.2.50
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.20.0
```

### Så fungerar den

1. **Skapa portfölj** → välj namn och startkapital.
2. **Sök aktie** → exempelvis `Nvidia`, `Apple`, `Volvo`, `Tesla`.
3. Tryck **Öppna**.
4. Du får aktuell marknadsdata och candlestick-graf.
5. Välj antal aktier.
6. **KÖP** använder Ask-priset.
7. **SÄLJ** använder Bid-priset.
8. **2 % courtage** dras automatiskt.
9. Alla portföljer har separata pengar, innehav och transaktioner.
10. Stop-loss och take-profit sparas per innehav.
11. Allt sparas i `portfolios.json`.

**Obs:** "riktiga börskurser" betyder här marknadsdata från Yahoo Finance. Beroende på marknad kan kurserna vara fördröjda. Simulatorn skickar aldrig riktiga order till börsen.
