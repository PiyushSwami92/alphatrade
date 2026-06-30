from alphatrade.config import Settings
from alphatrade.data.csv_loader import CSVLoader
from alphatrade.features.indicators import Indicators
from alphatrade.strategies.multi_confirmation import MultiConfirmationStrategy


def main():
    # Load configuration
    settings = Settings()

    symbol = settings.get("market.symbol")
    timeframe = settings.get("market.timeframe")

    csv_path = f"data/{symbol}_{timeframe}.csv"

    # Load historical data
    loader = CSVLoader(csv_path)
    df = loader.load()

    # ===============================
    # Calculate Indicators
    # ===============================

    df["SMA5"] = Indicators.sma(df, 5)
    df["EMA5"] = Indicators.ema(df, 5)
    df["RSI14"] = Indicators.rsi(df)

    macd = Indicators.macd(df)
    df["MACD"] = macd["MACD"]
    df["Signal"] = macd["Signal"]
    df["Histogram"] = macd["Histogram"]

    df["ATR14"] = Indicators.atr(df)

    bb = Indicators.bollinger_bands(df)
    df["BB_Middle"] = bb["BB_Middle"]
    df["BB_Upper"] = bb["BB_Upper"]
    df["BB_Lower"] = bb["BB_Lower"]

    # ===============================
    # Display Last 20 Candles
    # ===============================

    print("=" * 80)
    print("AlphaTrade Indicator Engine")
    print("=" * 80)

    print(
        df[
            [
                "timestamp",
                "close",
                "EMA5",
                "RSI14",
                "MACD",
                "Signal",
                "ATR14",
                "BB_Upper",
                "BB_Middle",
                "BB_Lower",
            ]
        ].tail(20)
    )

    # ===============================
    # Generate Trading Signal
    # ===============================

    strategy = MultiConfirmationStrategy()

    signal = strategy.generate_signal(df)

    print("\n" + "=" * 80)
    print("Trading Signal")
    print("=" * 80)
    print(f"Signal : {signal}")


if __name__ == "__main__":
    main()