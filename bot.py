import os
import asyncio
import random
import re

import aiohttp
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("Thiếu DISCORD_TOKEN trong Railway Variables!")

# =========================
# DISCORD
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# channel_id -> game
games = {}

# =========================
# JIKAN API
# =========================

JIKAN = "https://api.jikan.moe/v4"


async def get_random_character():
    """
    Lấy nhân vật ngẫu nhiên từ Jikan.
    """

    async with aiohttp.ClientSession() as session:

        for _ in range(5):

            try:
                async with session.get(
                    f"{JIKAN}/random/characters",
                    timeout=15
                ) as response:

                    if response.status != 200:
                        await asyncio.sleep(2)
                        continue

                    result = await response.json()

                    data = result.get("data")

                    if not data:
                        continue

                    name = data.get("name", "Unknown")

                    images = data.get("images", {})
                    jpg = images.get("jpg", {})

                    image = (
                        jpg.get("large_image_url")
                        or jpg.get("image_url")
                    )

                    if not image:
                        continue

                    about = data.get("about") or ""

                    nicknames = data.get("nicknames") or []

                    return {
                        "id": data.get("mal_id"),
                        "name": name,
                        "image": image,
                        "about": about,
                        "nicknames": nicknames
                    }

            except Exception as e:
                print("API error:", e)

                await asyncio.sleep(2)

    return None


# =========================
# CLEAN TEXT
# =========================

def clean_text(text):
    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9À-ỹ\s]",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================
# CHECK ANSWER
# =========================

def is_correct(character, guess):

    guess = clean_text(guess)

    name = clean_text(
        character["name"]
    )

    if guess == name:
        return True

    for nickname in character["nicknames"]:

        if guess == clean_text(nickname):
            return True

    return False


# =========================
# MAKE CLUES
# =========================

def make_clues(character):

    clues = []

    about = character["about"]

    if about:

        # Lấy vài câu đầu trong tiểu sử
        sentences = re.split(
            r"(?<=[.!?])\s+",
            about
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) > 25:

                clues.append(sentence)

            if len(clues) >= 3:
                break

    # Nếu API không có tiểu sử
    if not clues:

        clues.append(
            "Nhân vật này xuất hiện trong một anime/manga nổi tiếng."
        )

        clues.append(
            "Hãy quan sát thật kỹ hình ảnh để tìm manh mối."
        )

        clues.append(
            "Tên nhân vật có thể được tìm thấy trên MyAnimeList."
        )

    return clues


# =========================
# GAME
# =========================

class AnimeGame:

    def __init__(self, channel):

        self.channel = channel
        self.character = None

        self.clues = []
        self.clue_index = 0

        self.running = False
        self.winner = None

        self.task = None


    async def start(self):

        self.character = await get_random_character()

        if not self.character:
            await self.channel.send(
                "❌ Không thể lấy nhân vật lúc này. Thử lại sau!"
            )

            games.pop(
                self.channel.id,
                None
            )

            return

        self.clues = make_clues(
            self.character
        )

        self.clue_index = 1
        self.running = True

        embed = discord.Embed(
            title="🎌 ĐOÁN NHÂN VẬT ANIME",
            description=(
                "🖼️ **Nhìn hình ảnh và đoán nhân vật!**\n\n"

                f"💡 **Manh mối #1**\n"
                f"{self.clues[0]}\n\n"

                "⏱️ Thời gian: **60 giây**\n"
                "💬 Hãy gửi tên nhân vật vào chat!\n\n"

                "━━━━━━━━━━━━━━\n"
                "💡 `!clue` → thêm manh mối\n"
                "⏭️ `!skip` → bỏ qua"
            ),
            color=discord.Color.blurple()
        )

        embed.set_image(
            url=self.character["image"]
        )

        embed.set_footer(
            text="Anime Guess • Chúc may mắn!"
        )

        await self.channel.send(
            embed=embed
        )

        self.task = asyncio.create_task(
            self.timeout()
        )


    async def timeout(self):

        await asyncio.sleep(60)

        if not self.running:
            return

        self.running = False

        embed = discord.Embed(
            title="⏰ HẾT GIỜ!",
            description=(
                "Không ai đoán đúng.\n\n"

                f"🎯 Đáp án: **{self.character['name']}**\n\n"

                "Bạn có thể dùng `!start` để chơi tiếp."
            ),
            color=discord.Color.red()
        )

        embed.set_image(
            url=self.character["image"]
        )

        await self.channel.send(
            embed=embed
        )

        games.pop(
            self.channel.id,
            None
        )


