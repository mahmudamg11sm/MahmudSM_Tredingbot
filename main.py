import os
import asyncio
import logging
import nest_asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "SAKA_BOT_TOKEN_ANKA"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "123456789")  # saka telegram id naka
CHANNEL_USERNAME = "@Mahmudsm1"

BOT_NAME = "Dynamic Auto Signal Bot v13"

# ================= LOG =================
logging.basicConfig(level=logging.INFO)

# ================= DATA =================
COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT", "TRXUSDT",
    "SHIBUSDT", "LINKUSDT", "ATOMUSDT", "ETCUSDT", "FILUSDT", "APTUSDT",
    "NEARUSDT", "OPUSDT"
]

USERS = set()

# ================= HELPERS =================

def social_buttons():
    keyboard = [
        [InlineKeyboardButton("📢 Telegram", url="https://t.me/Mahmudsm1")],
        [InlineKeyboardButton("🐦 X (Twitter)", url="https://x.com/Mahmud_sm1")],
        [InlineKeyboardButton("📘 Facebook", url="https://www.facebook.com/profile.php?id=61580620438042")],
    ]
    return InlineKeyboardMarkup(keyboard)


def coins_keyboard():
    buttons = []
    row = []
    for c in COINS:
        row.append(InlineKeyboardButton(c.replace("USDT", ""), callback_data=f"coin:{c}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔍 Search Coin", callback_data="search")])
    return InlineKeyboardMarkup(buttons)


async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except:
        return False


# ================= SIGNAL =================

def get_signal(symbol: str):
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="crypto",
            exchange="BYBIT",
            interval=Interval.INTERVAL_15_MINUTES
        )
        analysis = handler.get_analysis()
        summary = analysis.summary

        return f"""
📊 *Signal for {symbol}*

🟢 Buy: {summary.get('BUY')}
🔴 Sell: {summary.get('SELL')}
⚪ Neutral: {summary.get('NEUTRAL')}

📈 Recommendation: *{summary.get('RECOMMENDATION')}*
"""
    except Exception as e:
        return f"❌ Ba a samu coin ba: {symbol}"


# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USERS.add(user.id)

    joined = await is_user_joined(update, context)
    if not joined:
        await update.message.reply_text(
            f"❗ Don amfani da bot, sai ka shiga channel ɗinmu:\n{CHANNEL_USERNAME}"
        )
        return

    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nZaɓi coin ko ka yi search:",
        reply_markup=coins_keyboard()
    )

    await update.message.reply_text(
        "Bi mu a shafukanmu 👇",
        reply_markup=social_buttons()
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "search":
        await query.message.reply_text("✍️ Rubuta sunan coin, misali: BTCUSDT ko ADAUSDT")
        return

    if data.startswith("coin:"):
        symbol = data.split(":")[1]
        text = get_signal(symbol)
        await query.message.reply_text(text, parse_mode="Markdown")
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        await update.message.reply_text(
            f"❗ Don amfani da bot, ka shiga channel ɗinmu:\n{CHANNEL_USERNAME}"
        )
        return

    text = update.message.text.upper().strip()

    if not text.endswith("USDT"):
        text = text + "USDT"

    await update.message.reply_text("⏳ Ana duba signal...")

    result = get_signal(text)
    await update.message.reply_text(result, parse_mode="Markdown")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Amfani: /broadcast sakonka")
        return

    msg = " ".join(context.args)

    count = 0
    for uid in USERS:
        try:
            await context.bot.send_message(uid, msg)
            count += 1
        except:
            pass

    await update.message.reply_text(f"✅ An tura wa mutane {count}")


# ================= MAIN =================

async def main():
    print(f"{BOT_NAME} yana gudana...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await app.run_polling()


# ================= START WITHOUT CRASH =================

if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
