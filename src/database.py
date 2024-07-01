import bisect
import tortoise
import tortoise.fields

from enum import IntEnum
from utils import save_model_after


class User(tortoise.Model):
    EXP_TO_LVLUP = [5, 25, 50, 100, 175, 250, 500, 1000, 2500]
    class LevelChange(IntEnum):
        level_up = 1
        same = 2
        level_down = 3

    id = tortoise.fields.BigIntField(primary_key=True)
    discord_id = tortoise.fields.BigIntField()
    helper_reputation = tortoise.fields.IntField(default=0)
    helper_level = tortoise.fields.IntField(default=0)

    @save_model_after
    async def change_rep(self, amount: int) -> LevelChange:
        new_rep = self.helper_reputation + amount
        new_level = bisect.bisect_left(self.EXP_TO_LVLUP, new_rep)
        old_level = self.helper_level

        self.helper_reputation = new_rep
        self.helper_level = new_level

        if new_level > old_level:
            return self.LevelChange.level_up
        if new_level < old_level:
            return self.LevelChange.level_down

        return self.LevelChange.same

    async def set_rep(self, amount: int) -> LevelChange:
        to_add = amount - self.helper_reputation
        return await self.change_rep(to_add)
    
    def rep_until_next_level(self) -> int:
        required_rep = self.EXP_TO_LVLUP[self.helper_level]
        remaining_rep = required_rep - self.helper_reputation
        return remaining_rep


class TicketStatus(IntEnum):
    created = 0
    burning = 1
    resolved = 2


class TicketPriority(IntEnum):
    regular = 0
    golden = 1


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
