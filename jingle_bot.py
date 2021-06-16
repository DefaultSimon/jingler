import logging
logging.basicConfig(level=logging.INFO)

from discord.ext.commands import Bot, when_mentioned_or

from jinglebot.database.db import Database
from jinglebot.configuration import config
from jinglebot.jingles import JingleManager

from jinglebot.cogs.guild_settings import GuildSettingsCog
from jinglebot.cogs.jingle_player import JinglePlayerCog
from jinglebot.cogs.misc import MiscCog
from jinglebot.cogs.user_settings import UserSettingsCog

log = logging.getLogger(__name__)

bot = Bot(
    command_prefix=when_mentioned_or(config.PREFIX)
)
database = Database()
jingle_manager = JingleManager()


@bot.event
async def on_ready():
    log.info("Bot is ready!")


bot.add_cog(GuildSettingsCog(bot))
bot.add_cog(JinglePlayerCog(bot))
bot.add_cog(MiscCog(bot))
bot.add_cog(UserSettingsCog(bot))


bot.run(config.BOT_TOKEN)
