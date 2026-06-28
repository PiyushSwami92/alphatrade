from pathlib import Path
import pandas as pd


class CSVLoader:
    """Load OHLCV data from a CSV file."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self):
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {self.file_path}"
            )

        df = pd.read_csv(self.file_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df