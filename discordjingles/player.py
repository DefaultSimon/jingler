import asyncio
import logging
from random import choice
from typing import Optional

from discord import VoiceChannel, VoiceClient, ClientException, FFmpegOpusAudio, Guild

from discordjingles.guild_settings import JingleMode
from discordjingles.jingles import Jingle, JingleManager
from discordjingles.guild_settings import GuildSettingsManager

log = logging.getLogger(__name__)

jingle_manager = JingleManager()
guild_manager = GuildSettingsManager()


async def get_proper_jingle(guild: Guild, override_mode: Optional[JingleMode] = None) -> Optional[Jingle]:
    """
    Return the guild jingle depending on current mode.

    :param guild: Guild to choose a jingle for.
    :param override_mode: If specified, overrides the guild jingle mode.
    :return:
        If set to `disabled`, return None.
        If set to `single`, return the default jingle.
        If set to `random`, return a random jingle.
    """
    guild_jingle_mode = guild_manager.get_guild_jingle_mode(guild)
    guild_jingle_default = guild_manager.get_guild_default_jingle(guild)

    if guild_jingle_mode == JingleMode.SINGLE or override_mode == JingleMode.SINGLE:
        return guild_jingle_default
    elif guild_jingle_mode == JingleMode.RANDOM or override_mode == JingleMode.RANDOM:
        return choice(list(jingle_manager.jingles_by_id.values()))
    elif guild_jingle_mode == JingleMode.DISABLED or override_mode == JingleMode.DISABLED:
        return None
    else:
        raise ValueError(f"Invalid jingle mode: {guild_jingle_mode}!")


async def play_jingle(channel: VoiceChannel, jingle: Jingle, fail_silently: bool = True) -> bool:
    try:
        # noinspection PyTypeChecker
        connection: VoiceClient = await channel.connect()
    except ClientException as e:
        log.warning(f"Error while trying to connect: {e}")

        if fail_silently:
            return False
        else:
            raise

    try:
        audio = FFmpegOpusAudio(source=str(jingle.path.absolute()))

        # Delay playback very slightly
        await asyncio.sleep(0.2)

        # Todo add a way to better detect when the playback has stopped (after can't be a coroutine)
        connection.play(audio)

        await asyncio.sleep(jingle.length)
        await connection.disconnect(force=False)
        return True
    finally:
        if connection.is_connected():
            await connection.disconnect(force=True)
            return False
