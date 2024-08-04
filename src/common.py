import discord


class CogWithBot(discord.Cog):
    def __init__(self, bot: discord.Bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot