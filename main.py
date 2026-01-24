import os
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@Mahmudsm1"
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# ================= DATA ==================
COINS = ["ADA", "BTC", "ETH", "SOL", "DOGE", "XRP", "LTC", "DOT", "BNB", "LINK"]
COINS_PER_ROW = 4

# Mock Bybit prices/signals
COIN_PRICES = {coin: f"${100+idx*10:.2f}" for idx, coin in enumerate(COINS)}

# ================= HELPERS =================
def coins_keyboard():
    keyboard = []
    row = []
    for idx, coin in enumerate(COINS, start=1):
        row.append(InlineKeyboardButton(coin, callback_data=f"coin:{coin}"))
        if idx % COINS_PER_ROW == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def social_buttons():
    keyboard = [
        [InlineKeyboardButton("Telegram", url="https://t.me/Mahmudsm1")],
        [InlineKeyboardButton("X/Twitter", url="https://x.com/Mahmud_sm1")],
        [InlineKeyboardButton("Facebook", url="https://www.facebook.com/profile.php?id=61580620438042")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_membership(update: Update):
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return True
    except:
        return False

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel verification
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=update.effective_user.id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}")
            return
    except:
        await update.message.reply_text(f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}")
        return

    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nBi mu a shafukanmu:",
        reply_markup=social_buttons()
    )
    await update.message.reply_text(
        "Zaɓi coin daga list ɗin:",
        reply_markup=coins_keyboard()
    )

async def coin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, coin = query.data.split(":")
    price = COIN_PRICES.get(coin, "Ba a samu price ba")
    await query.edit_message_text(f"Signal/Price don {coin}: {price}", reply_markup=coins_keyboard())

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    matches = [coin for coin in COINS if text in coin]
    if matches:
        await update.message.reply_text(
            "An samu coins:\n" + "\n".join(matches),
            reply_markup=coins_keyboard()
        )
    else:
        await update.message.reply_text("Ba a samu coin ba.", reply_markup=coins_keyboard())

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Kai ba admin bane!")
        return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Rubuta sako bayan /broadcast")
        return
    # Send to all chat_ids (for simplicity, only replies to current chat)
    await update.message.reply_text(f"[Broadcast]: {msg}")

# ================= MAIN =================
async def main():
    nest_asyncio.apply()  # Allow nested event loops in Railway/Render

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coin_button, pattern=r"^coin:"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search_coin))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("Dynamic Auto Signal Bot v8 yana gudana...")
    await app.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
