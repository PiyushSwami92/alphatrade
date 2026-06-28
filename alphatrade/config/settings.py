import yaml
from pathlib import Path


class Settings:

    def __init__(self):
        config_path = Path(__file__).parent / "settings.yaml"

        with open(config_path, "r") as file:
            self.data = yaml.safe_load(file)

    def get(self, key, default=None):
        keys = key.split(".")

        value = self.data

        for k in keys:

            if isinstance(value, dict):

                value = value.get(k)

            else:

                return default

        return value