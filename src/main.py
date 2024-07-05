import os
import discord
import asyncio
from tortoise import Tortoise
from database import User

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(loop=loop, intents=intents)


@bot.event
async def on_ready():
    print("Bot is ready!")


@bot.listen("on_ready", once=True)
async def register_all_users():
    async for member in bot.get_guild(696434683730329713).fetch_members(limit=None):
        await User.get_or_create(id=member.id)
    print("All missing users registered successfully!")


async def main():
    bot.load_extension(name="extensions.help_forum.setup")
    bot.load_extension(name="extensions.code_review.setup")
    await Tortoise.init(
        db_url=(
            f"asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
            f"@postgres-db:5432/{os.getenv('POSTGRES_DB')}"),
        modules={"discord": ["database"]})
    await Tortoise.generate_schemas(safe=True)
    await bot.login(os.getenv("BOT_TOKEN"))
    await bot.connect(reconnect=True)


if __name__ == "__main__":
    loop.run_until_complete(main())
