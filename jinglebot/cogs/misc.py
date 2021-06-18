import asyncio
import logging
import time
import subprocess
from datetime import timedelta

from discord import Game
from discord.ext.commands import Bot, Cog, command, Context

from jinglebot.configuration import pyproject, BASE_DIR
from jinglebot.database.db import Database
from jinglebot.emojis import Emoji

STARTUP_TIME = time.time()

log = logging.getLogger(__name__)
db = Database()


class MiscCog(Cog, name="Misc"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(
        name="ping",
        help="Shows some basic information about Jingler."
    )
    async def cmd_ping(self, ctx: Context):
        # Uptime
        uptime_delta = timedelta(seconds=int(time.time() - STARTUP_TIME))

        # Git commit
        if (BASE_DIR / ".git").exists():
            git_process = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            stripped_output: str = git_process.stdout.strip('\n')
            git_info: str = f" @ {stripped_output}"
        else:
            git_info: str = ""

        # Database
        db_total_changes = db.con.total_changes

        await ctx.send(
            f"{Emoji.TRUMPET} I'm alive!\n"
            f"Version: `{pyproject.VERSION}{git_info}`.\n"
            f"Uptime: `{str(uptime_delta)}`\n"
            f"Database: `{db_total_changes}` changes since startup"
        )

    @Cog.listener(name="on_ready")
    async def misc_on_ready(self):
        playing_str_with_version = f"jingles (v{pyproject.VERSION})"
        playing_str = "jingles"

        log.info(f"Setting presence to {playing_str_with_version}, waiting one minute.")
        jingle_activity_with_version: Game = Game(name=playing_str_with_version)
        await self._bot.change_presence(activity=jingle_activity_with_version)

        await asyncio.sleep(60)

        log.info(f"Setting presence to {playing_str}")
        jingle_activity: Game = Game(name=playing_str)
        await self._bot.change_presence(activity=jingle_activity)
