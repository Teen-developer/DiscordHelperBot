import discord
from settings import BOT_MESSAGE_CHANNEL_ID, HELP_FORUM_ID, BOOSTY_EMOJI, WELCOME_ROLE_ID
from utils import role_to_boosty_level
from database import User
from common import CogWithBot


class BoostyCog(CogWithBot):
    @discord.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        changed = set(after.roles) - set(before.roles)
        if len(changed) == 0:
            return
        
        role = changed.pop()
        boostyLevel = role_to_boosty_level(role)
        if boostyLevel == 0:
            return
        
        self.bot.dispatch("new_boosty_user", after, boostyLevel)

    @discord.Cog.listener(name="on_new_boosty_user")
    async def thank_new_subscriber(self, user: discord.Member, level: int):
        channel = self.bot.get_channel(BOT_MESSAGE_CHANNEL_ID)
        thanksEmbed = discord.Embed(
            title=f"{BOOSTY_EMOJI} {user.display_name} поддержал автора!",
            description=(
                f"❤️ Спасибо большое за активацию подписки **{level}** уровня\n\n"

                "Теперь ты можешь:\n"
                f"1. Создавать приоритетные вопросы в <#{HELP_FORUM_ID}>"
            ),
            color=0xf15f2c,
            thumbnail=user.display_avatar.url
        )

        await channel.send(
            user.mention,
            embed=thanksEmbed
        )


class WelcomeCog(CogWithBot):
    @discord.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await User.get_or_create(id=member.id)
        welcomeRole = member.guild.get_role(WELCOME_ROLE_ID)
        if welcomeRole is None:
            return print(
                "Не смог выдать приветственную роль пользователю "
                f"{member.display_name}. Роль не найдена"
            )

        await member.add_roles(welcomeRole, reason="Новый участник сервера")
        welcomeEmbed = discord.Embed(
            thumbnail=member.display_avatar.url,
            color=welcomeRole.color,
            title="У нас пополнение!",
            description=(
                f"Встречайте нового участника - **{member.display_name}**!\n"
                "Мы очень рады тебя видеть 💙\n\n"

                f"Задать вопрос по курсам пожно в <#{HELP_FORUM_ID}>"
            )
        )

        channel = self.bot.get_channel(BOT_MESSAGE_CHANNEL_ID)
        await channel.send(member.mention, embed=welcomeEmbed)
    
    @discord.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        user = await User.get_or_none(id=payload.user.id)
        if user:
            await user.delete()


class OwnerNotificationCog(CogWithBot):
    @discord.Cog.listener(name="on_new_boosty_user")
    async def new_boosty_sub(self, user: discord.Member, level: int):
        owner = await self.bot.get_or_fetch_user(self.bot.owner_id)
        if owner is None:
            return print("Couldn't send boosty notification to owner")

        await owner.send(
            f"**{user.display_name}** оформил подписку Boosty "
            f"**{level}** уровня на сервере **'{user.guild.name}'**"
        )
