import discord
from .cogs import BoostyCog, WelcomeCog, OwnerNotificationCog


def setup(bot: discord.Bot):
    bot.add_cog(BoostyCog(bot))
    bot.add_cog(WelcomeCog(bot))
    bot.add_cog(OwnerNotificationCog(bot))