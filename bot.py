# Nothing is imported, this sets up the logging
# noinspection PyUnresolvedReferences
import jingler.logs

import logging
import traceback

from discord.ext.commands import Bot, when_mentioned_or, Context, CheckFailure

from jingler.database.db import Database
from jingler.configuration import config
from jingler.jingles import JingleManager

from jingler.cogs.guild_settings import GuildSettingsCog
from jingler.cogs.jingle_player import JinglePlayerCog
from jingler.cogs.misc import MiscCog
from jingler.cogs.user_settings import UserSettingsCog

log = logging.getLogger(__name__)

bot = Bot(
    command_prefix=when_mentioned_or(config.PREFIX)
)
database = Database()
jingle_manager = JingleManager()


@bot.event
async def on_ready():
    log.info("Bot is ready!")


if config.USE_SERVER_WHITELIST:
    @bot.check
    async def check_whitelist(ctx: Context):
        return ctx.guild.id in config.SERVER_WHITELIST


@bot.event
async def on_command_error(ctx: Context, exception):
    if not isinstance(exception, CheckFailure):
        log.error(
            f"Command error: command={ctx.command}, author={ctx.author} ({ctx.author.id}), "
            f"args={ctx.args}, kwargs={ctx.kwargs}:\n"
            f"{traceback.format_exc()}"
        )


bot.add_cog(GuildSettingsCog(bot))
bot.add_cog(JinglePlayerCog(bot))
bot.add_cog(MiscCog(bot))
bot.add_cog(UserSettingsCog(bot))

bot.run(config.BOT_TOKEN)
