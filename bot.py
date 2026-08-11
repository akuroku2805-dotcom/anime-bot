import os
import discord
from discord.ext import commands
from datetime import datetime

TOKEN = os.getenv("TOKEN")

# ID kênh nhận báo cáo
LOG_CHANNEL_ID = 1536445926435065897

# Danh sách từ nhạy cảm
SENSITIVE_WORDS = [
    "dâm ib",
    "đụ má",
    "đụ mẹ",
    "địt mẹ",
    "đụ",
    "chịch",
]

# Role được miễn kiểm tra
STAFF_ROLES = [
    "Staff",
    "Admin",
    "Bạc xỉu",
   "Genesis",
   "Exodus"
  
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập: {bot.user}")
    print(f"ID: {bot.user.id}")


@bot.event
async def on_message(message):

    # Bỏ qua bot
    if message.author.bot:
        return

    # Bỏ qua DM
    if not message.guild:
        return

    # Kiểm tra role
    is_staff = any(
        role.name in STAFF_ROLES
        for role in message.author.roles
    )

    if is_staff:
        await bot.process_commands(message)
        return

    content = message.content.lower()

    # Tìm từ nhạy cảm
    found_words = [
        word for word in SENSITIVE_WORDS
        if word.lower() in content
    ]

    if found_words:

        # Xóa tin nhắn
        try:
            await message.delete()
        except discord.Forbidden:
            print("Bot không có quyền xóa tin nhắn.")

        # Cảnh báo người dùng
        try:
            warning = await message.channel.send(
                f"⚠️ {message.author.mention}, "
                f"tin nhắn của bạn chứa từ không được phép."
            )

            # Tự xóa cảnh báo sau 5 giây
            await warning.delete(delay=5)

        except discord.Forbidden:
            pass

        # Kênh log
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        if log_channel:

            embed = discord.Embed(
                title="🚨 CẢNH BÁO TỪ NHẠY CẢM",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="👤 Người dùng",
                value=f"{message.author.mention}\n"
                      f"`{message.author.id}`",
                inline=False
            )

            embed.add_field(
                name="📍 Kênh",
                value=message.channel.mention,
                inline=True
            )

            embed.add_field(
                name="⚠️ Từ phát hiện",
                value=", ".join(
                    f"`{word}`" for word in found_words
                ),
                inline=True
            )

            # Giới hạn nội dung log
            original_content = message.content

            if len(original_content) > 1000:
                original_content = original_content[:1000] + "..."

            embed.add_field(
                name="📝 Nội dung",
                value=f"```{original_content}```",
                inline=False
            )

            embed.set_footer(
                text=f"User ID: {message.author.id}"
            )

            await log_channel.send(embed=embed)

        return

    await bot.process_commands(message)


@bot.command()
@commands.has_permissions(administrator=True)
async def test(ctx):
    await ctx.send("✅ Bot cảnh báo từ nhạy cảm đang hoạt động!")


bot.run(TOKEN)
