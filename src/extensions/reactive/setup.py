import discord
from .cogs import BoostyCog


def setup(bot: discord.Bot):
    bot.add_cog(BoostyCog(bot))