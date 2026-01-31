import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
CHANNEL_USERNAME = "@Mahmudsm1"
COIN_WHITELIST_FILE = "coins.txt"

TP1_PERCENT = 50
TP2_PERCENT = 75
TP3_PERCENT = 100
SL_PERCENT = 20

# Load coin whitelist
with open(COIN_WHITELIST_FILE, "r") as f:
    COIN_WHITELIST = [line.strip().upper() for line in f.readlines()]

# ================= HELPERS =================
async def check_channel_join(update: Update) -> bool:
    try:
        member = await update.effective_chat.get_member(CHANNEL_USERNAME)
        return member.status not in ["left", "kicked"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await check_channel_join(update)
    if not joined:
        keyboard = [[InlineKeyboardButton("Join channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        await update.message.reply_text("Join channel first:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = [
        [InlineKeyboardButton("Search Coin 🔍", callback_data="search_coin")],
        [InlineKeyboardButton("My Signals 🔔", callback_data="my_signals")]
    ]
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return
    keyboard = [
        [InlineKeyboardButton("Broadcast Message", callback_data="broadcast")],
        [InlineKeyboardButton("Users List", callback_data="users")],
    ]
    await update.message.reply_text("Admin Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "search_coin":
        await query.edit_message_text("Send me the coin symbol to search:")
    elif query.data == "my_signals":
        await query.edit_message_text("Your active signals will appear here.")
    elif query.data == "broadcast":
        await query.edit_message_text("Send the broadcast message:")
    elif query.data == "users":
        await query.edit_message_text("List of users (placeholder)")

async def signal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.upper()
    if msg not in COIN_WHITELIST:
        await update.message.reply_text("Coin not in whitelist.")
        return
    # Simulated signal
    tp_hit = TP1_PERCENT  # Example: you can compute real signal % here
    sl_hit = SL_PERCENT
    keyboard = [[InlineKeyboardButton("View Signal", callback_data="my_signals")]]
    await update.message.reply_text(f"Signal received!\nTP1: +{TP1_PERCENT}%\nTP2: +{TP2_PERCENT}%\nTP3: +{TP3_PERCENT}%\nSL: -{SL_PERCENT}%", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, signal_handler))

    print("Bot started...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
