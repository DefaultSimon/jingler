import pathlib
import os
from typing import Any, List

from toml import load

DATA_DIR = pathlib.Path(os.path.dirname(__file__), "..", "data")
CONFIGURATION_FILENAME = pathlib.Path("configuration.toml")

CONFIGURATION_FILE = DATA_DIR / CONFIGURATION_FILENAME


class TOMLConfig:
    """
    General-purpose TOML config class.
    """
    __slots__ = ("data", )

    def __init__(self, json_data: dict):
        self.data = json_data

    @classmethod
    def from_filename(cls, file_path: str):
        with open(file_path, "r", encoding="utf-8") as config_file:
            data = load(config_file)

        return cls(data)

    def get_table(self, name: str, ignore_empty: bool = False) -> "TOMLConfig":
        data = self.data.get(name)

        if data is None and not ignore_empty:
            raise ValueError(f"Configuration table missing: '{name}'")

        return TOMLConfig(data)

    def get(self, name: str, fallback: Any = None, ignore_empty: bool = False) -> Any:
        data = self.data.get(name)

        if data is None and not ignore_empty:
            raise ValueError(f"Configuration value missing: '{name}'")

        if data is None:
            return fallback
        else:
            return data


class DiscordJingleConfig:
    __slots__ = (
        "BOT_TOKEN", "ENABLED_SERVERS", "PREFIX",
    )

    def __init__(self, toml_config: TOMLConfig):
        _auth_table = toml_config.get_table("Auth")
        self.BOT_TOKEN: str = _auth_table.get("token")

        _jingle_table = toml_config.get_table("Jingles")
        self.ENABLED_SERVERS: List[int] = _jingle_table.get("enabled_servers")

        _misc_table = toml_config.get_table("Misc")
        self.PREFIX: str = _misc_table.get("prefix")


    @classmethod
    def load_main_configuration(cls) -> "DiscordJingleConfig":
        return DiscordJingleConfig(
            TOMLConfig.from_filename(str(CONFIGURATION_FILE))
        )


config = DiscordJingleConfig.load_main_configuration()