# =========================
# READY
# =========================

@bot.event
async def on_ready():

    print(
        f"✅ Đăng nhập thành công: {bot.user}"
    )

    print(
        f"🆔 Bot ID: {bot.user.id}"
    )

    print(
        "🎌 Anime Guess Bot đang chạy!"
    )


# =========================
# START
# =========================

@bot.command()
async def start(ctx):

    if ctx.channel.id in games:

        await ctx.send(
            "⚠️ Kênh này đang có một ván!"
        )

        return

    game = AnimeGame(
        ctx.channel
    )

    games[
        ctx.channel.id
    ] = game

    await ctx.send(
        "🔎 Đang chọn một nhân vật anime..."
    )

    await game.start()


# =========================
# CLUE
# =========================

@bot.command()
async def clue(ctx):

    game = games.get(
        ctx.channel.id
    )

    if not game or not game.running:

        await ctx.send(
            "❌ Hiện không có ván chơi."
        )

        return

    if game.clue_index >= len(game.clues):

        await ctx.send(
            "💡 Đã hết manh mối!"
        )

        return

    clue_text = game.clues[
        game.clue_index
    ]

    number = game.clue_index + 1

    game.clue_index += 1

    embed = discord.Embed(
        title=f"💡 MANH MỐI #{number}",
        description=clue_text,
        color=discord.Color.gold()
    )

    await ctx.send(
        embed=embed
    )


# =========================
# SKIP
# =========================

@bot.command()
async def skip(ctx):

    game = games.get(
        ctx.channel.id
    )

    if not game or not game.running:

        await ctx.send(
            "❌ Không có ván chơi."
        )

        return

    game.running = False

    if game.task:
        game.task.cancel()

    embed = discord.Embed(
        title="⏭️ BỎ QUA",
        description=(
            f"🎯 Đáp án là:\n"
            f"**{game.character['name']}**\n\n"
            "Dùng `!start` để chơi tiếp."
        ),
        color=discord.Color.orange()
    )

    embed.set_image(
        url=game.character["image"]
    )

    await ctx.send(
        embed=embed
    )

    games.pop(
        ctx.channel.id,
        None
    )


# =========================
# STOP
# =========================

@bot.command()
@commands.has_permissions(
    manage_messages=True
)
async def stop(ctx):

    game = games.get(
        ctx.channel.id
    )

    if not game:

        await ctx.send(
            "❌ Không có game."
        )

        return

    game.running = False

    if game.task:
        game.task.cancel()

    games.pop(
        ctx.channel.id,
        None
    )

    await ctx.send(
        "🛑 Đã dừng game."
    )


# =========================
# HELP
# =========================

@bot.command()
async def animehelp(ctx):

    embed = discord.Embed(
        title="🎌 ANIME GUESS",
        description="Bot đoán nhân vật anime",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="🎮 !start",
        value="Bắt đầu game",
        inline=False
    )

    embed.add_field(
        name="💡 !clue",
        value="Nhận thêm manh mối",
        inline=False
    )

    embed.add_field(
        name="⏭️ !skip",
        value="Bỏ qua nhân vật",
        inline=False
    )

    embed.add_field(
        name="🛑 !stop",
        value="Dừng game",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# =========================
# MESSAGE / GUESS
# =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    game = games.get(
        message.channel.id
    )

    if game and game.running:

        if is_correct(
            game.character,
            message.content
        ):

            game.running = False
            game.winner = message.author

            if game.task:
                game.task.cancel()

            embed = discord.Embed(
                title="🎉 CHÍNH XÁC!",
                description=(
                    f"🏆 {message.author.mention}\n\n"

                    f"🎯 **{game.character['name']}**\n\n"

                    "⭐ Bạn đã đoán đúng!"
                ),
                color=discord.Color.green()
            )

            embed.set_image(
                url=game.character["image"]
            )

            await message.channel.send(
                embed=embed
            )

            games.pop(
                message.channel.id,
                None
            )

            return

    await bot.process_commands(
        message
    )


# =========================
# RUN
# =========================

bot.run(TOKEN)
