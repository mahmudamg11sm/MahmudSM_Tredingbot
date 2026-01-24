import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, PicklePersistence

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_USERNAME = "@Mahmudsm1"  # canza idan akwai sabo

COINS = ["BTC", "ETH", "ADA", "XRP", "SOL"]  # sample coins
COIN_REFRESH_INTERVAL = 60  # seconds

# ================== UTILS ==================
def coin_buttons():
    keyboard = [[InlineKeyboardButton(coin, callback_data=f"coin_{coin}")] for coin in COINS]
    return InlineKeyboardMarkup(keyboard)

def social_buttons():
    keyboard = [
        [InlineKeyboardButton("Telegram", url="https://t.me/Mahmudsm1")],
        [InlineKeyboardButton("X/Twitter", url="https://x.com/Mahmud_sm1")],
        [InlineKeyboardButton("Facebook", url="https://www.facebook.com/profile.php?id=61580620438042")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # check if user joined channel
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("left", "kicked"):
            await update.message.reply_text(
                f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}",
                reply_markup=social_buttons()
            )
            return
    except:
        await update.message.reply_text(
            f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}",
            reply_markup=social_buttons()
        )
        return

    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\nZaɓi coin:",
        reply_markup=coin_buttons()
    )

async def coin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    coin = query.data.split("_")[1]
    await query.edit_message_text(f"Ka zabi coin: {coin}")

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    results = [coin for coin in COINS if text in coin]
    if results:
        keyboard = [[InlineKeyboardButton(c, callback_data=f"coin_{c}")] for c in results]
        await update.message.reply_text(
            "Na samo coins ɗin nan:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("Ba a samu coin ba.")

# Admin broadcast
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    message = " ".join(context.args)
    for user_id in context.bot_data.get("users", []):
        try:
            await context.bot.send_message(user_id, message)
        except:
            pass
    await update.message.reply_text("Broadcast ya tura!")

# ================== BACKGROUND TASK ==================
async def refresh_coins_task(app):
    while True:
        # nan zaka iya haɗa API call daga Bybit ko tradingview
        # misali: COINS = updated list
        await asyncio.sleep(COIN_REFRESH_INTERVAL)

# ================== MAIN ==================
async def main():
    persistence = PicklePersistence(filepath="bot_data.pkl")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(coin_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # store users
    async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        users = context.bot_data.get("users", set())
        users.add(update.effective_user.id)
        context.bot_data["users"] = users
    app.add_handler(MessageHandler(filters.ALL, save_user))

    # start background task
    asyncio.create_task(refresh_coins_task(app))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
