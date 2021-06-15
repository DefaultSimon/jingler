import logging
logging.basicConfig(level=logging.INFO)

from typing import Optional

import asyncio
from discord import Member, VoiceState, VoiceChannel, Message, Attachment
from discord.ext.commands import Bot, Context, when_mentioned_or

from jinglebot.jingles import Jingle, generate_jingle_meta, JINGLES_DIR
from jinglebot.player import play_jingle, get_proper_jingle
from jinglebot.utilities import truncate_string
from jinglebot.configuration import config
from jinglebot.voice_state_diff import get_voice_state_change, VoiceStateAction
from jinglebot.guild_settings import GuildSettingsManager, JingleMode
from jinglebot.jingles import JingleManager

log = logging.getLogger(__name__)

is_ready_to_play = True

command_prefix = "."
bot = Bot(
    command_prefix=when_mentioned_or(command_prefix)
)
guilds = GuildSettingsManager()
jingle_manager = JingleManager()


@bot.command(name="ping", help="Pings the bot.")
async def cmd_ping(ctx: Context):
    await ctx.send(":musical_note: I'm alive!")


@bot.command(name="getmode", help="Displays the current jingle mode.")
async def cmd_getmode(ctx: Context):
    jingle_mode: JingleMode = guilds.get_guild_jingle_mode(ctx.guild)

    if jingle_mode == JingleMode.SINGLE:
        default_jingle: Jingle = guilds.get_guild_default_jingle(ctx.guild)

        # Warn the user if somehow the default jingle is unset
        if default_jingle is None:
            log.error(
                f"Jingle mode is set to 'single' on guild "
                f"'{ctx.guild.name}' ({ctx.guild.id}), but default jingle is unset."
            )
            await ctx.send(
                f":space_invader: Black magic! Jingle mode is set to `single`, "
                f"but you haven't set a default jingle yet! Please set one with `{command_prefix}setdefault`."
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
            f"Please set it using `{command_prefix}setmode [disabled/single/random]`"
        )
        raise ValueError(f"Invalid JingleMode: {jingle_mode}")


@bot.command(name="setmode", help="Sets the jingle mode for the current server.", usage="[disabled/single/random]")
async def cmd_setmode(ctx: Context, mode_set: Optional[str] = None):
    requested_mode = None if mode_set is None else mode_set.strip().lower()

    if requested_mode is None or mode_set not in ["single", "random", "disabled"]:
        # Show help message
        await ctx.send(
            f"Usage: `{command_prefix}setmode [disabled/single/random]`\n"
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
        if guilds.get_guild_default_jingle(ctx.guild) is None:
            await ctx.send(f":warning: Please set a default jingle first"
                           f" using the `{command_prefix}setdefault` command.")
            return

    guilds.update_guild_jingle_mode(ctx.guild, mode_enum)
    if mode_enum == JingleMode.DISABLED:
        await ctx.send(":checkered_flag: Guild jingle mode has been set to `disabled` - no jingles will be played.")
    elif mode_enum == JingleMode.SINGLE:
        default_jingle: Jingle = guilds.get_guild_default_jingle(ctx.guild)
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


@bot.command(name="getdefault", help="Displays the default jingle's information.")
async def cmd_setdefault(ctx: Context):
    default_jingle: Optional[Jingle] = guilds.get_guild_default_jingle(ctx.guild)

    if default_jingle is None:
        await ctx.send(f":information_source: No default jingle is currently set. "
                       f"You can set one using `{command_prefix}setdefault`.")
    else:
        await ctx.send(f":information_source: The default jingle is currently set to "
                       f"`{default_jingle.title} ({default_jingle.path.name})`")


@bot.command(name="setdefault", help="Sets the default jingle for this server.")
async def cmd_setdefault(ctx: Context):
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

        response: Message = await bot.wait_for("message", check=verify_response, timeout=120)
    except asyncio.TimeoutError:
        await ctx.send(":alarm_clock: Timed out (2 minutes), try again.")
        return

    chosen_index = int(response.content) - 1
    if chosen_index < 0 or chosen_index >= len(listed_jingles):
        await ctx.send(":warning: Invalid number, try again.")
        return

    chosen_jingle: Jingle = listed_jingles[chosen_index]
    guilds.update_guild_single_jingle(ctx.guild, chosen_jingle)

    await ctx.send(
        f":ballot_box_with_check: Default jingle "
        f"set to `{chosen_jingle.title} ({chosen_jingle.path.name})`."
   )


@bot.command(name="play", help="Manually play a jingle.", usage="[[random]/default]")
async def cmd_play(ctx: Context, jingle_mode_option: Optional[str] = None):
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


@bot.command(name="listjingles", help="Show available jingles.")
async def cmd_list_jingles(ctx: Context):
    listed_jingles = list(jingle_manager.jingles_by_id.values())
    jingles_listed = "\n".join([
        f"[{index + 1}]({jingle.path.name}) {jingle.title}" for index, jingle in enumerate(listed_jingles)
    ])

    await ctx.send(
        f":musical_score: **Available jingles:**\n"
        f"```md\n{jingles_listed}```\n"
    )


@bot.command(name="reloadjingles", help="Reload available jingles.")
async def cmd_reload_jingles(ctx: Context):
    jingle_manager.reload_available_jingles()
    await ctx.send(f":ballot_box_with_check: Jingles reloaded, **{len(jingle_manager.jingles_by_id)}** available.")


@bot.command(name="addjingle", help="Interactively add a new jingle.")
async def cmd_add_jingle(ctx: Context):
    # Request a title from the user
    await ctx.send(
        ":scroll: You're about to add a new jingle. "
        "What title would you like to give it (max. 65 characters)?"
    )

    try:
        def ensure_author(m: Message):
            return m.author.id == ctx.author.id

        user_title_message: Message = await bot.wait_for("message", check=ensure_author, timeout=120)
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

        user_upload_message: Message = await bot.wait_for("message", check=ensure_upload, timeout=240)
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


@bot.event
async def on_ready():
    log.info("on_ready!")


@bot.event
async def on_voice_state_update(member: Member, state_before: VoiceState, state_after: VoiceState):
    if member.id == bot.user.id:
        return
    log.info(f"on_voice_state_update for {member.display_name}")

    guild_jingle_mode = guilds.get_guild_jingle_mode(member.guild)
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


bot.run(config.BOT_TOKEN)
