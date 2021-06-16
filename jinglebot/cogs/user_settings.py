import asyncio
from typing import Optional

from discord import Message
from discord.ext.commands import Cog, Bot, command, Context

from jinglebot.configuration import config
from jinglebot.database.db import Database
from jinglebot.emojis import Emoji
from jinglebot.jingles import Jingle, JingleManager, format_jingles_for_pagination
from jinglebot.pagination import is_reaction_author, Pagination
from jinglebot.utilities import sanitize_jingle_code

jingle_manager = JingleManager()
db = Database()


class UserSettingsCog(Cog, name="UserSettings"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(name="getthemesong", help="Check your current theme song.")
    async def cmd_get_theme_song(self, ctx: Context):
        theme_song_id: Optional[str] = db.user_get_theme_song_jingle_id(ctx.author.id)
        theme_song: Optional[Jingle] = jingle_manager.get_jingle_by_id(theme_song_id)

        if theme_song is None:
            await ctx.send(
                f"{Emoji.MAILBOX_CLOSED} Looks like you currently don't have a theme song! "
                f"You can set one using `{config.PREFIX}setthemesong`!"
            )
        else:
            await ctx.send(
                f"{Emoji.MAILBOX_WITH_MAIL} Your current theme song "
                f"is `{theme_song.title} ({theme_song.path.name})`."
            )

    @command(name="setthemesong", help="Set your theme song (jingle).", usage="(jingle code)")
    async def cmd_set_theme_song(self, ctx: Context, prefilled_jingle_code: Optional[str] = None):
        if prefilled_jingle_code is not None:
            # User already supplied the new theme song, check if valid
            new_theme_song_id: str = sanitize_jingle_code(prefilled_jingle_code)

            if new_theme_song_id not in jingle_manager.jingles_by_id or len(new_theme_song_id) != 5:
                await ctx.send(f"{Emoji.WARNING} Invalid jingle code.")
                return

        else:
            # Do this interactively
            pagination = Pagination(
                channel=ctx.channel,
                client=self._bot,
                beginning_content=f"{Emoji.DIVIDERS} Available jingles:",
                item_list=format_jingles_for_pagination(jingle_manager),
                item_max_per_page=10,
                end_content=f"\nPick a jingle to set as the default on this server and reply with its code. "
                            f"If the \"single\" mode is activated, this jingle will "
                            f"be played each time instead of a random jingle.",
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

            new_theme_song_id: str = sanitize_jingle_code(response.content)

            if new_theme_song_id not in jingle_manager.jingles_by_id or len(new_theme_song_id) != 5:
                await ctx.send(f"{Emoji.WARNING} Invalid jingle code.")
                return

            await pagination.stop_pagination()

        # Update the setting
        new_theme_song: Optional[Jingle] = jingle_manager.get_jingle_by_id(new_theme_song_id)
        if not new_theme_song:
            await ctx.send(f"{Emoji.WARNING} Something went wrong: the jingle was picked but does not exist.")
            return

        db.user_set_theme_song_jingle_id(ctx.author.id, new_theme_song_id)
        await ctx.send(
            f"{Emoji.BALLOT_BOX_WITH_CHECK} Your new theme song is "
            f"`{new_theme_song.title} ({new_theme_song.path.name})`."
        )
