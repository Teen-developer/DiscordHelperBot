import discord
from .cogs import HelpCog


def setup(bot: discord.Bot):
    bot.add_cog(HelpCog())