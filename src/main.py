import os
import discord
import asyncio
from tortoise import Tortoise
from database import User

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
bot = discord.Bot(debug_guilds=[696434683730329713], loop=loop)


@bot.event
async def on_ready():
    print("Bot is ready!")


async def main():
    bot.load_extension(name="extensions.help_forum.setup")
    await Tortoise.init(
        db_url=(
            f"asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
            f"@postgres_db:5432/{os.getenv('POSTGRES_DB')}"),
        modules={"discord": ["database"]})
    await Tortoise.generate_schemas(safe=True)
    await bot.login(os.getenv("BOT_TOKEN"))
    await bot.connect(reconnect=True)


if __name__ == "__main__":
    loop.run_until_complete(main())
