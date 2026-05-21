import discord
from discord.ext import commands
import os
import asyncio

# ──────────────────────────────────────────
#  Bot setup
# ──────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

COGS = [
    "cogs.moderation",
    "cogs.utility",
    "cogs.automod",
    "cogs.roles",
]


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    print(f"Prefix: +   |   Servers: {len(bot.guilds)}")
    print(f"Loaded cogs: {', '.join(COGS)}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument. See `+help {ctx.command}`.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found. Mention them or use their ID.")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("Role not found. Mention it or check the name.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"I'm missing permissions: `{', '.join(error.missing_permissions)}`")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Silently ignore unknown commands
    else:
        await ctx.send(f"Unexpected error: `{error}`")
        raise error


# ──────────────────────────────────────────
#  +reload <cog>  (owner only)
# ──────────────────────────────────────────
@bot.command()
@commands.is_owner()
async def reload(ctx, cog: str):
    """Reload a cog. Usage: +reload moderation"""
    try:
        await bot.reload_extension(f"cogs.{cog}")
        await ctx.send(f"✅ Reloaded `cogs.{cog}`")
    except Exception as e:
        await ctx.send(f"❌ Failed to reload `cogs.{cog}`: `{e}`")


@bot.command()
@commands.is_owner()
async def reloadall(ctx):
    """Reload all cogs."""
    results = []
    for cog in COGS:
        try:
            await bot.reload_extension(cog)
            results.append(f"✅ {cog}")
        except Exception as e:
            results.append(f"❌ {cog}: {e}")
    await ctx.send("\n".join(results))


# ──────────────────────────────────────────
#  Load cogs and run
# ──────────────────────────────────────────
async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"  ✅ Loaded {cog}")
            except Exception as e:
                print(f"  ❌ Failed to load {cog}: {e}")
        await bot.start(os.environ["TOKEN"])

asyncio.run(main())
