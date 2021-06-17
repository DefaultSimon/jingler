import asyncio
import logging
from typing import Optional

from discord import Message
from discord.ext.commands import Cog, Bot, command, Context

from jinglebot.configuration import config
from jinglebot.database.db import Database
from jinglebot.emojis import Emoji
from jinglebot.jingles import JingleManager, Jingle, format_jingles_for_pagination, JingleMode
from jinglebot.pagination import is_reaction_author, Pagination
from jinglebot.utilities import sanitize_jingle_code

log = logging.getLogger(__name__)

database = Database()
jingle_manager = JingleManager()

HELP_SET_JINGLE_MODE: str = \
    "Sets the jingle mode for the current server.\n" \
    "Available modes dictate behaviour upon members joining a voice channel:\n" \
    "\tdisabled - do not play any jingles\n" \
    "\tsingle - play a specific jingle (personal theme songs override this)\n" \
    "\trandom - play a completely random jingle each time (personal theme songs override this)"


class GuildSettingsCog(Cog, name="GuildSettings"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(
        name="getjinglemode",
        help="Displays the jingle mode for the current server."
    )
    async def cmd_get_jingle_mode(self, ctx: Context):
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
                    f"{Emoji.SPACE_INVADER} Black magic! Jingle mode is set to `single`, "
                    f"but you haven't set a default jingle yet! Please set one with `{config.PREFIX}setdefault`."
                )
                return

            await ctx.send(
                f"{Emoji.LEVEL_SLIDER} Jingle mode is set to `single` - "
                f"the jingle played upon joining a voice channel will "
                f"always be `{default_jingle.title} ({default_jingle.path.name})`"
            )
        elif jingle_mode == JingleMode.RANDOM:
            await ctx.send(
                f"{Emoji.GAME_DIE} Jingle mode is set to `random` - "
                "upon joining a voice channel a random jingle will be played."
            )
        elif jingle_mode == JingleMode.DISABLED:
            await ctx.send(
                f"{Emoji.DETECTIVE} Jingle mode is set to `disabled` - "
                "no jingles will be played upon members joining a voice channel."
            )
        else:
            await ctx.send(
                f"{Emoji.EXCLAMATION} Something went wrong, the jingle mode is invalid. "
                f"Please set it using `{config.PREFIX}setjinglemode [disabled/single/random]`"
            )
            raise ValueError(f"Invalid JingleMode: {jingle_mode}")

    @command(
        name="setjinglemode",
        help=HELP_SET_JINGLE_MODE,
        usage="[disabled/single/random]"
    )
    async def cmd_set_jingle_mode(self, ctx: Context, mode_set: Optional[str] = None):
        requested_mode = None if mode_set is None else mode_set.strip().lower()

        if requested_mode is None or mode_set not in ["single", "random", "disabled"]:
            # Show help message
            await ctx.send(
                f"Usage: `{config.PREFIX}setjinglemode [disabled/single/random]`\n"
                + HELP_SET_JINGLE_MODE
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
                await ctx.send(f"{Emoji.WARNING} Please set a default jingle first"
                               f" using the `{config.PREFIX}setdefault` command.")
                return

        database.guild_set_jingle_mode(ctx.guild.id, mode_enum)
        if mode_enum == JingleMode.DISABLED:
            await ctx.send(
                f"{Emoji.CHECKERED_FLAG} Guild jingle mode has been set to `disabled` - no jingles will be played."
            )
        elif mode_enum == JingleMode.SINGLE:
            default_jingle_id: Optional[str] = database.guild_get_default_jingle_id(ctx.guild.id)
            default_jingle: Jingle = jingle_manager.get_jingle_by_id(default_jingle_id)
            await ctx.send(
                f"{Emoji.CHECKERED_FLAG} Guild jingle mode has been set to `single` "
                f"- jingle `{default_jingle.title} ({default_jingle.path.name})` "
                f"will be played upon members joining a voice channel."
            )
        elif mode_enum == JingleMode.RANDOM:
            await ctx.send(
                f"{Emoji.CHECKERED_FLAG} Guild jingle mode has been set to `random` - "
                "a random jingle will be played each time a member joins a voice channel."
            )

    @command(
        name="getdefault",
        help="Displays the default jingle for this server."
    )
    async def cmd_getdefault(self, ctx: Context):
        default_jingle_id: Optional[str] = database.guild_get_default_jingle_id(ctx.guild.id)
        default_jingle: Jingle = jingle_manager.get_jingle_by_id(default_jingle_id)

        if default_jingle is None:
            await ctx.send(f"{Emoji.INFORMATION_SOURCE} No default jingle is currently set. "
                           f"You can set one using `{config.PREFIX}setdefault`.")
        else:
            await ctx.send(f"{Emoji.INFORMATION_SOURCE} The default jingle is currently set to "
                           f"`{default_jingle.title} ({default_jingle.path.name})`")

    @command(
        name="setdefault",
        help="Sets the default jingle for this server. "
             "If the server jingle mode is not \"single\", this will have no effect.",
        usage="(jingle code)"
    )
    async def cmd_setdefault(self, ctx: Context, prefilled_jingle_id: Optional[str] = None):
        if prefilled_jingle_id is not None:
            # User already supplied the new default, check if the code is valid and update

            prefilled_jingle_id = sanitize_jingle_code(prefilled_jingle_id)
            if prefilled_jingle_id not in jingle_manager.jingles_by_id:
                await ctx.send(f"{Emoji.WARNING} Invalid jingle code.")
                return

            new_default_jingle_id: str = prefilled_jingle_id
        else:
            # User did not yet choose a jingle, do this interactively
            # List available jingles and allow the user to pick
            pagination = Pagination(
                channel=ctx.channel,
                client=self._bot,
                beginning_content=f"{Emoji.DIVIDERS} Available jingles:",
                item_list=format_jingles_for_pagination(jingle_manager),
                item_max_per_page=10,
                end_content=f"\nPick a jingle to set as the default on this server and reply with its code. "
                            f"If the \"single\" mode is active this jingle will be played each time "
                            f"a member joins a voice channel (unless they have their own theme song).",
                code_block_begin="```md\n",
                paginate_action_check=is_reaction_author(ctx.author.id),
                timeout=120,
                begin_pagination_immediately=True,
            )

            try:
                def verify_response(message: Message):
                    return message.author.id == ctx.author.id \
                           and message.channel.id == ctx.channel.id \
                           and len(sanitize_jingle_code(message.content)) == 5

                response: Message = await self._bot.wait_for("message", check=verify_response, timeout=120)
            except asyncio.TimeoutError:
                await ctx.send(f"{Emoji.ALARM_CLOCK} Timed out (`2 minutes`), try again.")
                return

            new_default_jingle_id: str = sanitize_jingle_code(response.content)
            if new_default_jingle_id not in jingle_manager.jingles_by_id or len(new_default_jingle_id) != 5:
                await ctx.send(f"{Emoji.WARNING} Invalid jingle code.")
                return

            await pagination.stop_pagination()

        new_default_jingle: Optional[Jingle] = jingle_manager.get_jingle_by_id(new_default_jingle_id)
        if not new_default_jingle:
            await ctx.send(f"{Emoji.WARNING} Something went wrong: the jingle was picked but does not exist.")
            return

        database.guild_set_default_jingle_id(ctx.guild.id, new_default_jingle_id)
        await ctx.send(
            f"{Emoji.BALLOT_BOX_WITH_CHECK} Default jingle "
            f"set to `{new_default_jingle.title} ({new_default_jingle.path.name})`."
        )

    @command(
        name="getthemesongmode",
        help="Check your current theme song setting for the server."
    )
    async def cmd_get_theme_song_mode(self, ctx: Context):
        theme_song_mode: bool = database.guild_get_theme_songs_mode(ctx.guild.id)
        if theme_song_mode is True:
            await ctx.send(
                f"{Emoji.PLACARD} Theme songs are currently **enabled**. If a member has their own theme song, "
                f"it will be played when they join a voice channel (unless that feature is disabled as well)."
            )
        else:
            await ctx.send(
                f"{Emoji.PLACARD} Theme songs are currently **disabled**. Any potential theme songs will be ignored "
                f"and which jingles are played is dictated by the jingle mode (see `{config.PREFIX}getjinglemode`)."
            )

    @command(
        name="setthemesongmode",
        help="Enable (play if set) or disable (ignore) theme songs for this server.",
        usage="[enable/disable]"
    )
    async def cmd_set_theme_song_mode(self, ctx: Context, enable_or_disable: Optional[str] = None):
        if enable_or_disable is None:
            # Print help message
            await ctx.send(
                f"Usage: `{config.PREFIX}setthemesongmode [enable/disable]`\n"
                f"Enable (play if set) or disable (ignore) theme songs for this server."
            )
            return

        enable_or_disable = enable_or_disable.strip().lower()
        if enable_or_disable in ["enable", "enabled"]:
            theme_song_option: bool = True
        elif enable_or_disable in ["disable", "disabled"]:
            theme_song_option: bool = False
        else:
            await ctx.send(
                f"{Emoji.WARNING} Invalid mode (should be either `enable` or `disable`), please try again."
            )
            return

        database.guild_set_theme_songs_mode(ctx.guild.id, theme_song_option)
        if theme_song_option is True:
            await ctx.send(
                f"{Emoji.PLACARD} Theme songs are now **enabled** - if a member has "
                f"their own theme song, it will be played."
            )
        else:
            await ctx.send(
                f"{Emoji.PLACARD} Theme songs are now **disabled** - any potential theme songs "
                f"that members have will be ignored in this server."
            )
