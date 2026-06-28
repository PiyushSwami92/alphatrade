from alphatrade.config import Settings
from alphatrade.data.csv_loader import CSVLoader
from alphatrade.features.indicators import Indicators


def main():

    settings = Settings()

    symbol = settings.get("market.symbol")
    timeframe = settings.get("market.timeframe")

    loader = CSVLoader(f"data/{symbol}_{timeframe}.csv")

    df = loader.load()

    df["EMA20"] = Indicators.ema(df, 20)

    print(df[["timestamp", "close", "EMA20"]])


if __name__ == "__main__":
    main()