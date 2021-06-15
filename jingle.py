import logging
from typing import Optional
from random import choice

from discordjingles.jingles import Jingle

logging.basicConfig(level=logging.INFO)

import asyncio
from discord import Member, VoiceState, VoiceChannel, FFmpegOpusAudio, VoiceClient, Message
from discord.errors import ClientException
from discord.ext.commands import Bot, Context, when_mentioned_or

from discordjingles.configuration import config
from discordjingles.voice_state_diff import get_voice_state_change, VoiceStateAction
from discordjingles.guild_settings import GuildSettingsManager, JingleMode
from discordjingles.jingles import JingleManager

log = logging.getLogger(__name__)

is_ready_to_play = True

bot = Bot(
    command_prefix=when_mentioned_or(".")
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
                f"but you haven't set a default jingle yet! Please set one with `{bot.command_prefix}setdefault`."
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
            f"Please set it using `{bot.command_prefix}setmode [disabled/single/random]`"
        )
        raise ValueError(f"Invalid JingleMode: {jingle_mode}")


@bot.command(name="setmode", help="Sets the jingle mode for the current server.", usage="[disabled/single/random]")
async def cmd_setmode(ctx: Context, mode_set: Optional[str] = None):
    requested_mode = None if mode_set is None else mode_set.strip().lower()

    if requested_mode is None or mode_set not in ["single", "random", "disabled"]:
        # Show help message
        await ctx.send(
            f"Usage: `{bot.command_prefix}setmode [disabled/single/random]`\n"
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
                           f" using the `{bot.command_prefix}setdefault` command.")
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
                       f"You can set one using `{bot.command_prefix}setdefault`.")
    else:
        await ctx.send(f":information_source: The default jingle is currently set to "
                       f"**{default_jingle.title}** (`{default_jingle.path.name}`)")


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

    await ctx.send(f":ballot_box_with_check: Default jingle set to **{chosen_jingle.title}**.")


@bot.event
async def on_ready():
    log.info("on_ready!")


@bot.event
async def on_voice_state_update(member: Member, state_before: VoiceState, state_after: VoiceState):
    if member.id == bot.user.id:
        return

    log.info(f"on_voice_state_update for {member.display_name}")

    guild_jingle_mode = guilds.get_guild_jingle_mode(member.guild)
    guild_jingle_default = guilds.get_guild_default_jingle(member.guild)

    # Make sure we only trigger this on whitelisted servers
    guild_id = member.guild.id
    if guild_id not in config.ENABLED_SERVERS:
        return

    if guild_jingle_mode == JingleMode.DISABLED:
        return

    # Make sure we only trigger this on voice channel joins
    log.info(f"Change: {get_voice_state_change(state_before, state_after).value}")
    if get_voice_state_change(state_before, state_after) != VoiceStateAction.JOINED:
        return

    target_voice_channel: VoiceChannel = state_after.channel

    try:
        # noinspection PyTypeChecker
        connection: VoiceClient = await target_voice_channel.connect(cls=VoiceClient)
    except ClientException as e:
        log.warning(f"Error while trying to connect: {e}")
        return


    try:
        if guild_jingle_mode == JingleMode.SINGLE:
            jingle = guild_jingle_default
        else:
            jingle = choice(list(jingle_manager.jingles_by_id.values()))

        audio = FFmpegOpusAudio(source=str(jingle.path.absolute()))

        # Delay playback very slightly
        await asyncio.sleep(0.2)

        # Todo add a way to better detect when the playback has stopped (after can't be a coroutine)
        connection.play(audio)

        await asyncio.sleep(jingle.length)
        await connection.disconnect(force=False)
    finally:
        if connection.is_connected():
            await connection.disconnect(force=True)


bot.run(config.BOT_TOKEN)
