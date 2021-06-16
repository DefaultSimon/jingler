from discord.ext.commands import Bot, Cog, command, Context


class MiscCog(Cog, name="Misc"):
    def __init__(self, bot: Bot):
        self._bot = bot

    @command(name="ping", help="Pings the bot.")
    async def cmd_ping(self, ctx: Context):
        await ctx.send(":musical_note: I'm alive!")
