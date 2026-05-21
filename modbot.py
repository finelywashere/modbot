import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
import re
from typing import Optional

# ──────────────────────────────────────────
#  Bot setup
# ──────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)


# ──────────────────────────────────────────
#  Helper: parse duration strings
#  Accepts: 10s, 5m, 2h, 1d  (or combos: 1h30m)
# ──────────────────────────────────────────
def parse_duration(duration_str):
    """Return total seconds from a duration string, or None if invalid."""
    pattern = r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration_str.strip())
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (int(v or 0) for v in match.groups())
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def format_duration(seconds):
    """Turn seconds back into a human-readable string."""
    parts = []
    for unit, label in [(86400, "day"), (3600, "hour"), (60, "minute"), (1, "second")]:
        val, seconds = divmod(seconds, unit)
        if val:
            parts.append(f"{val} {label}{'s' if val != 1 else ''}")
    return ", ".join(parts) if parts else "0 seconds"


# ──────────────────────────────────────────
#  Permission check decorator
# ──────────────────────────────────────────
def has_mod_role():
    """Allow administrators OR users with a role named Moderator / Mod."""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        mod_roles = {"moderator", "mod", "admin"}
        if any(r.name.lower() in mod_roles for r in ctx.author.roles):
            return True
        raise commands.MissingPermissions(["moderator"])
    return commands.check(predicate)


# ──────────────────────────────────────────
#  Events
# ──────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    print(f"Prefix: +   |   Servers: {len(bot.guilds)}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument. See `+help {ctx.command}`.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found. Mention them or use their ID.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"I'm missing permissions: `{', '.join(error.missing_permissions)}`")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use this command.")
    else:
        await ctx.send(f"Unexpected error: `{error}`")
        raise error


# ──────────────────────────────────────────
#  +ban  @member [duration] [reason]
# ──────────────────────────────────────────
@bot.command()
@has_mod_role()
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, duration: Optional[str] = None, *, reason: str = "No reason provided."):
    """Ban a member. Usage: +ban @user [duration] [reason]"""
    if member == ctx.author:
        return await ctx.send("You can't ban yourself.")
    if member.top_role >= ctx.author.top_role and not ctx.author.guild_permissions.administrator:
        return await ctx.send("You can't ban someone with an equal or higher role.")

    seconds = None
    if duration:
        seconds = parse_duration(duration)
        if seconds is None:
            reason = f"{duration} {reason}".strip()

    duration_text = format_duration(seconds) if seconds else "Permanent"

    try:
        embed = discord.Embed(title="You have been banned", color=discord.Color.red())
        embed.add_field(name="Server", value=ctx.guild.name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=duration_text, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await member.send(embed=embed)
    except discord.Forbidden:
        pass

    await member.ban(reason=f"[{ctx.author}] {reason}")

    embed = discord.Embed(title="Member Banned", color=discord.Color.red())
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Duration", value=duration_text, inline=False)
    embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
    await ctx.send(embed=embed)

    if seconds:
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason="Temporary ban expired.")
            await ctx.send(f"{member} ban has expired and they have been unbanned.")
        except discord.NotFound:
            pass


# ──────────────────────────────────────────
#  +kick  @member [reason]
# ──────────────────────────────────────────
@bot.command()
@has_mod_role()
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    """Kick a member. Usage: +kick @user [reason]"""
    if member == ctx.author:
        return await ctx.send("You can't kick yourself.")
    if member.top_role >= ctx.author.top_role and not ctx.author.guild_permissions.administrator:
        return await ctx.send("You can't kick someone with an equal or higher role.")

    try:
        embed = discord.Embed(title="You have been kicked", color=discord.Color.orange())
        embed.add_field(name="Server", value=ctx.guild.name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await member.send(embed=embed)
    except discord.Forbidden:
        pass

    await member.kick(reason=f"[{ctx.author}] {reason}")

    embed = discord.Embed(title="Member Kicked", color=discord.Color.orange())
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
    await ctx.send(embed=embed)


# ──────────────────────────────────────────
#  +mute  @member <duration> [reason]
# ──────────────────────────────────────────
@bot.command()
@has_mod_role()
@commands.bot_has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason provided."):
    """Timeout a member. Usage: +mute @user <duration> [reason]"""
    if member == ctx.author:
        return await ctx.send("You can't mute yourself.")
    if member.top_role >= ctx.author.top_role and not ctx.author.guild_permissions.administrator:
        return await ctx.send("You can't mute someone with an equal or higher role.")

    if not duration:
        return await ctx.send("Please provide a duration. Example: `+mute @user 10m Spamming`")

    seconds = parse_duration(duration)
    if not seconds:
        return await ctx.send("Invalid duration. Examples: `10m`, `2h`, `1d30m`")

    max_seconds = 28 * 86400
    if seconds > max_seconds:
        return await ctx.send("Max mute duration is 28 days (Discord limit).")

    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    await member.timeout(until, reason=f"[{ctx.author}] {reason}")

    duration_text = format_duration(seconds)

    try:
        embed = discord.Embed(title="You have been muted", color=discord.Color.dark_gray())
        embed.add_field(name="Server", value=ctx.guild.name, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=duration_text, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await member.send(embed=embed)
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="Member Muted", color=discord.Color.dark_gray())
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Duration", value=duration_text, inline=False)
    embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
    embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:R>", inline=False)
    await ctx.send(embed=embed)


# ──────────────────────────────────────────
#  +unmute  @member
# ──────────────────────────────────────────
@bot.command()
@has_mod_role()
@commands.bot_has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member, *, reason: str = "Mute removed by moderator."):
    """Remove a timeout. Usage: +unmute @user [reason]"""
    if not member.is_timed_out():
        return await ctx.send(f"{member.mention} is not currently muted.")

    await member.timeout(None, reason=f"[{ctx.author}] {reason}")

    embed = discord.Embed(title="Member Unmuted", color=discord.Color.green())
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
    await ctx.send(embed=embed)


# ──────────────────────────────────────────
#  +unban  user_id [reason]
# ──────────────────────────────────────────
@bot.command()
@has_mod_role()
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason: str = "Ban removed by moderator."):
    """Unban a user by ID. Usage: +unban <user_id> [reason]"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"[{ctx.author}] {reason}")

        embed = discord.Embed(title="Member Unbanned", color=discord.Color.green())
        embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("That user is not banned or doesn't exist.")


# ──────────────────────────────────────────
#  Run
# ──────────────────────────────────────────
import os
bot.run(os.environ["TOKEN"])
