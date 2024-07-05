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