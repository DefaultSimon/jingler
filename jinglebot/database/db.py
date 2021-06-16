import logging
import pathlib
from sqlite3 import Connection, connect, Cursor
from typing import Dict, Optional, Any

from jinglebot.configuration import DATA_DIR
from jinglebot.guild_settings import JingleMode
from jinglebot.utilities import get_nth_with_default, Singleton

log = logging.getLogger(__name__)

DATABASE_NAME = "jinglebot.db"
DB_INIT_FILEPATH = pathlib.Path(__file__, "..", "db_init.sql")


JINGLE_MODE_INT_TO_ENUM: Dict[int, JingleMode] = {
    0: JingleMode.DISABLED,
    1: JingleMode.SINGLE,
    2: JingleMode.RANDOM,
}
JINGLE_MODE_ENUM_TO_INT: Dict[JingleMode, int] = {
    v: k for k, v in JINGLE_MODE_INT_TO_ENUM.items()
}


class Database(metaclass=Singleton):
    """
    A SQLite3 database wrapper for guild_settings and user_settings.
    """
    def __init__(self):
        self.con: Connection = connect(str(DATA_DIR / DATABASE_NAME))
        self._ensure_tables()

    def _ensure_tables(self):
        """
        Ensure the proper tables (guild_settings and user_settings) exist.
        """
        cur: Cursor = self.con.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()

        if ("guild_settings",) not in tables or ("user_settings",) not in tables:
            with open(str(DB_INIT_FILEPATH), "r", encoding="utf8") as db_init_file:
                cur.executescript(db_init_file.read())
            self.con.commit()

            log.info("Ran db_init.sql.")
        else:
            log.info("guild_settings and user_settings already exist.")

    #####
    # Guild private
    #####
    def _ensure_guild(self, guild_id: int):
        """
        Make sure the guild entry exists.
        :param guild_id: Guild ID to ensure the existence of.
        """
        cur: Cursor = self.con.cursor()
        cur.execute(
            "SELECT id FROM guild_settings where id=?;",
            (guild_id,)
        )

        if cur.fetchone() is None:
            # Create new guild
            cur.execute(
                "INSERT INTO guild_settings (id) VALUES (?);",
                (guild_id,)
            )
            self.con.commit()

    def _get_guild_field(self, guild_id: int, field_name: str) -> Any:
        """
        Fetch a single guild field from the database.
        :param guild_id: Guild ID to get the field for.
        :param field_name: Field name.
        WARNING: This field is not sanitized inside the query!
        :return: Field value.
        """
        cur: Cursor = self.con.cursor()
        cur.execute(
            f"SELECT {field_name} FROM guild_settings WHERE id = ?",
            (guild_id, )
        )
        return get_nth_with_default(cur.fetchone(), 0)

    def _set_guild_field(self, guild_id: int, field_name: str, field_value: Any):
        """
        Set a single guild field.
        :param guild_id: Guild ID to set the field for.
        :param field_name: Field name to set the value for.
        WARNING: This field is not sanitized inside the query!
        :param field_value: Field value.
        """
        cur: Cursor = self.con.cursor()
        cur.execute(
            f"UPDATE guild_settings SET {field_name} = ? WHERE id = ?",
            (field_value, guild_id)
        )
        self.con.commit()

    #####
    # Guild settings
    #####
    def guild_get_jingle_mode(self, guild_id: int, default_mode: JingleMode = JingleMode.DISABLED) -> JingleMode:
        """
        Return the jingle mode for the current server.
        :param guild_id: Guild ID to get the setting for.
        :param default_mode: In case the jingle mode is null, return this default.
        :return: JingleMode for the guild.
        """
        self._ensure_guild(guild_id)

        guild_jingle_mode: int = self._get_guild_field(guild_id, "jingle_mode")
        if guild_jingle_mode is None:
            return default_mode
        else:
            return JINGLE_MODE_INT_TO_ENUM.get(guild_jingle_mode)

    def guild_set_jingle_mode(self, guild_id: int, jingle_mode: JingleMode):
        """
        Set the jingle mode for the current server.
        :param guild_id: Guild ID to set the jingle mode for.
        :param jingle_mode: Jingle mode to set.
        """
        self._ensure_guild(guild_id)

        jingle_mode_int = JINGLE_MODE_ENUM_TO_INT.get(jingle_mode)
        self._set_guild_field(guild_id, "jingle_mode", jingle_mode_int)

    def guild_get_default_jingle_id(self, guild_id: int) -> Optional[str]:
        """
        Return the default jingle ID for the current server.
        :param guild_id: Guild ID to get the setting for.
        :return: Jingle ID or None if unset.
        """
        self._ensure_guild(guild_id)
        return self._get_guild_field(guild_id, "default_jingle_id")

    def guild_set_default_jingle_id(self, guild_id: int, jingle_id: str):
        """
        Set the default jingle ID for the current server.
        :param guild_id: Guild ID to set the default jingle for.
        :param jingle_id: Jingle ID that will become the default.
        """
        self._ensure_guild(guild_id)
        self._set_guild_field(guild_id, "default_jingle_id", jingle_id)

    #####
    # User private
    #####
    def _ensure_user(self, user_id: int):
        """
        Make sure the user entry exists.
        :param user_id: User to ensure the existence of.
        """
        cur: Cursor = self.con.cursor()
        cur.execute(
            "SELECT id FROM user_settings where id=?;",
            (user_id, )
        )

        if cur.fetchone() is None:
            # Create new user
            cur.execute(
                "INSERT INTO user_settings (id) VALUES (?);",
                (user_id, )
            )
            self.con.commit()

    def _get_user_field(self, user_id: int, field_name: str) -> Any:
        """
        Fetch a single user field from the database.
        :param user_id: User ID to get the field for.
        :param field_name: Field name.
        WARNING: This field is not sanitized inside the query!
        :return: Field value.
        """
        cur: Cursor = self.con.cursor()
        cur.execute(
            f"SELECT {field_name} FROM user_settings WHERE id = ?",
            (user_id, )
        )
        return get_nth_with_default(cur.fetchone(), 0)

    def _set_user_field(self, user_id: int, field_name: str, field_value: Any):
        """
        Set a single user's field.
        :param user_id: User ID to set the field for.
        :param field_name: Field name.
        WARNING: This field is not sanitized inside the query!
        :param field_value: Field value.
        """
        cur: Cursor = self.con.cursor()
        cur.execute(
            f"UPDATE user_settings SET {field_name} = ? WHERE id = ?",
            (field_value, user_id)
        )
        self.con.commit()

    #####
    # User settings
    #####
    def user_get_theme_song_jingle_id(self, user_id: int) -> Optional[str]:
        """
        Get the user's theme song jingle ID, if set.
        :param user_id: User ID to get the theme song for.
        :return: Jingle ID that the user has for their theme song, or None if unset.
        """
        self._ensure_user(user_id)
        return self._get_user_field(user_id, "theme_song_jingle_id")

    def user_set_theme_song_jingle_id(self, user_id: int, jingle_id: Optional[str]):
        """
        Set the user's theme song jingle ID.
        :param user_id: User ID to set the theme song for.
        :param jingle_id: Jingle ID that will become the user's theme song.
        """
        self._ensure_user(user_id)
        self._set_user_field(user_id, "theme_song_jingle_id", jingle_id)
