import discord
from .cogs import ReviewCog


def setup(bot: discord.Bot):
    bot.add_cog(ReviewCog(bot))
