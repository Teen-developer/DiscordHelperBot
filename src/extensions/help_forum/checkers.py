import discord
from discord.ext.commands import check
from .exceptions import NotAThreadOwner, ThreadAlreadyAnswered
from database import Ticket, TicketStatus


def thread_owner_only():
    async def predicate(ctx: discord.ApplicationContext):
        if ctx.author.id != ctx.channel.owner_id:
            raise NotAThreadOwner
        return True
    return check(predicate)


def no_thread_solution_yet():
    async def predicate(ctx: discord.ApplicationContext):
        ticket = await Ticket.get_or_none(thread_id=ctx.channel_id).only("status")
        if not ticket or ticket.status == TicketStatus.resolved:
            raise ThreadAlreadyAnswered
        return True
    return check(predicate)