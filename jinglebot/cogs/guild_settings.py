import asyncio
import logging
from typing import Optional

from discord import Message
from discord.ext.commands import Cog, Bot, command, Context

from jinglebot.configuration import config
from jinglebot.database.db import Database
from jinglebot.guild_settings import JingleMode
from jinglebot.jingles import JingleManager, Jingle

log = logging.getLogger(__name__)

database = Database()
jingle_manager = JingleManager()


class GuildSettingsCog(Cog, name="GuildSettings"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(name="getmode", help="Displays the current jingle mode.")
    async def cmd_getmode(self, ctx: Context):
        jingle_mode: JingleMode = database.guild_get_jingle_mode(ctx.guild.id)

        if jingle_mode == JingleMode.SINGLE:
            default_jingle_id: Optional[str] = database.guild_get_default_jingle_id(ctx.guild.id)
            default_jingle: Jingle = jingle_manager.get_jingle_by_id(default_jingle_id)

            # Warn the user if somehow the default jingle is unset
            if default_jingle is None:
                log.error(
                    f"Jingle mode is set to 'single' on guild "
                    f"'{ctx.guild.name}' ({ctx.guild.id}), but default jingle is unset."
                )
                await ctx.send(
                    f":space_invader: Black magic! Jingle mode is set to `single`, "
                    f"but you haven't set a default jingle yet! Please set one with `{config.PREFIX}setdefault`."
                )
                return

            await ctx.send(
                f":headphones: Jingle mode is set to `single` - "
                f"the jingle played upon joining a voice channel will "
                f"always be `{default_jingle.title} ({default_jingle.path.name})`"
            )
        elif jingle_mode == JingleMode.RANDOM:
            await ctx.send(
                ":headphones: Jingle mode is set to `random` - "
                "upon joining a voice channel a random jingle will be played."
            )
        elif jingle_mode == JingleMode.DISABLED:
            await ctx.send(
                ":headphones: Jingle mode is set to `disabled` - "
                "no jingles will be played upon members joining a voice channel."
            )
        else:
            await ctx.send(
                ":exclamation: Something went wrong, the jingle mode is invalid. "
                f"Please set it using `{config.PREFIX}setmode [disabled/single/random]`"
            )
            raise ValueError(f"Invalid JingleMode: {jingle_mode}")

    @command(name="setmode", help="Sets the jingle mode for the current server.", usage="[disabled/single/random]")
    async def cmd_setmode(self, ctx: Context, mode_set: Optional[str] = None):
        requested_mode = None if mode_set is None else mode_set.strip().lower()

        if requested_mode is None or mode_set not in ["single", "random", "disabled"]:
            # Show help message
            await ctx.send(
                f"Usage: `{config.PREFIX}setmode [disabled/single/random]`\n"
                f"Available modes: \n"
                f"\t`disabled` - do not play any jingles upon members joining a voice channel\n"
                f"\t`single` - play a specific jingle upon members joining a voice channel\n"
                f"\t`random` - play a random jingle upon members joining a voice channel"
            )
            return

        mode_enum: JingleMode = {
            "disabled": JingleMode.DISABLED,
            "single": JingleMode.SINGLE,
            "random": JingleMode.RANDOM,
        }.get(requested_mode)

        if mode_enum == JingleMode.SINGLE:
            # Reject until the default jingle is set
            if database.guild_get_default_jingle_id(ctx.guild.id) is None:
                await ctx.send(f":warning: Please set a default jingle first"
                               f" using the `{config.PREFIX}setdefault` command.")
                return

        database.guild_set_jingle_mode(ctx.guild.id, mode_enum)
        if mode_enum == JingleMode.DISABLED:
            await ctx.send(":checkered_flag: Guild jingle mode has been set to `disabled` - no jingles will be played.")
        elif mode_enum == JingleMode.SINGLE:
            default_jingle_id: Optional[str] = database.guild_get_default_jingle_id(ctx.guild.id)
            default_jingle: Jingle = jingle_manager.get_jingle_by_id(default_jingle_id)
            await ctx.send(
                f":checkered_flag: Guild jingle mode has been set to `single` "
                f"- jingle `{default_jingle.title} ({default_jingle.path.name})` "
                f"will be played upon members joining a voice channel."
            )
        elif mode_enum == JingleMode.RANDOM:
            await ctx.send(
                ":checkered_flag: Guild jingle mode has been set to `random` - "
                "a random jingle will be played each time a member joins a voice channel."
            )

    @command(name="getdefault", help="Displays the default jingle's information.")
    async def cmd_setdefault(self, ctx: Context):
        default_jingle_id: Optional[str] = database.guild_get_default_jingle_id(ctx.guild.id)
        default_jingle: Jingle = jingle_manager.get_jingle_by_id(default_jingle_id)

        if default_jingle is None:
            await ctx.send(f":information_source: No default jingle is currently set. "
                           f"You can set one using `{config.PREFIX}setdefault`.")
        else:
            await ctx.send(f":information_source: The default jingle is currently set to "
                           f"`{default_jingle.title} ({default_jingle.path.name})`")

    @command(name="setdefault", help="Sets the default jingle for this server.")
    async def cmd_setdefault(self, ctx: Context):
        # List available jingles and allow the user to pick
        listed_jingles = list(jingle_manager.jingles_by_id.values())
        jingles_listed = "\n".join([
            f"[{index + 1}]({jingle.path.name}) {jingle.title}" for index, jingle in enumerate(listed_jingles)
        ])

        await ctx.send(
            f":musical_score: **Available jingles:**\n"
            f"```md\n{jingles_listed}```\n"
            f"Pick a jingle to set as the default on this server.\n"
            f"If the \"single\" jingle mode is activated, this jingle will be played instead of a random jingle."
        )

        try:
            def verify_response(message: Message):
                return message.author.id == ctx.author.id \
                       and message.channel.id == ctx.channel.id \
                       and str(message.content).isdigit()

            response: Message = await self._bot.wait_for("message", check=verify_response, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send(":alarm_clock: Timed out (2 minutes), try again.")
            return

        chosen_index = int(response.content) - 1
        if chosen_index < 0 or chosen_index >= len(listed_jingles):
            await ctx.send(":warning: Invalid number, try again.")
            return

        chosen_jingle: Jingle = listed_jingles[chosen_index]
        database.guild_set_default_jingle_id(ctx.guild.id, chosen_jingle.id)

        await ctx.send(
            f":ballot_box_with_check: Default jingle "
            f"set to `{chosen_jingle.title} ({chosen_jingle.path.name})`."
        )
