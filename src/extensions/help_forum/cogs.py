import discord
from discord.ext import commands

from .views import JumpView
from .exceptions import NotInHelpForum
from .settings import (HELP_FORUM_ID,
                       INITIAL_MESSAGE_EMBED_IMAGE_URL,
                       HELPER_ROLE_ID) 
from .checkers import (no_thread_solution_yet,
                       thread_owner_only)


class HelpCog(discord.Cog):
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

        embed = discord.Embed(
            title="Пост создан!",
            description=(
                "В скором времени на него дадут ответ, просим немного подождать.\n"
                "📝 Вы можете пометить ответ как решение нажав **ПКМ** на сообщение -> "
                f"\"Приложения\" -> \"{HelpCog.mark_as_answer.name}\""
            ),
            image=INITIAL_MESSAGE_EMBED_IMAGE_URL,
            color=0x4334eb,
        )

        await thread.send(embed=embed)

    @discord.message_command(name="Пометить как решение ✅")
    @no_thread_solution_yet()
    @thread_owner_only()
    async def mark_as_answer(self, ctx: discord.ApplicationContext, message: discord.Message):
        if message.author.bot:
            error_embed = discord.Embed(
                title="❌ Ошибка",
                description="Нельзя помечать ответ бота как решение вопроса"
            )
            return await ctx.respond(embed=error_embed)
        
        if message.author.id == ctx.author.id:
            # Ответил на свой же вопрос
            success_embed = discord.Embed(
                title="✅ Успешно",
                description=(
                    "Вы пометили свой ответ как решение вопроса.\n"
                    ""
                ),
                fields=[
                    discord.EmbedField(
                        name="Показать решение",
                        value=f"[Нажать сюда]({message.jump_url})"
                    )
                ]
            )

            await ctx.respond(embed=success_embed)
            await message.add_reaction("✅")
            starting_message = await anext(ctx.channel.history(
                after=ctx.channel.created_at,
                limit=1,
                oldest_first=True
            ))
            return await starting_message.edit(view=JumpView(message.jump_url))

        # Пометил как ответ сообщение другого пользователя. TODO
        await ctx.respond("Пометил, как ответ")
        await message.add_reaction("✅")

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