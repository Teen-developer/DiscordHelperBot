import discord.ui


class JumpView(discord.ui.View):
    def __init__(self, url: str, *args, **kwargs):
        redirectButton = discord.ui.Button(label="Перейти к ответу", url=url)
        super().__init__(redirectButton, *args, **kwargs)