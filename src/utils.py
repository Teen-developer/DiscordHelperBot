from functools import wraps
from tortoise import Model
from tortoise.transactions import in_transaction


def save_model_after(f):
    "Сохраняет модель после изменения её внутренних параметров внутри транзакции"
    @wraps(f)
    async def wrapper(self: Model, *args, **kwargs):
        async with in_transaction():
            result = await f(self, *args, **kwargs)
            await self.save()
            return result
    return wrapper