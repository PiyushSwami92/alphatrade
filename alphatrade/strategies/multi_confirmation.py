import pandas as pd


class MultiConfirmationStrategy:
    """
    Multi-confirmation trading strategy.
    """

    def generate_signal(self, df: pd.DataFrame) -> str:

        latest = df.iloc[-1]

        buy_conditions = [

            latest["EMA5"] > latest["BB_Middle"],

            latest["RSI14"] > 55,

            latest["MACD"] > latest["Signal"],

            latest["close"] > latest["BB_Middle"]

        ]

        sell_conditions = [

            latest["EMA5"] < latest["BB_Middle"],

            latest["RSI14"] < 45,

            latest["MACD"] < latest["Signal"],

            latest["close"] < latest["BB_Middle"]

        ]

        if all(buy_conditions):
            return "BUY"

        if all(sell_conditions):
            return "SELL"

        return "HOLD"