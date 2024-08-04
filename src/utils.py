import discord
from settings import BOOSTY_LEVEL1_ROLE, BOOSTY_LEVEL2_ROLE, BOOSTY_LEVEL3_ROLE, BOOSTY_LEVEL4_ROLE
from functools import wraps
from tortoise import Model
from tortoise.transactions import in_transaction


def log_task_exceptions(f):
    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception as e:
            print("Asyncio task raised an exception:")
            print(e)
            print(type(e))
            raise e
    return wrapper


def save_model_after(f):
    "Сохраняет модель после изменения её внутренних параметров внутри транзакции"
    @wraps(f)
    async def wrapper(self: Model, *args, **kwargs):
        async with in_transaction():
            result = await f(self, *args, **kwargs)
            await self.save()
            return result
    return wrapper


def role_to_boosty_level(role: discord.Role) -> int:
    if role.id == BOOSTY_LEVEL4_ROLE:
        return 4
    if role.id == BOOSTY_LEVEL3_ROLE:
        return 3
    if role.id == BOOSTY_LEVEL2_ROLE:
        return 2
    if role.id == BOOSTY_LEVEL1_ROLE:
        return 1
    return 0


def get_boosty_level(user: discord.Member) -> int:
    for role in reversed(user.roles):
        if (level := role_to_boosty_level(role)) > 0:
            return level
    return 0