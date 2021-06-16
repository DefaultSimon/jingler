import asyncio
import logging
from random import choice
from typing import Optional

from discord import VoiceChannel, VoiceClient, ClientException, FFmpegOpusAudio, Guild

from jinglebot.database.db import Database
from jinglebot.guild_settings import JingleMode
from jinglebot.jingles import Jingle, JingleManager

log = logging.getLogger(__name__)

jingle_manager = JingleManager()
database = Database()


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
    guild_jingle_mode: JingleMode = database.guild_get_jingle_mode(guild.id)
    guild_default_jingle_id: Optional[str] = database.guild_get_default_jingle_id(guild.id)
    guild_default_jingle: Optional[Jingle] = jingle_manager.get_jingle_by_id(guild_default_jingle_id)

    if guild_jingle_mode == JingleMode.SINGLE or override_mode == JingleMode.SINGLE:
        return guild_default_jingle
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
