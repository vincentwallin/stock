```python
import streamlit as st
import pandas as pd
from datetime import datetime
import time

from database import (
    load_data,
    save_data,
    create_portfolio,
    delete_portfolio,
    reset_portfolio,
    get_active_portfolio,
    update_portfolio,
)

from market_data import (
    search_stocks,
    get_current_price,
    get_bid_ask,
    get_stock_data,
    get_market_indices,
)

from trading import (
    buy_stock,
    sell_stock,
    calculate_position_pnl,
    calculate_portfolio_value,
    check_stop_take_profit,
    calculate_statistics,
)

from charts import (
    candlestick_chart,
    volume_chart,
    portfolio_value_chart,
    allocation_chart,
    pnl_chart,
)


# ============================================================
# KONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Stock Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #0b0f14;
    }

    [data-testid="stSidebar"] {
        background: #0d1219;
        border-right: 1px solid #222a35;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.5px;
    }

    .metric-card {
        background: #111820;
        border: 1px solid #222a35;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 10px;
    }

    .metric-title {
        color: #8b96a5;
        font-size: 13px;
        margin-bottom: 5px;
    }

    .metric-value {
        color: #f5f7fa;
        font-size: 25px;
        font-weight: 700;
    }

    .small-muted {
        color: #7f8a99;
        font-size: 13px;
    }

    div[data-testid="stMetric"] {
        background: #111820;
        border: 1px solid #222a35;
        padding: 15px;
        border-radius: 12px;
    }

    button[kind="primary"] {
        border-radius: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HJÄLPFUNKTIONER
# ============================================================

def money(value):
    if value is None:
        return "0,00 kr"

    return f"{value:,.2f} kr".replace(",", "X").replace(".", ",").replace("X", " ")


def percent(value):
    return f"{value:+.2f}%"


def get_prices_for_portfolio(portfolio):
    symbols = list(portfolio.get("holdings", {}).keys())

    prices = {}

    for symbol in symbols:
        price = get_current_price(symbol)

        if price is not None:
            prices[symbol] = price

    return prices


def update_value_history(portfolio):
    prices = get_prices_for_portfolio(portfolio)

    value = calculate_portfolio_value(
        portfolio,
        prices
    )

    history = portfolio.setdefault("value_history", [])

    now = datetime.now().isoformat()

    if history:
        last = history[-1]

        try:
            last_time = datetime.fromisoformat(last["timestamp"])

            if (datetime.now() - last_time).total_seconds() < 10:
                last["value"] = value
            else:
                history.append(
                    {
                        "timestamp": now,
                        "value": value
                    }
                )

        except Exception:
            history.append(
                {
                    "timestamp": now,
                    "value": value
                }
            )

    else:
        history.append(
            {
                "timestamp": now,
                "value": value
            }
        )


def format_transaction_table(transactions):
    if not transactions:
        return pd.DataFrame()

    rows = []

    for transaction in reversed(transactions):
        timestamp = transaction.get("timestamp", "")

        try:
            timestamp = datetime.fromisoformat(
                timestamp
            ).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        rows.append(
            {
                "Tid": timestamp,
                "Aktie": transaction.get("symbol", ""),
                "Typ": transaction.get("side", ""),
                "Antal": transaction.get("shares", 0),
                "Pris": money(transaction.get("price", 0)),
                "Courtage": money(transaction.get("commission", 0)),
                "Totalt": money(transaction.get("total", 0)),
                "P&L": (
                    money(transaction.get("pnl", 0))
                    if transaction.get("side") == "SELL"
                    else "-"
                ),
            }
        )

    return pd.DataFrame(rows)


def show_message(success, message):
    if success:
        st.success(message)
    else:
        st.error(message)


# ============================================================
# DATA
# ============================================================

if "app_data" not in st.session_state:
    st.session_state.app_data = load_data()

data = st.session_state.app_data

if not data.get("portfolios"):
    create_portfolio(
        data,
        "Min portfölj",
        100000
    )

portfolio_names = list(data["portfolios"].keys())

if data.get("active_portfolio") not in portfolio_names:
    data["active_portfolio"] = portfolio_names[0]

active_name = data["active_portfolio"]
portfolio = get_active_portfolio(data)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("Stock Trader")

    st.caption("Trading simulator")

    st.divider()

    st.subheader("Portfölj")

    selected_portfolio = st.selectbox(
        "Välj portfölj",
        portfolio_names,
        index=portfolio_names.index(active_name),
        label_visibility="collapsed",
    )

    if selected_portfolio != active_name:
        data["active_portfolio"] = selected_portfolio
        save_data(data)
        st.session_state.app_data = data
        st.rerun()

    st.divider()

    with st.expander("Ny portfölj"):

        new_name = st.text_input(
            "Namn"
        )

        new_capital = st.number_input(
            "Startkapital",
            min_value=1.0,
            value=100000.0,
            step=1000.0,
        )

        if st.button(
            "Skapa portfölj",
            use_container_width=True
        ):

            try:
                create_portfolio(
                    data,
                    new_name,
                    new_capital
                )

                st.session_state.app_data = data

                st.success("Portföljen skapades.")
                time.sleep(0.5)
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    with st.expander("Portföljinställningar"):

        st.write(
            f"**Startkapital:** {money(portfolio['starting_capital'])}"
        )

        if st.button(
            "Återställ portfölj",
            use_container_width=True
        ):

            reset_portfolio(
                data,
                portfolio["name"]
            )

            st.session_state.app_data = data
            st.rerun()

        if len(data["portfolios"]) > 1:

            if st.button(
                "Ta bort portfölj",
                use_container_width=True
            ):

                try:
                    delete_portfolio(
                        data,
                        portfolio["name"]
                    )

                    st.session_state.app_data = data
                    st.rerun()

                except ValueError as error:
                    st.error(str(error))

    st.divider()

    st.caption("Ingen riktig order skickas.")
    st.caption("Alla pengar och trades är simulerade.")


# ============================================================
# MARKNADSTICKER
# ============================================================

indices = get_market_indices()

if indices:

    cols = st.columns(len(indices))

    for column, index_data in zip(cols, indices):

        with column:

            change = index_data["change_percent"]

            st.metric(
                index_data["name"],
                f"{index_data['price']:,.2f}",
                f"{change:+.2f}%"
            )


# ============================================================
# HEADER
# ============================================================

st.title("Stock Trader")

st.write(
    f"Portfölj: **{portfolio['name']}**"
)

st.divider()


# ============================================================
# PORTFÖLJVÄRDE
# ============================================================

prices = get_prices_for_portfolio(portfolio)

portfolio_value = calculate_portfolio_value(
    portfolio,
    prices
)

starting_capital = portfolio["starting_capital"]

total_pnl = portfolio_value - starting_capital

if starting_capital:
    total_return = (
        total_pnl / starting_capital
    ) * 100
else:
    total_return = 0


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Portföljvärde",
        money(portfolio_value)
    )

with col2:
    st.metric(
        "Kontanter",
        money(portfolio["cash"])
    )

with col3:
    st.metric(
        "P&L",
        money(total_pnl),
        percent(total_return)
    )

with col4:
    st.metric(
        "Antal positioner",
        len(portfolio["holdings"])
    )


# ============================================================
# UPPDATERA HISTORIK
# ============================================================

update_value_history(portfolio)
update_portfolio(data, portfolio)

st.session_state.app_data = data


# ============================================================
# FLikar
# ============================================================

tab_trade, tab_chart, tab_portfolio, tab_stats, tab_history, tab_watchlist = st.tabs(
    [
        "Trade",
        "Chart",
        "Portfolio",
        "Statistics",
        "History",
        "Watchlist",
    ]
)


# ============================================================
# TRADE
# ============================================================

with tab_trade:

    st.subheader("Trade")

    search_query = st.text_input(
        "Sök aktie",
        placeholder="Exempel: Apple, Tesla, Volvo, Nvidia..."
    )

    search_results = []

    if search_query:

        search_results = search_stocks(
            search_query
        )

    if search_results:

        options = [
            f"{result['symbol']} — {result['name']}"
            for result in search_results
        ]

        selected_result = st.selectbox(
            "Välj aktie",
            options
        )

        selected_index = options.index(
            selected_result
        )

        selected_stock = search_results[
            selected_index
        ]

        symbol = selected_stock["symbol"]

    else:

        held_symbols = list(
            portfolio["holdings"].keys()
        )

        if held_symbols:

            symbol = st.selectbox(
                "Aktie",
                held_symbols
            )

        else:

            symbol = st.text_input(
                "Aktiesymbol",
                placeholder="Exempel: AAPL"
            ).upper().strip()

    if symbol:

        current_price = get_current_price(
            symbol
        )

        bid, ask, spread = get_bid_ask(
            symbol
        )

        if current_price is None:

            st.warning(
                "Kunde inte hämta priset för denna aktie."
            )

        else:

            price_col1, price_col2, price_col3 = st.columns(3)

            with price_col1:
                st.metric(
                    "Senaste pris",
                    money(current_price)
                )

            with price_col2:

                if bid is not None:
                    st.metric(
                        "Bid",
                        money(bid)
                    )

            with price_col3:

                if ask is not None:
                    st.metric(
                        "Ask",
                        money(ask)
                    )

            st.divider()

            trade_col1, trade_col2 = st.columns(2)

            with trade_col1:

                st.subheader("Köp")

                buy_shares = st.number_input(
                    "Antal aktier",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"buy_{symbol}"
                )

                buy_stop = st.number_input(
                    "Stop-loss",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    key=f"buy_stop_{symbol}"
                )

                buy_target = st.number_input(
                    "Take-profit",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    key=f"buy_target_{symbol}"
                )

                if ask is not None:

                    estimated_value = (
                        ask * buy_shares
                    )

                    estimated_commission = (
                        estimated_value * 0.02
                    )

                    estimated_total = (
                        estimated_value
                        + estimated_commission
                    )

                    st.caption(
                        f"Pris: {money(estimated_value)}"
                    )

                    st.caption(
                        f"Courtage 2%: {money(estimated_commission)}"
                    )

                    st.caption(
                        f"Totalt: {money(estimated_total)}"
                    )

                if st.button(
                    "Köp",
                    type="primary",
                    use_container_width=True,
                    key=f"buy_button_{symbol}"
                ):

                    success, message = buy_stock(
                        portfolio,
                        symbol,
                        buy_shares,
                        current_price,
                        stop_loss=(
                            buy_stop
                            if buy_stop > 0
                            else None
                        ),
                        take_profit=(
                            buy_target
                            if buy_target > 0
                            else None
                        )
                    )

                    show_message(
                        success,
                        message
                    )

                    if success:

                        update_portfolio(
                            data,
                            portfolio
                        )

                        st.session_state.app_data = data

                        time.sleep(0.3)
                        st.rerun()

            with trade_col2:

                st.subheader("Sälj")

                owned = portfolio["holdings"].get(
                    symbol
                )

                if owned:

                    owned_shares = owned["shares"]

                    st.write(
                        f"Du äger **{owned_shares}** aktier."
                    )

                    st.write(
                        f"Snittpris: "
                        f"**{money(owned['average_price'])}**"
                    )

                    sell_shares = st.number_input(
                        "Antal att sälja",
                        min_value=1,
                        max_value=int(owned_shares),
                        value=1,
                        step=1,
                        key=f"sell_{symbol}"
                    )

                    if bid is not None:

                        estimated_value = (
                            bid * sell_shares
                        )

                        estimated_commission = (
                            estimated_value * 0.02
                        )

                        estimated_total = (
                            estimated_value
                            - estimated_commission
                        )

                        st.caption(
                            f"Försäljningsvärde: "
                            f"{money(estimated_value)}"
                        )

                        st.caption(
                            f"Courtage 2%: "
                            f"{money(estimated_commission)}"
                        )

                        st.caption(
                            f"Du får: "
                            f"{money(estimated_total)}"
                        )

                    if st.button(
                        "Sälj",
                        use_container_width=True,
                        key=f"sell_button_{symbol}"
                    ):

                        success, message = sell_stock(
                            portfolio,
                            symbol,
                            sell_shares,
                            current_price
                        )

                        show_message(
                            success,
                            message
                        )

                        if success:

                            update_portfolio(
                                data,
                                portfolio
                            )

                            st.session_state.app_data = data

                            time.sleep(0.3)
                            st.rerun()

                else:

                    st.info(
                        "Du äger inte den här aktien."
                    )


# ============================================================
# CHART
# ============================================================

with tab_chart:

    st.subheader("Marknad")

    chart_symbol = st.text_input(
        "Aktiesymbol",
        value=(
            symbol
            if "symbol" in locals()
            and symbol
            else "AAPL"
        )
    ).upper().strip()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        interval = st.selectbox(
            "Intervall",
            [
                "1m",
                "5m",
                "1h",
                "1d",
            ]
        )

    with chart_col2:

        period = st.selectbox(
            "Period",
            [
                "1d",
                "5d",
                "1mo",
                "3mo",
                "6mo",
                "1y",
            ]
        )

    interval_periods = {
        "1m": ["1d", "5d"],
        "5m": ["1d", "5d", "1mo"],
        "1h": ["5d", "1mo", "3mo", "6mo"],
        "1d": ["1mo", "3mo", "6mo", "1y"],
    }

    allowed_periods = interval_periods[
        interval
    ]

    if period not in allowed_periods:
        period = allowed_periods[0]

    data_chart = get_stock_data(
        chart_symbol,
        period=period,
        interval=interval
    )

    if data_chart.empty:

        st.warning(
            "Ingen kursdata kunde hämtas."
        )

    else:

        candle = candlestick_chart(
            data_chart,
            chart_symbol
        )

        if candle:
            st.plotly_chart(
                candle,
                use_container_width=True
            )

        volume = volume_chart(
            data_chart
        )

        if volume:
            st.plotly_chart(
                volume,
                use_container_width=True
            )


# ============================================================
# PORTFOLIO
# ============================================================

with tab_portfolio:

    st.subheader("Portfolio")

    prices = get_prices_for_portfolio(
        portfolio
    )

    if not portfolio["holdings"]:

        st.info(
            "Din portfölj är tom."
        )

    else:

        rows = []

        for stock_symbol, holding in portfolio[
            "holdings"
        ].items():

            current = prices.get(
                stock_symbol
            )

            if current is None:
                continue

            position = calculate_position_pnl(
                holding,
                current
            )

            rows.append(
                {
                    "Aktie": stock_symbol,
                    "Antal": holding["shares"],
                    "Snittpris": money(
                        holding["average_price"]
                    ),
                    "Pris": money(current),
                    "Värde": money(
                        position["current_value"]
                    ),
                    "P&L": money(
                        position["pnl"]
                    ),
                    "P&L %": percent(
                        position["pnl_percent"]
                    ),
                    "Stop-loss": (
                        money(holding["stop_loss"])
                        if holding.get("stop_loss")
                        else "-"
                    ),
                    "Take-profit": (
                        money(holding["take_profit"])
                        if holding.get("take_profit")
                        else "-"
                    ),
                }
            )

        if rows:

            portfolio_df = pd.DataFrame(
                rows
            )

            st.dataframe(
                portfolio_df,
                use_container_width=True,
                hide_index=True
            )

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        allocation = allocation_chart(
            portfolio,
            prices
        )

        if allocation:
            st.plotly_chart(
                allocation,
                use_container_width=True
            )

    with chart_col2:

        performance = portfolio_value_chart(
            portfolio.get(
                "value_history",
                []
            )
        )

        if performance:
            st.plotly_chart(
                performance,
                use_container_width=True
            )


# ============================================================
# STATISTICS
# ============================================================

with tab_stats:

    st.subheader("Trading Statistics")

    stats = calculate_statistics(
        portfolio
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Trades",
            stats["total_trades"]
        )

    with col2:
        st.metric(
            "Win rate",
            f"{stats['win_rate']:.2f}%"
        )

    with col3:
        st.metric(
            "Realiserad P&L",
            money(
                stats["total_realized_pnl"]
            )
        )

    col4, col5 = st.columns(2)

    with col4:
        st.metric(
            "Största vinst",
            money(
                stats["biggest_win"]
            )
        )

    with col5:
        st.metric(
            "Största förlust",
            money(
                stats["biggest_loss"]
            )
        )

    pnl = pnl_chart(
        portfolio.get(
            "transactions",
            []
        )
    )

    if pnl:
        st.plotly_chart(
            pnl,
            use_container_width=True
        )

    st.info(
        "Win rate räknas från avslutade säljtrades."
    )


# ============================================================
# HISTORY
# ============================================================

with tab_history:

    st.subheader("Transaction History")

    transaction_df = format_transaction_table(
        portfolio.get(
            "transactions",
            []
        )
    )

    if transaction_df.empty:

        st.info(
            "Inga trades har gjorts ännu."
        )

    else:

        st.dataframe(
            transaction_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# WATCHLIST
# ============================================================

with tab_watchlist:

    st.subheader("Watchlist")

    if "watchlist" not in st.session_state:

        st.session_state.watchlist = [
            "AAPL",
            "NVDA",
            "TSLA",
            "MSFT",
            "VOLV-B.ST",
        ]

    watch_input = st.text_input(
        "Lägg till aktie",
        placeholder="Exempel: AMD"
    ).upper().strip()

    if st.button(
        "Lägg till"
    ):

        if (
            watch_input
            and watch_input
            not in st.session_state.watchlist
        ):

            st.session_state.watchlist.append(
                watch_input
            )

            st.rerun()

    st.divider()

    watch_rows = []

    for watch_symbol in st.session_state.watchlist:

        price = get_current_price(
            watch_symbol
        )

        if price is None:
            continue

        history = get_stock_data(
            watch_symbol,
            period="2d",
            interval="1d"
        )

        change_percent = 0

        if len(history) >= 2:

            previous = float(
                history["Close"].iloc[-2]
            )

            change_percent = (
                (price - previous)
                / previous
                * 100
            )

        watch_rows.append(
            {
                "Symbol": watch_symbol,
                "Pris": money(price),
                "Förändring": percent(
                    change_percent
                ),
            }
        )

    if watch_rows:

        watch_df = pd.DataFrame(
            watch_rows
        )

        st.dataframe(
            watch_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Ingen watchlist-data kunde hämtas."
        )


# ============================================================
# STOP-LOSS / TAKE-PROFIT
# ============================================================

prices = get_prices_for_portfolio(
    portfolio
)

triggered_orders = check_stop_take_profit(
    portfolio,
    prices
)

if triggered_orders:

    for order in triggered_orders:

        st.warning(
            f"{order['reason']}: "
            f"{order['symbol']} såldes automatiskt."
        )

    update_portfolio(
        data,
        portfolio
    )

    st.session_state.app_data = data
```
