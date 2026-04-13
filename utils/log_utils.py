"""
utils/log_utils.py — שליחת הודעות Log לחדר הדיסקורד
"""
import discord
from datetime import datetime, timezone
from config import LOG_CHANNEL_ID

# ── צבעים לפי קטגוריה ──────────────────────────────────────
LOG_COLORS = {
    "system":   0x5865F2,   # כחול Discord
    "player":   0x57F287,   # ירוק
    "battle":   0xED4245,   # אדום
    "catch":    0xFEE75C,   # צהוב
    "pvp":      0xFF6600,   # כתום
    "shop":     0x00BFFF,   # תכלת
    "admin":    0xEB459E,   # ורוד
    "error":    0xFF0000,   # אדום חזק
    "shutdown": 0x747F8D,   # אפור
}

# ── אימוג'י לפי קטגוריה ────────────────────────────────────
LOG_EMOJIS = {
    "system":   "🤖",
    "player":   "🆕",
    "battle":   "⚔️",
    "catch":    "🎣",
    "pvp":      "🥊",
    "shop":     "🛒",
    "admin":    "🛡️",
    "error":    "❌",
    "shutdown": "🔴",
}


async def send_log(
    bot: discord.Client,
    category: str,
    title: str,
    description: str = "",
    fields: list[tuple] = None,
    user: discord.Member | discord.User = None,
):
    """
    שולח הודעת Log לחדר ה-logs.

    Parameters
    ----------
    bot         : Discord bot instance
    category    : "system" | "player" | "battle" | "catch" | "pvp" | "shop" | "admin" | "error" | "shutdown"
    title       : כותרת ה-embed
    description : תיאור (אופציונלי)
    fields      : רשימת tuples (name, value, inline=True)
    user        : המשתמש שגרם לאירוע (אופציונלי)
    """
    if not LOG_CHANNEL_ID:
        return

    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    color = LOG_COLORS.get(category, 0x99AAB5)
    emoji = LOG_EMOJIS.get(category, "📋")
    now = datetime.now(timezone.utc)

    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=description or "",
        color=color,
        timestamp=now,
    )

    if user:
        embed.set_author(
            name=f"{user.display_name} ({user.id})",
            icon_url=user.display_avatar.url,
        )

    if fields:
        for field in fields:
            name, value = field[0], field[1]
            inline = field[2] if len(field) > 2 else True
            embed.add_field(name=name, value=str(value), inline=inline)

    embed.set_footer(text=f"Pokemon Bot Logs")

    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass  # הבוט אין גישה לערוץ — בשקט
