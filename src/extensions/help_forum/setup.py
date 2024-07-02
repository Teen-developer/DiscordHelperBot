import discord
from .cogs import HelpCog, ReputationCog


def setup(bot: discord.Bot):
    bot.add_cog(HelpCog(bot))
    bot.add_cog(ReputationCog())