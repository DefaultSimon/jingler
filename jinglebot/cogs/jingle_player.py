import asyncio
import logging
from typing import Optional

from discord import VoiceState, VoiceChannel, Message, Attachment, Member
from discord.ext.commands import Cog, Bot, command, Context

from jinglebot.configuration import config
from jinglebot.database.db import Database
from jinglebot.guild_settings import JingleMode
from jinglebot.jingles import JingleManager, JINGLES_DIR, generate_jingle_meta
from jinglebot.player import get_proper_jingle, play_jingle
from jinglebot.utilities import truncate_string
from jinglebot.voice_state_diff import get_voice_state_change, VoiceStateAction

log = logging.getLogger(__name__)

database = Database()
jingle_manager = JingleManager()


class JinglePlayerCog(Cog, name="Jingles"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(name="play", help="Manually play a jingle.", usage="[[random]/default]")
    async def cmd_play(self, ctx: Context, jingle_mode_option: Optional[str] = None):
        # Find member's voice channel
        voice_state: Optional[VoiceState] = ctx.author.voice
        if not voice_state:
            await ctx.send(":warning: You're currently not in a voice channel.")
            return

        voice_channel: Optional[VoiceChannel] = voice_state.channel
        if not voice_channel:
            await ctx.send(":warning: You're currently not in a voice channel.")
            return

        jingle_mode_option = jingle_mode_option.strip().lower() if jingle_mode_option else None
        jingle_mode = {
            "default": JingleMode.SINGLE,
            "random": JingleMode.RANDOM,
        }.get(jingle_mode_option, "default")
        if not jingle_mode:
            await ctx.send(":warning: Invalid jingle mode, available modes: `random` and `default` jingle.")
            return

        jingle = await get_proper_jingle(ctx.guild, jingle_mode)

        did_play = await play_jingle(voice_channel, jingle)
        if did_play:
            await ctx.message.add_reaction("☑️")
        else:
            await ctx.message.add_reaction("❌")

    @command(name="listjingles", help="Show available jingles.")
    async def cmd_list_jingles(self, ctx: Context):
        listed_jingles = list(jingle_manager.jingles_by_id.values())
        jingles_listed = "\n".join([
            f"[{index + 1}]({jingle.path.name}) {jingle.title}" for index, jingle in enumerate(listed_jingles)
        ])

        await ctx.send(
            f":musical_score: **Available jingles:**\n"
            f"```md\n{jingles_listed}```\n"
        )

    @command(name="reloadjingles", help="Reload available jingles.")
    async def cmd_reload_jingles(self, ctx: Context):
        jingle_manager.reload_available_jingles()
        await ctx.send(f":ballot_box_with_check: Jingles reloaded, **{len(jingle_manager.jingles_by_id)}** available.")

    @command(name="addjingle", help="Interactively add a new jingle.")
    async def cmd_add_jingle(self, ctx: Context):
        # Request a title from the user
        await ctx.send(
            ":scroll: You're about to add a new jingle. "
            "What title would you like to give it (max. 65 characters)?"
        )

        try:
            def ensure_author(m: Message):
                return m.author.id == ctx.author.id

            user_title_message: Message = await self._bot.wait_for("message", check=ensure_author, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send(":alarm_clock: Timed out (2 minutes), try again.")
            return

        jingle_title = truncate_string(str(user_title_message.content).strip(), 65)

        # Request an upload from the user
        await ctx.send(
            f":file_folder: Cool, the title will be `{jingle_title}`!\n"
            f"Please upload an `.mp3` file to add a new jingle with your title. Upload size limit: `1 MB`"
        )

        try:
            def ensure_upload(m: Message):
                return m.author.id == ctx.author.id \
                       and len(m.attachments) == 1 \
                       and m.attachments[0].filename.endswith(".mp3")

            user_upload_message: Message = await self._bot.wait_for("message", check=ensure_upload, timeout=240)
        except asyncio.TimeoutError:
            await ctx.send(":alarm_clock: Timed out (4 minutes), try again.")
            return

        attachment: Attachment = user_upload_message.attachments[0]
        if attachment.size >= (1024 * 1024):
            await ctx.send(":x: File is too big.")
            return

        # Download the file into "jingles"
        output_jingle_path = JINGLES_DIR / attachment.filename
        if output_jingle_path.exists():
            await ctx.send(":warning: A file with this name already exists, please rename and try again.")
            return

        response = await ctx.send(":yarn: Saving...")
        await attachment.save(str(output_jingle_path.absolute()))
        generate_jingle_meta(output_jingle_path, jingle_title)

        jingle_manager.reload_available_jingles()
        await response.edit(
            content=f":yarn: Jingle saved, `{len(jingle_manager.jingles_by_id)}` jingles now available."
        )

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, state_before: VoiceState, state_after: VoiceState):
        if member.id == self._bot.user.id:
            return
        log.info(f"on_voice_state_update for {member.display_name}")

        guild_jingle_mode: JingleMode = database.guild_get_jingle_mode(member.guild.id)
        if guild_jingle_mode == JingleMode.DISABLED:
            return

        # Make sure we only trigger this on whitelisted servers
        guild_id = member.guild.id
        if guild_id not in config.ENABLED_SERVERS:
            return

        # Make sure we only trigger this on voice channel joins
        log.info(f"Change: {get_voice_state_change(state_before, state_after).value}")
        if get_voice_state_change(state_before, state_after) != VoiceStateAction.JOINED:
            return

        target_voice_channel: VoiceChannel = state_after.channel

        jingle = await get_proper_jingle(member.guild)
        if jingle is None:
            return

        await play_jingle(target_voice_channel, jingle)
