import pandas as pd


class Indicators:

    @staticmethod
    def ema(df: pd.DataFrame, period: int):

        return df["close"].ewm(
            span=period,
            adjust=False
        ).mean()

    @staticmethod
    def sma(df: pd.DataFrame, period: int):

        return df["close"].rolling(
            window=period
        ).mean()