from discord.ext.commands import CheckFailure


class NotInHelpForum(CheckFailure):
    pass


class NotAThreadOwner(CheckFailure):
    pass

