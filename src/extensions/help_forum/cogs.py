import discord
from discord.ext import commands

from .views import JumpView
from .exceptions import NotInHelpForum, ThreadAlreadyAnswered, NotAThreadOwner
from .settings import (HELP_FORUM_ID,
                       INITIAL_MESSAGE_EMBED_IMAGE_URL,
                       HELPER_ROLE_ID, BOT_MESSAGE_CHANNEL_ID) 
from .checkers import (no_thread_solution_yet,
                       thread_owner_only)
from database import Ticket, User, UserLevelChange


class HelpCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    ticket_command = discord.SlashCommandGroup(
        name="ticket",
        checks=[commands.check_any(
            commands.has_role(HELPER_ROLE_ID),
            commands.is_owner()
        )]
    )

    @discord.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if not thread.parent_id == HELP_FORUM_ID:
            return

        await Ticket.create(owner_id=thread.owner_id, thread_id=thread.id)

        embed = discord.Embed(
            title=f"Вопрос создан!",
            description=(
                "В скором времени на него дадут ответ, просим немного подождать.\n"
                "📝 Вы можете пометить ответ как решение нажав **ПКМ** на сообщение -> "
                f"\"Приложения\" -> \"{HelpCog.mark_as_answer.name}\""
            ),
            image=INITIAL_MESSAGE_EMBED_IMAGE_URL,
            color=0x4334eb,
        )

        await thread.send(embed=embed)

    @discord.Cog.listener()
    async def on_user_help_level_up(self, member: discord.Member, new_level: int):
        embed = discord.Embed(
            title="🌟 Уровень помощи вырос!",
            description=(
                f"{member.display_name}, поздравляю!\n"
                f"Теперь твой уровень поддержки: **{new_level}**!\n\n"
                "Я очень благодарен за твой труд. Благодаря тебе всё больше "
                "и больше людей преодолевают трудности обучения и познают "
                "новые для себя темы. Спасибо 💙"
            ),
            color=0xFFD700
        )

        await self.bot.get_channel(BOT_MESSAGE_CHANNEL_ID).send(member.mention, embed=embed)
        

    @discord.message_command(name="Пометить как решение ✅")
    @no_thread_solution_yet()
    @thread_owner_only()
    async def mark_as_answer(self, ctx: discord.ApplicationContext, message: discord.Message):
        if message.author.bot:
            error_embed = discord.Embed(
                title="❌ Ошибка",
                description="Нельзя помечать ответ бота как решение вопроса",
            )
            return await ctx.respond(embed=error_embed, ephemeral=True)
        
        success_embed = discord.Embed(
            title="✅ Успешно",
            fields=[
                discord.EmbedField(
                    name="Показать решение",
                    value=f"[Нажать сюда]({message.jump_url})"
                )
            ]
        )

        ticket = await Ticket.resolve(thread_id=ctx.channel_id, helper_id=message.author.id)
        if message.author.id == ctx.author.id: # Ответил на свой же вопрос
            success_embed.description = "Вы пометили свой ответ как решение вопроса"
        else:
            success_embed.description = f"Вопрос решён пользователем {message.author.mention}"
            user = await User.get(id=message.author.id)
            level_change, level = await user.change_rep(ticket.bounty)
            if level_change == UserLevelChange.level_up:
                await ctx.bot.dispatch("user_help_level_up", message.author, level)

        await message.add_reaction("✅")
        await ctx.respond(embed=success_embed)
        starting_message = await anext(ctx.channel.history(
            after=ctx.channel.created_at,
            limit=1,
            oldest_first=True
        ))

        await starting_message.edit(view=JumpView(message.jump_url))

    @discord.user_command(name="Проверить уровень репутации 🌟")
    async def reputation_check(self, ctx: discord.ApplicationContext, member: discord.Member):
        user = await User.get(id=member.id).only("helper_reputation", "helper_level")

        embed = discord.Embed(
            title=f"❓ Уровень помощника "**{member.display_name}**"",
            description=(
                f"Пользователь имеет `{user.helper_level}` уровень\n"
                f"Репутация: {user.helper_reputation}\n"
                f"До следующего уровня: {user.rep_until_next_level()}"
            ),
            color=0x4334eb,
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @ticket_command.command(description="Переименовывает текущий вопрос")
    async def rename(self, ctx: discord.ApplicationContext, new_name: str):
        await ctx.channel.edit(name=new_name)
        await ctx.respond(f"Пользователь {ctx.author.mention} изменил название")

    @ticket_command.command(description="Закрывает текущий вопрос")
    async def archive(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Вопрос закрыт")
        await ctx.channel.archive(locked=True)
    
    @ticket_command.command(description="Открывает заного текущий вопрос")
    async def unarchive(self, ctx: discord.ApplicationContext):
        await ctx.channel.unarchive()
        await ctx.respond(f"Вопрос открыт")

    def cog_check(self, ctx: discord.ApplicationContext):
        if (
            ctx.channel.type != discord.ChannelType.public_thread or
            ctx.channel.parent_id != HELP_FORUM_ID
        ):
            raise NotInHelpForum
        return True
    
    async def cog_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, NotInHelpForum):
            await ctx.respond(
                f"Эта команда может быть использована только в <#{HELP_FORUM_ID}>",
                ephemeral=True
            )
        elif isinstance(error, commands.MissingRole):
            await ctx.respond(
                "Эту команду может вызывать только администратор "
                f"и люди с ролью <@&{error.missing_role}>",
                ephemeral=True
            )
        elif isinstance(error, commands.CheckAnyFailure):
            await ctx.respond(
                "У вас недостаточно разрешений на выполнение этой команды",
                ephemeral=True
            )
        elif isinstance(error, ThreadAlreadyAnswered):
            await ctx.respond(
                "Этот вопрос уже был решён и поставить новое решение нельзя",
                ephemeral=True
            )
        elif isinstance(error, NotAThreadOwner):
            await ctx.respond(
                "Это не ваш вопрос",
                ephemeral=True
            )