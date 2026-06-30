import pandas as pd


class Indicators:
    """Collection of technical indicators."""

    @staticmethod
    def sma(df: pd.DataFrame, period: int) -> pd.Series:
        return df["close"].rolling(window=period).mean()

    @staticmethod
    def ema(df: pd.DataFrame, period: int) -> pd.Series:
        return df["close"].ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df["close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss

        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:

        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            "MACD": macd_line,
            "Signal": signal_line,
            "Histogram": histogram,
        })

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:

        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()

        true_range = pd.concat(
            [high_low, high_close, low_close],
            axis=1
        ).max(axis=1)

        return true_range.rolling(window=period).mean()

    @staticmethod
    def bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: int = 2,
    ) -> pd.DataFrame:

        sma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return pd.DataFrame({
            "BB_Middle": sma,
            "BB_Upper": upper,
            "BB_Lower": lower,
        })