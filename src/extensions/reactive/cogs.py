import discord
from settings import BOT_MESSAGE_CHANNEL_ID, HELP_FORUM_ID, BOOSTY_EMOJI
from utils import role_to_boosty_level


class BoostyCog(discord.Cog):
    def __init__(self, bot: discord.Bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @discord.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        changed = set(after.roles) - set(before.roles)
        if len(changed) == 0:
            return
        
        role = changed.pop()
        boostyLevel = role_to_boosty_level(role)
        if boostyLevel == 0:
            return
        
        channel = self.bot.get_channel(BOT_MESSAGE_CHANNEL_ID)
        thanksEmbed = discord.Embed(
            title=f"{BOOSTY_EMOJI} {after.display_name} поддержал автора!",
            description=(
                f"❤️ Спасибо большое за активацию подписки **{boostyLevel}** уровня\n\n"

                "Теперь ты можешь:\n"
                f"1. Создавать приоритетные вопросы в <#{HELP_FORUM_ID}>"
            ),
            color=0xf15f2c,
            thumbnail=after.display_avatar.url
        )

        await channel.send(
            after.mention,
            embed=thanksEmbed
        )

        owner = await self.bot.get_or_fetch_user(self.bot.owner_id)
        if owner is None:
            return print("Couldn't send boosty notification to owner")
        
        await owner.send(
            f"**{after.display_name}** оформил подписку Boosty "
            f"**{boostyLevel}** уровня на сервере **'{after.guild.name}'**"
        )