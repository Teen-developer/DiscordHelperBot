import bisect
import discord
import tortoise
import tortoise.fields

from enum import IntEnum
from datetime import datetime
from typing import Optional
from settings import BOT_IMPORTANT_MESSAGES_CHANNEL


class TicketStatus(IntEnum):
    created = 0
    burning = 1
    resolved = 2


class TicketPriority(IntEnum):
    regular = 0
    golden = 1


class UserLevelChange(IntEnum):
    level_up = -1
    same = 0
    level_down = 1


class Review(tortoise.Model):
    id = tortoise.fields.IntField(primary_key=True)
    started_at = tortoise.fields.DatetimeField(auto_now_add=True)
    closed_at = tortoise.fields.DatetimeField()
    message_id = tortoise.fields.BigIntField()

    @classmethod
    def get_active_or_none(cls, **kwargs):
        current_time = datetime.now()
        return cls.get_or_none(started_at__lte=current_time, closed_at__gte=current_time, **kwargs)

    @classmethod
    async def check_if_user_present(cls, discord_id: int) -> Optional[bool]:
        """
            Проверяет, записан ли пользователь на код-ревью или нет.
            Возвращает `None` если нет сбора заявок или `bool`, обозначающий
            наличие заявки от пользователя, в противном случае
        """
        review = await cls.get_active_or_none().prefetch_related("entries")
        if not review:
            return None
        
        for entr in review.entries:
            if entr.discord_id == discord_id:
                return True
        
        return False

    @classmethod
    async def delete_entry_if_present(cls, discord_id: int) -> Optional[bool]:
        """
            Удаляет запись участника на код-ревью по `discord_id`.
            Возвращает `None` если нет сбора заявок. Иначе `bool` - статус операции
        """
        review = await cls.get_active_or_none().prefetch_related("entries")

        if not review:
            return None

        for entry in review.entries:
            if entry.discord_id == discord_id:
                await entry.delete()
                return True

        return False

    @property
    def seconds_until_finished(self):
        current_time = datetime.now().astimezone()
        return max((self.closed_at - current_time).total_seconds(), 0)
    
    async def close(self, bot: discord.Bot):
        participants = await self.entries.all()
        channel = (
            bot.get_channel(BOT_IMPORTANT_MESSAGES_CHANNEL) or
            await bot.fetch_channel(BOT_IMPORTANT_MESSAGES_CHANNEL)
        )

        message = await channel.fetch_message(self.message_id)
        await message.edit(view=None)
        if participants:
            users_string = "\n".join(f"<@{user.discord_id}>" for user in participants)
            await message.reply(
                content=(
                    "## Приём заявок на код-ревью завершён!\n"
                    "📃Список участвующих:\n"
                    f'{users_string}\n'
                    "В этот канал скоро придёт информация со временем начала стрима =)"
                )
            )
        else:
            await message.reply(
                "Код-ревью отменено, так как никто на него не записался. Очень жаль 😢"
            )


class ReviewEntry(tortoise.Model):
    review = tortoise.fields.ForeignKeyField("discord.Review",
                                             related_name="entries")
    discord_id = tortoise.fields.BigIntField()
    description = tortoise.fields.CharField(max_length=1000)
    github_url = tortoise.fields.CharField(max_length=100)
    architecture_image_url = tortoise.fields.CharField(max_length=100, null=True)
    check_modules = tortoise.fields.CharField(max_length=200)


class User(tortoise.Model):
    EXP_TO_LVLUP = [5, 25, 50, 100, 175, 250, 500, 1000, 2500]

    id = tortoise.fields.BigIntField(primary_key=True)
    helper_reputation = tortoise.fields.IntField(default=0)
    helper_level = tortoise.fields.IntField(default=0)
    asked_questions = tortoise.fields.IntField(default=0)
    resolved_questions = tortoise.fields.IntField(default=0)

    async def change_rep(self, amount: int) -> tuple[UserLevelChange, int]:
        new_rep = self.helper_reputation + amount
        new_level = bisect.bisect_right(self.EXP_TO_LVLUP, new_rep)
        old_level = self.helper_level

        self.helper_reputation = new_rep
        self.helper_level = new_level

        if new_level > old_level:
            return UserLevelChange.level_up, new_level
        if new_level < old_level:
            return UserLevelChange.level_down, new_level

        return UserLevelChange.same, new_level

    async def set_rep(self, amount: int) -> tuple[UserLevelChange, int]:
        to_add = amount - self.helper_reputation
        return await self.change_rep(to_add)
    
    def rep_until_next_level(self) -> int:
        required_rep = self.EXP_TO_LVLUP[self.helper_level]
        remaining_rep = required_rep - self.helper_reputation
        return remaining_rep
    
    def __str__(self):
        return f"<User: {self.id}>"


class Ticket(tortoise.Model):
    id = tortoise.fields.IntField(primary_key=True)
    owner = tortoise.fields.ForeignKeyField("discord.User",
                                            related_name="created_tickets")
    helper = tortoise.fields.ForeignKeyField("discord.User",
                                             related_name="resolved_tickets",
                                             null=True)
    bounty = tortoise.fields.IntField(default=5)
    thread_id = tortoise.fields.BigIntField(unique=True)
    status = tortoise.fields.IntEnumField(TicketStatus, default=TicketStatus.created)
    priority = tortoise.fields.IntEnumField(TicketPriority, default=TicketPriority.regular)
    created_at = tortoise.fields.DatetimeField(auto_now_add=True)
    resolved_at = tortoise.fields.DatetimeField(null=True)

    @classmethod
    async def resolve(cls, thread_id: int, helper_id: int):
        ticket = await cls.get(thread_id=thread_id)
        ticket.resolved_at = datetime.now()
        ticket.status = TicketStatus.resolved
        ticket.helper_id = helper_id
        await ticket.save()
        return ticket