import os
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from tradingview_ta import TA_Handler, Interval

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))

CHANNEL_USERNAME = "Mahmudsm1"
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1000000000000"))

TP1 = 50   # %
TP2 = 75
TP3 = 100
SL = -20

COINS_FILE = "coins.txt"

# ================== LOAD COINS ==================
def load_coins():
    if not os.path.exists(COINS_FILE):
        return []
    with open(COINS_FILE, "r") as f:
        return [c.strip().upper() for c in f if c.strip()]

COINS = load_coins()

# ================== HELPERS ==================
async def is_verified(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False


async def force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            "🔔 Join Channel",
            url=f"https://t.me/{CHANNEL_USERNAME}"
        )
    ]]
    await update.effective_message.reply_text(
        "🚫 *Join channel first kafin amfani da bot*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== SIGNAL LOGIC ==================
def analyze_coin(symbol: str):
    handler = TA_Handler(
        symbol=symbol,
        exchange="BINANCE",
        screener="crypto",
        interval=Interval.INTERVAL_1_HOUR
    )

    analysis = handler.get_analysis()
    summary = analysis.summary

    signal = summary["RECOMMENDATION"]
    price = analysis.indicators["close"]

    return signal, price

def build_signal_text(symbol, signal, price):
    tp1 = price * (1 + TP1 / 100)
    tp2 = price * (1 + TP2 / 100)
    tp3 = price * (1 + TP3 / 100)
    sl  = price * (1 + SL / 100)

    return f"""
🚨 *NEW SIGNAL*
*{symbol}* (1H)

📊 Signal: *{signal}*
💰 Entry: `{price:.4f}`

🎯 TP1: `{tp1:.4f}` (+{TP1}%)
🎯 TP2: `{tp2:.4f}` (+{TP2}%)
🎯 TP3: `{tp3:.4f}` (+{TP3}%)

🛑 SL: `{sl:.4f}` ({SL}%)

⚠️ Manage risk properly
"""

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_verified(user_id, context):
        await force_join(update, context)
        return

    keyboard = [
        [InlineKeyboardButton("🔍 Search Coin", callback_data="search")],
        [InlineKeyboardButton("📈 Coins List", callback_data="coins")]
    ]

    await update.message.reply_text(
        "🤖 *MahmudSM Trading Bot*\n\nZaɓi abinda kake so 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== CALLBACKS ==================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not await is_verified(user_id, context):
        await force_join(update, context)
        return

    if query.data == "search":
        await query.message.reply_text("✍️ Rubuta coin (misali: BTCUSDT)")

    elif query.data == "coins":
        text = "📈 *Available Coins*\n\n"
        for c in COINS[:50]:
            text += f"• {c}\n"
        await query.message.reply_text(text, parse_mode="Markdown")

# ================== SEARCH HANDLER ==================
async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_verified(user_id, context):
        await force_join(update, context)
        return

    symbol = update.message.text.upper()

    if symbol not in COINS:
        await update.message.reply_text("❌ Coin ba a whitelist ba")
        return

    try:
        signal, price = analyze_coin(symbol)
        text = build_signal_text(symbol, signal, price)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("⚠️ Error yayin analysis")

# ================== ADMIN ==================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("❌ Rubuta saƙo")
        return

    await update.message.reply_text("✅ Broadcast sent")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    app.run_polling()

if __name__ == "__main__":
    main()
