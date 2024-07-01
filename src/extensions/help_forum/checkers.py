import discord
from discord.ext.commands import check
from .exceptions import NotAThreadOwner


def thread_owner_only():
    async def predicate(ctx: discord.ApplicationContext):
        if ctx.author.id != ctx.channel.owner_id:
            raise NotAThreadOwner
        return True
    return check(predicate)


def no_thread_solution_yet():
    async def predicate(ctx: discord.ApplicationContext):
        return True
    return check(predicate)