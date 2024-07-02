import discord
import asyncio
from discord.ext import commands

from tortoise.transactions import in_transaction
from .views import JumpView
from .exceptions import NotInHelpForum, ThreadAlreadyAnswered, NotAThreadOwner
from .settings import (HELP_FORUM_ID,
                       INITIAL_MESSAGE_EMBED_IMAGE_URL,
                       HELPER_ROLE_ID, BOT_MESSAGE_CHANNEL_ID) 
from .checkers import (no_thread_solution_yet,
                       thread_owner_only)
from database import Ticket, User, UserLevelChange


class ReputationCog(discord.Cog):
    @discord.user_command(name="Показать карточку участника 🌟")
    async def reputation_check(self, ctx: discord.ApplicationContext, member: discord.Member):
        if member.bot:
            return await ctx.respond("Вы не можете проверить уровень репутации у бота", ephemeral=True)

        user = await (User
                      .get_or_none(id=member.id)
                      .only(
                          "helper_reputation", "helper_level",
                          "asked_questions", "resolved_questions"))
        
        if not user:
            return await ctx.respond("Этот пользователь больше не находится на этом сервере", ephemeral=True)

        embed = discord.Embed(
            title=f"Карточка участника",
            description=f"{member.mention}",
            fields=(
                discord.EmbedField(
                    name="🏆 Статистика",
                    value=(
                        f"Задано вопросов: **{user.asked_questions}**\n"
                        f"Отвечено на другие вопросы: **{user.resolved_questions}**"
                    ),
                ),
                discord.EmbedField(
                    name="🌟 Репутация помощника",
                    value=(
                        f"Уровень: **{user.helper_level}**\n"
                        f"Репутация: **{user.helper_reputation}**\n"
                        f"Следующий уровень через **{user.rep_until_next_level()}** очков"
                    ),
                ),
            ),
            color=member.color,
            thumbnail=member.display_avatar.url,
            footer=discord.EmbedFooter("*При выходе с сервера данные сбрасываются")
        )

        await ctx.respond(embed=embed, ephemeral=True)
    

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

        async with in_transaction():
            await Ticket.create(owner_id=thread.owner_id, thread_id=thread.id)
            user = await User.get(id=thread.owner_id).only("id", "asked_questions")
            user.asked_questions += 1
            await user.save(update_fields=["asked_questions"])

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
    async def on_member_join(self, member: discord.Member):
        await User.get_or_create(id=member.id)
    
    @discord.Cog.listener()
    async def on_raw_member_remove(payload: discord.RawMemberRemoveEvent):
        user = await User.get_or_none(id=payload.user.id)
        if user:
            await user.delete()

    @discord.Cog.listener()
    async def on_user_help_level_up(self, member: discord.Member, new_level: int):
        embed = discord.Embed(
            title="<:upvote:1154341416286298172> Уровень помощи вырос!",
            description=(
                f"{member.display_name}, поздравляю!\n"
                f"Теперь твой уровень поддержки: **{new_level}**!\n\n"
                "Я очень благодарен за твой труд.\nБлагодаря тебе всё больше "
                "и больше людей преодолевают трудности обучения и познают "
                "новые для себя темы.\nСпасибо 💙"
            ),
            thumbnail=member.display_avatar.url,
            color=0xFFD700
        )

        await self.bot.get_channel(BOT_MESSAGE_CHANNEL_ID).send(member.mention, embed=embed)
        

    @discord.message_command(name="Пометить как решение ✅")
    @no_thread_solution_yet()
    @thread_owner_only()
    async def mark_as_answer(self, ctx: discord.ApplicationContext, message: discord.Message):
        await ctx.defer()
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

            async with in_transaction():
                user = await User.get(id=message.author.id)
                user.resolved_questions += 1
                level_change, level = await user.change_rep(ticket.bounty)
                await user.save()
                if level_change == UserLevelChange.level_up:
                    ctx.bot.dispatch("user_help_level_up", message.author, level)

        data = await asyncio.gather(
            message.add_reaction("✅"),
            ctx.respond(embed=success_embed),
            anext(ctx.channel.history(
                after=ctx.channel.created_at,
                limit=1,
                oldest_first=True
            ))
        )

        starting_message = data[2]
        await starting_message.edit(view=JumpView(message.jump_url))

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
                "Этот вопрос уже был решён и поставить новое решение нельзя или он был задан до обновления бота",
                ephemeral=True
            )
        elif isinstance(error, NotAThreadOwner):
            await ctx.respond(
                "Это не ваш вопрос",
                ephemeral=True
            )