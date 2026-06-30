#!/usr/bin/env python3
"""Generate sample OHLCV CSV data for testing."""

import random
from datetime import datetime, timedelta

import pandas as pd


def generate_data(rows=1000):
    current_time = datetime(2024, 1, 1, 9, 0)

    price = 1.1000

    candles = []

    for _ in range(rows):

        change = random.uniform(-0.0015, 0.0015)

        open_price = price

        close_price = price + change

        high = max(open_price, close_price) + random.uniform(0, 0.0005)
        low = min(open_price, close_price) - random.uniform(0, 0.0005)

        volume = random.randint(1000, 5000)

        candles.append(
            [
                current_time,
                round(open_price, 5),
                round(high, 5),
                round(low, 5),
                round(close_price, 5),
                volume,
            ]
        )

        price = close_price
        current_time += timedelta(minutes=15)

    df = pd.DataFrame(
        candles,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
    )

    df.to_csv("data/EURUSD_M15.csv", index=False)

    print("Generated", len(df), "candles.")
    print("Saved to data/EURUSD_M15.csv")


if __name__ == "__main__":
    generate_data()