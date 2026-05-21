import discord
from discord.ext import commands
from datetime import timedelta
import asyncio
import re
from typing import Optional


def parse_duration(duration_str):
    pattern = r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration_str.strip())
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (int(v or 0) for v in match.groups())
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def format_duration(seconds):
    parts = []
    for unit, label in [(86400, "day"), (3600, "hour"), (60, "minute"), (1, "second")]:
        val, seconds = divmod(seconds, unit)
        if val:
            parts.append(f"{val} {label}{'s' if val != 1 else ''}")
    return ", ".join(parts) if parts else "0 seconds"


def is_mod(member):
    if member.guild_permissions.administrator:
        return True
    mod_roles = {"moderator", "mod", "admin"}
    return any(r.name.lower() in mod_roles for r in member.roles)


def has_mod_role():
    async def predicate(ctx):
        if is_mod(ctx.author):
            return True
        raise commands.MissingPermissions(["moderator"])
    return commands.check(predicate)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── +ban ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, duration: Optional[str] = None, *, reason: str = "No reason provided."):
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

        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=duration_text, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)

        if seconds:
            await asyncio.sleep(seconds)
            try:
                await ctx.guild.unban(member, reason="Temporary ban expired.")
                await ctx.send(f"✅ {member}'s ban has expired and they have been unbanned.")
            except discord.NotFound:
                pass

    # ── +kick ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided."):
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

        embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)

    # ── +mute ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason provided."):
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
        if seconds > 28 * 86400:
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

        embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_gray())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Duration", value=duration_text, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:R>", inline=False)
        await ctx.send(embed=embed)

    # ── +unmute ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "Mute removed by moderator."):
        """Remove a timeout. Usage: +unmute @user [reason]"""
        if not member.is_timed_out():
            return await ctx.send(f"{member.mention} is not currently muted.")

        await member.timeout(None, reason=f"[{ctx.author}] {reason}")

        embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)

    # ── +unban ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason: str = "Ban removed by moderator."):
        """Unban a user by ID. Usage: +unban <user_id> [reason]"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"[{ctx.author}] {reason}")
            embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green())
            embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
            await ctx.send(embed=embed)
        except discord.NotFound:
            await ctx.send("That user is not banned or doesn't exist.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
