import os
import discord
import asyncio
from tortoise import Tortoise
from database import User

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(debug_guilds=[696434683730329713], loop=loop, intents=intents)


@bot.event
async def on_ready():
    # async for member in bot.get_guild(696434683730329713).fetch_members(limit=None):
        # user = await User.get_or_create(id=member.id)

    member = await bot.get_guild(696434683730329713).fetch_member(327484242097340416)
    user = await User.get(id=327484242097340416)
    level_change, new_level = await user.change_rep(0)
    bot.dispatch("user_help_level_up", member, new_level)
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
