import discord
import asyncio
from discord.ui import View, button, Modal, InputText
from settings import BOT_IMPORTANT_MESSAGES_CHANNEL
from database import Review, ReviewEntry
from datetime import datetime, timedelta
from discord.ext import commands
from utils import log_task_exceptions


class ReviewFormModal(Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(title="Запись на код-ревью", *args, **kwargs)
        self.add_item(InputText(
            label="Ссылка на репозиторий бота",
            placeholder="https://github.com/.../...",
            min_length=25,
            max_length=100
        ))

        self.add_item(InputText(
            label="Описание работы",
            placeholder="Что умеет бот, как им пользоваться",
            min_length=100,
            max_length=1000,
            style=discord.InputTextStyle.multiline,
        ))

        self.add_item(InputText(
            label="Умещается ли ваш бот в 550-650 строк кода?",
            placeholder="Если нет, перечислите модули бота на проверку",
            max_length=200,
        ))

        self.add_item(InputText(
            label="Ссылка на скрин архитектуры бота (желательно)",
            placeholder="https://imgur.com/ (фото загружать только на imgur!)",
            required=False,
            max_length=100,
        ))


    async def callback(self, interaction: discord.Interaction):
        current_review = await Review.get_active_or_none().only("id")
        if not current_review:
            return await interaction.respond("Сбор заявок уже закончился")

        git, description, modules, image = map(lambda x: x.value, self.children)
        await ReviewEntry.create(
            review=current_review,
            discord_id=interaction.user.id,
            description=description,
            github_url=git,
            architecture_image_url=image or None,
            check_modules=modules,
        )

        await interaction.respond("Вы успешно записаны на код-ревью!", ephemeral=True)


class ReviewFormView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, timeout=None)

    @button(label="Записаться", style=discord.ButtonStyle.green, emoji="📃", custom_id="review-button-add")
    async def appoint(self, button: discord.ui.Button, interaction: discord.Interaction):
        user_present = await Review.check_if_user_present(interaction.user.id)
        if user_present is None:
            return await interaction.respond("Сбор заявок уже завершён", ephemeral=True)

        if user_present is True:
            return await interaction.respond("Вы уже записались на это код-ревью", ephemeral=True)

        await interaction.response.send_modal(ReviewFormModal())

    @button(label="Отмена записи", style=discord.ButtonStyle.red, emoji="✖️", custom_id="review-button-cancel")
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        status = await Review.delete_entry_if_present(interaction.user.id)

        if status is None:
            return await interaction.respond("Сбор заявок завершён", ephemeral=True)

        if status is True:
            return await interaction.respond("Вы отменили запись", ephemeral=True)
        
        await interaction.respond("Вы ещё не записывались на это код-ревью", ephemeral=True)


class ReviewCog(discord.Cog):
    def __init__(self, bot: discord.Bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.on_ready_fired = False
        self.review_instance = None
        self.delete_task: asyncio.Task = None

    @log_task_exceptions
    async def close_review_on_timeout(self, review: Review, bot: discord.Bot):
        await asyncio.sleep(review.seconds_until_finished)
        await review.close(bot)
        self.review_instance = None

    review = discord.SlashCommandGroup(name="review", checks=[commands.is_owner()])

    @review.command()
    async def launch(self, ctx: discord.ApplicationContext, days: int):
        if self.review_instance:
            return await ctx.respond("Уже есть активное ревью!", ephemeral=True)

        await ctx.respond("Успешно создан", ephemeral=True)
        end_date = datetime.now() + timedelta(days=days)

        embed = discord.Embed(
            description=(
                "# Открыт приём заявок на код-ревью!\n"
                "В нём я буду проверять качество вашего дискорд кода, смотреть на его функционал, давать свои комментарии и советы. Всё мероприятие будет транслироваться на ютуб канал сервера:\n"
                "https://www.youtube.com/@teen-developer\n"

                "## Требования:\n"
                "1. Код должен быть выложен на GitHub в **публичном **репозитории\n"
                "2. На момент проверки бот должен **быть запущен** у вас на сервере\n"
                "3. Из кода должны быть удалены **все **чувствительные данные *(токены, пароли, адреса)*\n"
                "4. Необходимо подготовить **описание **бота (что он умеет делать, как им пользоваться)\n"
                "5. В идеале сделать изображение с архитектурой бота. Так проверка будет быстрее (Какие Cog'и/Extension'ы есть, какими сторонними api он пользуется, какая база данных и т.п)\n"
                "6. По размеру, код должен быть **максимум 550-650 строк**. В крайнем случае, вы сможете дополнительно указать, на какие модули бота мне нужно посмотреть, если кодовая база __превышает__ этот лимит\n"

                f"⭕ Приём заявок закончится через <t:{int(end_date.timestamp())}:R>"
            ),
            color=0x8ae378,
        )

        message = await ctx.bot.get_channel(BOT_IMPORTANT_MESSAGES_CHANNEL).send(
            ctx.guild.default_role,
            embed=embed,
            view=ReviewFormView()
        )

        self.review_instance = review = await Review.create(message_id=message.id, closed_at=end_date)
        if self.delete_task and not self.delete_task.done():
            self.delete_task.cancel()
        self.delete_task = asyncio.create_task(self.close_review_on_timeout(review, self.bot))

    @discord.Cog.listener()
    async def on_ready(self):
        if self.on_ready_fired:
            return
        self.on_ready_fired = True

        self.review_instance = await Review.get_active_or_none()
        if self.review_instance and self.delete_task is None:
            print("Хых. Словил бибу")
            self.delete_task = asyncio.create_task(
                self.close_review_on_timeout(self.review_instance, self.bot)
            )

    async def cog_command_error(self, ctx: discord.ApplicationContext, error: Exception) -> None:
        if isinstance(error, commands.NotOwner):
            return await ctx.respond("Вы не являетесь владельцем этого бота")
        raise error