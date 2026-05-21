import discord
from discord.ext import commands


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


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── +giverole ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(manage_roles=True)
    async def giverole(self, ctx, member: discord.Member, role: discord.Role):
        """Give a role to a member. Usage: +giverole @user @role"""
        if role >= ctx.author.top_role and not ctx.author.guild_permissions.administrator:
            return await ctx.send("You can't give a role equal to or higher than your own.")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I can't assign that role — it's higher than my own role.")
        if role in member.roles:
            return await ctx.send(f"{member.mention} already has the {role.mention} role.")

        await member.add_roles(role, reason=f"Role given by {ctx.author}")

        embed = discord.Embed(title="✅ Role Given", color=role.color)
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Role", value=role.mention, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)

    # ── +removerole ──
    @commands.command()
    @has_mod_role()
    @commands.bot_has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, role: discord.Role):
        """Remove a role from a member. Usage: +removerole @user @role"""
        if role >= ctx.author.top_role and not ctx.author.guild_permissions.administrator:
            return await ctx.send("You can't remove a role equal to or higher than your own.")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I can't remove that role — it's higher than my own role.")
        if role not in member.roles:
            return await ctx.send(f"{member.mention} doesn't have the {role.mention} role.")

        await member.remove_roles(role, reason=f"Role removed by {ctx.author}")

        embed = discord.Embed(title="❌ Role Removed", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Role", value=role.mention, inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Roles(bot))
