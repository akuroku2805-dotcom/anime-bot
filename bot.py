import os
import re
import discord
from discord.ext import commands
from datetime import datetime, timezone

TOKEN = os.getenv("TOKEN")

# ID kênh nhận báo cáo
LOG_CHANNEL_ID = 1537485970260234332

# Danh sách từ nhạy cảm
SENSITIVE_WORDS = [
    "dâm ib",
    "đụ má",
    "đụ mẹ",
    "địt mẹ",
    "đụ",
    "chịch",
   "dâm",
   "địt",
   "sex",
  "cặc",
  "lồn",
  "bú cặc",
  "bú lồn",
]

# Role được miễn kiểm tra
STAFF_ROLES = [
    "Staff",
    "Admin",
    "Bạc xỉu",
    "Genesis",
    "Exodus"
]

# Regex:
# - Không bắt "đụ" trong "đụng"
# - Không bắt "đụ" trong "đụt"
# - Vẫn bắt "đụ" khi đứng riêng
SENSITIVE_PATTERN = re.compile(
    r"(?<!\w)(?:" +
    "|".join(
        re.escape(word)
        for word in sorted(SENSITIVE_WORDS, key=len, reverse=True)
    ) +
    r")(?!\w)",
    re.IGNORECASE
)


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

    # =========================
    # KIỂM TRA TỪ NHẠY CẢM
    # =========================

    matches = SENSITIVE_PATTERN.findall(message.content)

    # Loại bỏ từ trùng nhau
    found_words = list(dict.fromkeys(
        match.lower() for match in matches
    ))

    if found_words:

        # Xóa tin nhắn
        try:
            await message.delete()
        except discord.Forbidden:
            print("❌ Bot không có quyền xóa tin nhắn.")
        except discord.NotFound:
            pass

        # Cảnh báo người dùng
        try:
            warning = await message.channel.send(
                f"⚠️ {message.author.mention}, "
                f"tin nhắn của bạn chứa từ không được phép."
            )

            # Tự xóa sau 5 giây
            await warning.delete(delay=5)

        except discord.Forbidden:
            pass

        # =========================
        # GỬI LOG
        # =========================

        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        if log_channel:

            embed = discord.Embed(
                title="🚨 CẢNH BÁO TỪ NHẠY CẢM",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="👤 Người dùng",
                value=(
                    f"{message.author.mention}\n"
                    f"`{message.author.id}`"
                ),
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

            # Nội dung tin nhắn
            original_content = message.content

            # Giới hạn Discord embed field
            if len(original_content) > 1000:
                original_content = original_content[:1000] + "..."

            # Tránh lỗi nếu nội dung chứa ```
            original_content = original_content.replace("```", "'''")

            embed.add_field(
                name="📝 Nội dung",
                value=f"```{original_content}```",
                inline=False
            )

            embed.set_footer(
                text=f"User ID: {message.author.id}"
            )

            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                print("❌ Bot không có quyền gửi log.")

        return

    # Xử lý command
    await bot.process_commands(message)


@bot.command()
@commands.has_permissions(administrator=True)
async def test(ctx):
    await ctx.send(
        "✅ Bot cảnh báo từ nhạy cảm đang hoạt động!"
    )


@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Bạn không có quyền sử dụng lệnh này.",
            delete_after=5
        )


if not TOKEN:
    print("❌ Không tìm thấy TOKEN trong biến môi trường!")

else:
    bot.run(TOKEN)
