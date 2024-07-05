import discord
from .cogs import ReviewCog, ReviewFormView


def setup(bot: discord.Bot):
    bot.add_cog(ReviewCog(bot))
    bot.add_view(ReviewFormView())
