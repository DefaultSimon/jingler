from enum import Enum
from typing import Dict, Optional

from discord import Guild

from jinglebot.jingles import Jingle
from jinglebot.utilities import Singleton


class JingleMode(Enum):
    DISABLED = "disabled"
    SINGLE = "single"
    RANDOM = "random"


class GuildSettings:
    def __init__(self):
        # Set up defaults
        self.jingle_mode: JingleMode = JingleMode.RANDOM
        self.jingle_default: Optional[Jingle] = None


class GuildSettingsManager(metaclass=Singleton):
    def __init__(self):
        self.settings_by_guild_id: Dict[int, GuildSettings] = {}
        # TODO add persistence

    def _ensure_guild_settings_exist(self, guild: Guild) -> GuildSettings:
        if guild.id not in self.settings_by_guild_id:
            # Create new GuildSettings
            guild_settings = GuildSettings()
            self.settings_by_guild_id[guild.id] = guild_settings
        else:
            # Fetch existing GuildSettings
            guild_settings = self.settings_by_guild_id[guild.id]

        return guild_settings


    def get_guild_jingle_mode(self, guild: Guild) -> JingleMode:
        """
        Get the jingle mode setting for some guild.
        :param guild: Guild to get the setting for.
        :return: JingleMode setting.
        """
        guild_settings = self._ensure_guild_settings_exist(guild)
        return guild_settings.jingle_mode

    def update_guild_jingle_mode(self, guild: Guild, jingle_mode: JingleMode):
        """
        Update the jingle_mode setting for a single guild.
        :param guild: Guild to update the setting for.
        :param jingle_mode: Jingle mode to set.
        """
        guild_settings = self._ensure_guild_settings_exist(guild)
        guild_settings.jingle_mode = jingle_mode

    def get_guild_default_jingle(self, guild: Guild) -> Jingle:
        """
        Get the default jingle for a some guild.
        :param guild: Guild to get the setting for.
        :return: Default Jingle.
        """
        guild_settings = self._ensure_guild_settings_exist(guild)
        return guild_settings.jingle_default

    def update_guild_single_jingle(self, guild: Guild, jingle: Jingle):
        """
        Update the single main jingle setting for a single guild.
        :param guild: Guild to update the setting for.
        :param jingle: Jingle to set as the default.
        """
        guild_settings = self._ensure_guild_settings_exist(guild)
        guild_settings.jingle_default = jingle
