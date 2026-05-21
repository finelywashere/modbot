import discord
from discord.ext import commands
import asyncio


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


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}  # Shared via cog; automod cog reads from here too

    # ── +afk ──
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Set yourself as AFK. Usage: +afk [reason]"""
        self.afk_users[ctx.author.id] = {
            "reason": reason,
            "time": discord.utils.utcnow()
        }
        embed = discord.Embed(
            title="AFK Set",
            description=f"{ctx.author.mention} is now AFK: **{reason}**",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        try:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
        except discord.Forbidden:
            pass

    # ── +purge ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete messages. Usage: +purge <amount> (max 1000)"""
        if amount < 1:
            return await ctx.send("Amount must be at least 1.")
        if amount > 1000:
            return await ctx.send("Max purge amount is 1000.")

        await ctx.message.delete()

        deleted = 0
        while amount > 0:
            to_delete = min(amount, 100)
            purged = await ctx.channel.purge(limit=to_delete)
            deleted += len(purged)
            amount -= to_delete
            if len(purged) < to_delete:
                break

        confirm = await ctx.send(f"🗑️ Deleted **{deleted}** messages.")
        await asyncio.sleep(5)
        await confirm.delete()

    # ── on_message: AFK handler ──
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Remove AFK when user sends a message
        if message.author.id in self.afk_users:
            afk_data = self.afk_users.pop(message.author.id)
            elapsed = int((discord.utils.utcnow() - afk_data["time"]).total_seconds())
            embed = discord.Embed(
                description=f"Welcome back {message.author.mention}! You were AFK for **{format_duration(elapsed)}**.",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            try:
                if message.author.display_name.startswith("[AFK] "):
                    await message.author.edit(nick=message.author.display_name[6:] or None)
            except discord.Forbidden:
                pass

        # Notify if someone pings an AFK user
        for mentioned in message.mentions:
            if mentioned.id in self.afk_users:
                afk_data = self.afk_users[mentioned.id]
                embed = discord.Embed(
                    description=f"{mentioned.mention} is AFK: **{afk_data['reason']}** — <t:{int(afk_data['time'].timestamp())}:R>",
                    color=discord.Color.yellow()
                )
                await message.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
