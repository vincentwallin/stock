```python
from datetime import datetime


COMMISSION_RATE = 0.02
MIN_SHARES = 1


def calculate_commission(value):
    return value * COMMISSION_RATE


def calculate_buy_price(market_price, spread_percent=0.0005):
    return market_price * (1 + spread_percent)


def calculate_sell_price(market_price, spread_percent=0.0005):
    return market_price * (1 - spread_percent)


def buy_stock(
    portfolio,
    symbol,
    shares,
    market_price,
    stop_loss=None,
    take_profit=None
):
    if shares < MIN_SHARES:
        return False, "Du måste köpa minst 1 hel aktie."

    if int(shares) != shares:
        return False, "Du kan bara köpa hela aktier."

    shares = int(shares)

    execution_price = calculate_buy_price(market_price)

    gross_value = execution_price * shares
    commission = calculate_commission(gross_value)
    total_cost = gross_value + commission

    if total_cost > portfolio["cash"]:
        return False, "Du har inte tillräckligt med pengar."

    portfolio["cash"] -= total_cost

    if symbol not in portfolio["holdings"]:
        portfolio["holdings"][symbol] = {
            "shares": 0,
            "average_price": 0,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "total_invested": 0
        }

    holding = portfolio["holdings"][symbol]

    old_shares = holding["shares"]
    old_invested = holding["total_invested"]

    new_shares = old_shares + shares
    new_invested = old_invested + total_cost

    holding["shares"] = new_shares
    holding["total_invested"] = new_invested
    holding["average_price"] = new_invested / new_shares

    if stop_loss is not None:
        holding["stop_loss"] = float(stop_loss)

    if take_profit is not None:
        holding["take_profit"] = float(take_profit)

    transaction = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "side": "BUY",
        "shares": shares,
        "price": execution_price,
        "commission": commission,
        "total": total_cost
    }

    portfolio["transactions"].append(transaction)

    return True, f"Köpte {shares} aktier i {symbol}."


def sell_stock(portfolio, symbol, shares, market_price):
    if symbol not in portfolio["holdings"]:
        return False, "Du äger inte den här aktien."

    holding = portfolio["holdings"][symbol]

    if shares < MIN_SHARES:
        return False, "Du måste sälja minst 1 hel aktie."

    if int(shares) != shares:
        return False, "Du kan bara sälja hela aktier."

    shares = int(shares)

    if shares > holding["shares"]:
        return False, "Du äger inte så många aktier."

    execution_price = calculate_sell_price(market_price)

    gross_value = execution_price * shares
    commission = calculate_commission(gross_value)
    net_value = gross_value - commission

    average_price = holding["average_price"]

    estimated_cost = average_price * shares
    pnl = net_value - estimated_cost

    portfolio["cash"] += net_value

    holding["shares"] -= shares
    holding["total_invested"] -= estimated_cost

    if holding["shares"] <= 0:
        del portfolio["holdings"][symbol]
    else:
        holding["average_price"] = (
            holding["total_invested"] / holding["shares"]
        )

    transaction = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "side": "SELL",
        "shares": shares,
        "price": execution_price,
        "commission": commission,
        "total": net_value,
        "pnl": pnl
    }

    portfolio["transactions"].append(transaction)

    return True, f"Sålde {shares} aktier i {symbol}. P&L: {pnl:.2f} kr"


def calculate_position_pnl(holding, current_price):
    shares = holding["shares"]
    average_price = holding["average_price"]

    current_value = current_price * shares
    invested = average_price * shares

    pnl = current_value - invested

    return {
        "current_value": current_value,
        "invested": invested,
        "pnl": pnl,
        "pnl_percent": (pnl / invested * 100) if invested else 0
    }


def calculate_portfolio_value(portfolio, prices):
    value = portfolio["cash"]

    for symbol, holding in portfolio["holdings"].items():
        price = prices.get(symbol)

        if price is not None:
            value += price * holding["shares"]

    return value


def check_stop_take_profit(portfolio, prices):
    """
    Kontrollerar stop-loss och take-profit.

    Returnerar en lista med automatiska försäljningar.
    """

    triggered = []

    for symbol in list(portfolio["holdings"].keys()):
        holding = portfolio["holdings"][symbol]

        if symbol not in prices:
            continue

        price = prices[symbol]

        stop_loss = holding.get("stop_loss")
        take_profit = holding.get("take_profit")

        reason = None

        if stop_loss is not None and price <= stop_loss:
            reason = "Stop-loss"

        elif take_profit is not None and price >= take_profit:
            reason = "Take-profit"

        if reason:
            shares = holding["shares"]

            success, message = sell_stock(
                portfolio,
                symbol,
                shares,
                price
            )

            if success:
                triggered.append({
                    "symbol": symbol,
                    "reason": reason,
                    "message": message
                })

    return triggered


def calculate_statistics(portfolio):
    sells = [
        transaction
        for transaction in portfolio["transactions"]
        if transaction["side"] == "SELL"
    ]

    if not sells:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "biggest_win": 0,
            "biggest_loss": 0,
            "total_realized_pnl": 0
        }

    pnls = [
        float(transaction.get("pnl", 0))
        for transaction in sells
    ]

    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]

    return {
        "total_trades": len(pnls),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": (
            len(wins) / len(pnls) * 100
            if pnls
            else 0
        ),
        "biggest_win": max(pnls) if pnls else 0,
        "biggest_loss": min(pnls) if pnls else 0,
        "total_realized_pnl": sum(pnls)
    }
```
