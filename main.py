import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6648308251  # canza zuwa ID naka
WHITELIST_FILE = "whitelist.txt"
VERIFIED_CHANNEL = "@YourChannel"  # channel verification placeholder

# ================== LOAD COINS ==================
def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    return []

COIN_WHITELIST = load_whitelist()

# ================== TP/SL ==================
TP_SL_DEFAULT = {"TP1": 50, "TP2": 75, "TP3": 100, "SL": 20}

def get_tp_sl(signal_type):
    """Dynamic TP/SL based on signal"""
    tp_sl = TP_SL_DEFAULT.copy()
    if signal_type == "SELL":
        tp_sl = {"TP1": 20, "TP2": 35, "TP3": 50, "SL": 10}
    elif signal_type == "BOTH":
        tp_sl = TP_SL_DEFAULT  # can adjust if needed
    return tp_sl

# ================== HELPERS ==================
def is_admin(user_id):
    return user_id == ADMIN_ID

def verify_channel(update: Update):
    # Placeholder logic for channel verification
    return True  # return False if user not verified

# ================== COMMAND HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Search Coin", callback_data="search")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to Trading Bot!", reply_markup=reply_markup)

async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Send the coin symbol to search:")

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not verify_channel(update):
        await update.message.reply_text("❌ Please join the verified channel first!")
        return

    coin = update.message.text.upper()
    if coin in COIN_WHITELIST:
        # Placeholder for real tradingview analysis
        signal = "BOTH"  # Could be BUY, SELL, BOTH based on real analysis
        tp_sl = get_tp_sl(signal)
        msg = (
            f"✅ Coin: {coin}\nSignal: {signal}\n"
            f"TP1: {tp_sl['TP1']}\nTP2: {tp_sl['TP2']}\nTP3: {tp_sl['TP3']}\nSL: {tp_sl['SL']}"
        )
    else:
        msg = f"❌ Coin {coin} is not in whitelist."
    await update.message.reply_text(msg)

# ================== ADMIN COMMANDS ==================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    text = " ".join(context.args)
    # Placeholder for sending broadcast to users
    await update.message.reply_text(f"Broadcasted message: {text}")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    await update.message.reply_text("User list placeholder")  # Replace with DB

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    await update.message.reply_text("Admin panel placeholder")

# ================== MAIN ==================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("admin", admin))
    
    # Callback queries
    app.add_handler(CallbackQueryHandler(search_callback, pattern="search"))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # Run polling safely
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())
