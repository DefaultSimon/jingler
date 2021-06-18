import pathlib
from typing import Any, List

from toml import load

BASE_DIR = pathlib.Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"

CONFIGURATION_FILENAME = pathlib.Path("configuration.toml")
PYPROJECT_FILENAME = pathlib.Path("pyproject.toml")

CONFIGURATION_FILE = DATA_DIR / CONFIGURATION_FILENAME
PYPROJECT_FILE = BASE_DIR / PYPROJECT_FILENAME


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
        "BOT_TOKEN",
        "PREFIX",
        "USE_SERVER_WHITELIST", "SERVER_WHITELIST",
        "MAX_JINGLE_FILESIZE_MB", "MAX_JINGLE_LENGTH_SECONDS", "MAX_JINGLE_TITLE_LENGTH"
    )

    def __init__(self, toml_config: TOMLConfig):
        _auth_table = toml_config.get_table("Auth")
        self.BOT_TOKEN: str = str(_auth_table.get("token", ""))

        _general_table = toml_config.get_table("General")
        self.PREFIX: str = str(_general_table.get("prefix", "."))

        _server_table = toml_config.get_table("Server")
        self.USE_SERVER_WHITELIST: bool = bool(_server_table.get("use_server_whitelist", False))
        self.SERVER_WHITELIST: List[int] = list(_server_table.get("server_whitelist", []))

        _jingles_table = toml_config.get_table("Jingles")
        self.MAX_JINGLE_FILESIZE_MB: float = round(int(_jingles_table.get("max_jingle_filesize_kb", 1024)) / 1024, 2)
        self.MAX_JINGLE_LENGTH_SECONDS: float = float(_jingles_table.get("max_jingle_length_seconds", 10))
        self.MAX_JINGLE_TITLE_LENGTH: int = int(_jingles_table.get("max_jingle_title_length", 65))

    @classmethod
    def load_main_configuration(cls) -> "DiscordJingleConfig":
        return DiscordJingleConfig(
            TOMLConfig.from_filename(str(CONFIGURATION_FILE))
        )


class JinglerPyproject:
    __slots__ = ("VERSION", )

    def __init__(self, toml_config: TOMLConfig):
        _tool_poetry_table = toml_config.get_table("tool").get_table("poetry")
        self.VERSION = _tool_poetry_table.get("version")

    @classmethod
    def load_pyproject(cls) -> "JinglerPyproject":
        return JinglerPyproject(
            TOMLConfig.from_filename(str(PYPROJECT_FILE))
        )


config = DiscordJingleConfig.load_main_configuration()
pyproject = JinglerPyproject.load_pyproject()
