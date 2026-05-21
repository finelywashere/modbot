import discord
from discord.ext import commands
from datetime import timedelta
import asyncio
import re
import time
from collections import defaultdict


NSFW_KEYWORDS = [
    "porn", "pornhub", "xvideos", "xnxx", "onlyfans", "nsfw",
    "nude", "nudes", "naked", "sex", "hentai", "xxx", "cum",
    "dick", "pussy", "cock", "boobs", "tits", "ass", "anal",
    "blowjob", "handjob", "masturbat", "orgasm", "erotic",
    "fetish", "bdsm", "rape", "molest", "horny", "slut", "whore"
]

NSFW_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in NSFW_KEYWORDS) + r')\b',
    re.IGNORECASE
)

SPAM_LIMIT = 10      # messages
SPAM_WINDOW = 3      # seconds
SPAM_MUTE_DURATION = 3600  # 1 hour


def is_mod(member):
    if member.guild_permissions.administrator:
        return True
    mod_roles = {"moderator", "mod", "admin"}
    return any(r.name.lower() in mod_roles for r in member.roles)


class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = defaultdict(list)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Mods/admins are exempt
        if is_mod(message.author):
            return

        # ── NSFW filter ──
        if NSFW_PATTERN.search(message.content):
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            warn = await message.channel.send(
                f"🚫 {message.author.mention} NSFW content is not allowed here."
            )
            await asyncio.sleep(5)
            try:
                await warn.delete()
            except discord.NotFound:
                pass
            return

        # ── Spam filter ──
        now = time.time()
        uid = message.author.id
        self.spam_tracker[uid] = [t for t in self.spam_tracker[uid] if now - t < SPAM_WINDOW]
        self.spam_tracker[uid].append(now)

        if len(self.spam_tracker[uid]) > SPAM_LIMIT:
            self.spam_tracker[uid].clear()
            until = discord.utils.utcnow() + timedelta(seconds=SPAM_MUTE_DURATION)
            try:
                await message.author.timeout(until, reason="Automod: Spamming")
                embed = discord.Embed(
                    title="🔇 Automod — Spam Detected",
                    description=f"{message.author.mention} has been muted for **1 hour** for spamming.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(Automod(bot))
