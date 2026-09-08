```python
import json
import os
from datetime import datetime

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "portfolios.json")


def ensure_data_folder():
    os.makedirs(DATA_DIR, exist_ok=True)


def default_portfolio(name="Min portfölj", starting_capital=100000):
    return {
        "name": name,
        "starting_capital": float(starting_capital),
        "cash": float(starting_capital),
        "holdings": {},
        "transactions": [],
        "value_history": [
            {
                "timestamp": datetime.now().isoformat(),
                "value": float(starting_capital)
            }
        ],
        "created_at": datetime.now().isoformat()
    }


def load_data():
    ensure_data_folder()

    if not os.path.exists(DATA_FILE):
        data = {
            "active_portfolio": "Min portfölj",
            "portfolios": {
                "Min portfölj": default_portfolio()
            }
        }
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "portfolios" not in data:
            data["portfolios"] = {}

        if not data["portfolios"]:
            data["portfolios"]["Min portfölj"] = default_portfolio()

        if "active_portfolio" not in data:
            data["active_portfolio"] = list(data["portfolios"].keys())[0]

        return data

    except (json.JSONDecodeError, OSError):
        data = {
            "active_portfolio": "Min portfölj",
            "portfolios": {
                "Min portfölj": default_portfolio()
            }
        }
        save_data(data)
        return data


def save_data(data):
    ensure_data_folder()

    temporary_file = DATA_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    os.replace(temporary_file, DATA_FILE)


def create_portfolio(data, name, starting_capital):
    name = name.strip()

    if not name:
        raise ValueError("Portföljens namn får inte vara tomt.")

    if name in data["portfolios"]:
        raise ValueError("Det finns redan en portfölj med det namnet.")

    if starting_capital <= 0:
        raise ValueError("Startkapitalet måste vara större än 0.")

    data["portfolios"][name] = default_portfolio(
        name=name,
        starting_capital=starting_capital
    )

    data["active_portfolio"] = name

    save_data(data)

    return data


def delete_portfolio(data, name):
    if name not in data["portfolios"]:
        return data

    if len(data["portfolios"]) <= 1:
        raise ValueError("Du måste ha minst en portfölj.")

    del data["portfolios"][name]

    if data["active_portfolio"] == name:
        data["active_portfolio"] = list(data["portfolios"].keys())[0]

    save_data(data)

    return data


def reset_portfolio(data, name):
    if name not in data["portfolios"]:
        raise ValueError("Portföljen finns inte.")

    portfolio = data["portfolios"][name]

    data["portfolios"][name] = default_portfolio(
        name=name,
        starting_capital=portfolio["starting_capital"]
    )

    data["active_portfolio"] = name

    save_data(data)

    return data


def get_active_portfolio(data):
    name = data["active_portfolio"]
    return data["portfolios"][name]


def update_portfolio(data, portfolio):
    name = portfolio["name"]

    data["portfolios"][name] = portfolio

    save_data(data)

    return data
```
