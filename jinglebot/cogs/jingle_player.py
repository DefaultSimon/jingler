import asyncio
import logging
from typing import Optional

from discord import VoiceState, VoiceChannel, Message, Attachment, Member
from discord.ext.commands import Cog, Bot, command, Context

from jinglebot.configuration import config
from jinglebot.database.db import Database
from jinglebot.emojis import UnicodeEmoji, Emoji
from jinglebot.jingles import JingleManager, JINGLES_DIR, save_jingle_meta, get_audio_file_length, JingleMode
from jinglebot.pagination import Pagination, is_reaction_author
from jinglebot.player import get_guild_jingle, play_jingle
from jinglebot.utilities import truncate_string, generate_jingle_id
from jinglebot.voice_state_diff import get_voice_state_change, VoiceStateAction

log = logging.getLogger(__name__)

database = Database()
jingle_manager = JingleManager()

MAX_JINGLE_FILE_SIZE_MB = 1
MAX_JINGLE_LENGTH_SEC = 10


class JinglePlayerCog(Cog, name="Jingles"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(name="playrandom", help="Manually play a random jingle.")
    async def cmd_play(self, ctx: Context, jingle_mode_option: Optional[str] = None):
        # Find member's voice channel
        voice_state: Optional[VoiceState] = ctx.author.voice
        if not voice_state:
            await ctx.send(f"{Emoji.WARNING} You're currently not in a voice channel.")
            return

        voice_channel: Optional[VoiceChannel] = voice_state.channel
        if not voice_channel:
            await ctx.send(f"{Emoji.WARNING} You're currently not in a voice channel.")
            return

        jingle = await get_guild_jingle(ctx.guild, JingleMode.RANDOM)
        did_play = await play_jingle(voice_channel, jingle)
        if did_play:
            await ctx.message.add_reaction(UnicodeEmoji.BALLOT_BOX_WITH_CHECK)
        else:
            await ctx.message.add_reaction(UnicodeEmoji.X)

    @command(name="listjingles", help="Show available jingles.")
    async def cmd_list_jingles(self, ctx: Context):
        listed_jingles = list(jingle_manager.jingles_by_id.values())
        formatted_jingle_list = [
            f"[{jingle.id}]({jingle.path.name}) {jingle.title}" for index, jingle in enumerate(listed_jingles)
        ]

        await Pagination(
            channel=ctx.channel,
            client=self._bot,
            beginning_content=f"{Emoji.DIVIDERS} There are `{len(listed_jingles)}` available:\n",
            item_list=formatted_jingle_list,
            item_max_per_page=15,
            code_block_begin="```md\n",
            paginate_action_check=is_reaction_author(ctx.author.id),
            timeout=120,
            begin_pagination_immediately=True,
        )

    @command(name="reloadjingles", help="Reload available jingles.")
    async def cmd_reload_jingles(self, ctx: Context):
        jingle_manager.reload_available_jingles()
        await ctx.send(f"{Emoji.BALLOT_BOX_WITH_CHECK} Jingles reloaded, **{len(jingle_manager.jingles_by_id)}** available.")

    @command(name="addjingle", help="Interactively add a new jingle.")
    async def cmd_add_jingle(self, ctx: Context):
        # Request a title from the user
        await ctx.send(
            f"{Emoji.SCROLL} You're about to add a new jingle. "
            "What title would you like to give it (max. 65 characters)?"
        )

        try:
            def ensure_author(m: Message):
                return m.author.id == ctx.author.id

            user_title_message: Message = await self._bot.wait_for("message", check=ensure_author, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send(f"{Emoji.ALARM_CLOCK} Timed out (2 minutes), try again.")
            return

        jingle_title = truncate_string(str(user_title_message.content).strip(), 65)
        jingle_id = generate_jingle_id()

        # Request an upload from the user
        await ctx.send(
            f"{Emoji.FILE_FOLDER} Cool, the title will be `{jingle_title}`! "
            f"Please upload an `.mp3` file to add a new jingle with your title.\n"
            f"Make sure the file is smaller than `{MAX_JINGLE_FILE_SIZE_MB} MB` "
            f"and shorter than `{MAX_JINGLE_LENGTH_SEC} seconds`."
        )

        try:
            def ensure_upload(m: Message):
                return m.author.id == ctx.author.id \
                       and len(m.attachments) == 1 \
                       and m.attachments[0].filename.endswith(".mp3")

            user_upload_message: Message = await self._bot.wait_for("message", check=ensure_upload, timeout=240)
        except asyncio.TimeoutError:
            await ctx.send(f"{Emoji.ALARM_CLOCK} Timed out (4 minutes), try again.")
            return

        attachment: Attachment = user_upload_message.attachments[0]

        # Make sure the file size limit is respected
        if attachment.size >= (1024 * 1024 * MAX_JINGLE_FILE_SIZE_MB):
            await ctx.send(f"{Emoji.X} File is too big.")
            return

        # Download the file into "jingles"
        output_jingle_path = JINGLES_DIR / attachment.filename
        if output_jingle_path.exists():
            await ctx.send(f"{Emoji.WARNING} A file with this name already exists, please rename and try again.")
            return

        response = await ctx.send(f"{Emoji.YARN} Saving...")

        await attachment.save(str(output_jingle_path.absolute()))

        # Make sure the audio file length limit is respected
        if jingle_length := get_audio_file_length(output_jingle_path) > MAX_JINGLE_LENGTH_SEC:
            await ctx.send(f"{Emoji.WARNING} File is too long (`{jingle_length} s`), please shorten and try again.")

            # Don't forget to delete the file!
            if output_jingle_path.exists():
                output_jingle_path.unlink()
            return

        # If everything checks out, generate the .meta file, reload available jingles and inform the user
        save_jingle_meta(output_jingle_path, jingle_title, jingle_id)

        jingle_manager.reload_available_jingles()
        await response.edit(
            content=f"{Emoji.YARN} Jingle saved and available with code `{jingle_id}`."
                    f"\n`{len(jingle_manager.jingles_by_id)}` jingles now available."
        )

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, state_before: VoiceState, state_after: VoiceState):
        if member.id == self._bot.user.id:
            return

        guild_jingle_mode: JingleMode = database.guild_get_jingle_mode(member.guild.id)
        if guild_jingle_mode == JingleMode.DISABLED:
            return

        # Make sure we only trigger this on whitelisted servers
        guild_id = member.guild.id
        if guild_id not in config.ENABLED_SERVERS:
            return

        # Make sure we only trigger this on voice channel joins
        if get_voice_state_change(state_before, state_after) != VoiceStateAction.JOINED:
            return

        target_voice_channel: VoiceChannel = state_after.channel

        # If this user has a theme song, play that one
        # Otherwise pick a guild jingle (random/default, depending on setting)
        user_theme_song_id: Optional[str] = database.user_get_theme_song_jingle_id(member.id)
        if user_theme_song_id is not None and user_theme_song_id in jingle_manager.jingles_by_id:
            jingle = jingle_manager.get_jingle_by_id(user_theme_song_id)
            log.info(
                f"User \"{member.name}\" ({member.id}) has theme song: \"{jingle.title}\" ({jingle.path.name})"
            )
        else:
            jingle = await get_guild_jingle(member.guild)
            log.info(
                f"User \"{member.name}\" ({member.id}) does not have a theme song; "
                f"picked from guild: \"{jingle.title}\" ({jingle.path.name})"
            )

        await play_jingle(target_voice_channel, jingle)
