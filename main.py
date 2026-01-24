import os
import json
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not CHANNEL_USERNAME or not ADMIN_ID:
    raise RuntimeError("Ka tabbata ka sa BOT_TOKEN, CHANNEL_USERNAME, ADMIN_ID a Railway Variables")

# ================= DATA =================
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        return set(json.load(f))

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

USERS = load_users()

# ================= COINS =================
COINS = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","LTC","TRX","MATIC","AVAX","DOT","LINK","UNI","SHIB"]

# ================= KEYBOARDS =================
def coin_keyboard():
    rows = []
    row = []
    for c in COINS:
        row.append(c)
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("✅ Na shiga (Check)", callback_data="check_join")]
    ])

# ================= JOIN CHECK =================
async def is_joined(user_id, context):
    try:
        m = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member","administrator","creator"]
    except:
        return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_joined(user.id, context):
        await update.message.reply_text("❗ Dole ne ka shiga channel kafin amfani da bot.", reply_markup=join_keyboard())
        return

    USERS.add(user.id)
    save_users(USERS)

    await update.message.reply_text(
        "🚀 Barka da zuwa Dynamic Auto Signal Bot\n\nZaɓi coin ko yi amfani da:\n/price BTC\n/signal ETH",
        reply_markup=coin_keyboard()
    )

# ================= CHECK BUTTON =================
async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if await is_joined(user_id, context):
        USERS.add(user_id)
        save_users(USERS)
        await q.edit_message_text("✅ Yanzu zaka iya amfani da bot.")
        await context.bot.send_message(user_id, "Zaɓi coin:", reply_markup=coin_keyboard())
    else:
        await q.edit_message_text("❌ Har yanzu baka shiga channel ba.", reply_markup=join_keyboard())

# ================= PRICE =================
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Misali: /price BTC")
        return

    coin = context.args[0].upper()
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT", timeout=10)
        p = float(r.json()["price"])
        await update.message.reply_text(f"💰 {coin} Price: ${p:,.2f}")
    except:
        await update.message.reply_text("❌ Coin ba a samu ba.")

# ================= SIGNAL =================
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Misali: /signal BTC")
        return

    coin = context.args[0].upper()
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT", timeout=10)
        p = float(r.json()["price"])
        high = p * 1.03
        low = p * 0.97

        text = (
            f"🪙 {coin}\n"
            f"💰 Price: ${p:,.2f}\n"
            f"🎯 Target: ~ ${high:,.2f}\n"
            f"🛑 Stop: ~ ${low:,.2f}\n\n"
            f"⚠️ Analysis ne kawai."
        )

        await update.message.reply_text(text)

    except:
        await update.message.reply_text("❌ Error.")

# ================= TEXT BUTTON =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.upper()
    if txt in COINS:
        context.args = [txt]
        await signal(update, context)

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        f"👑 Admin Panel\n\nUsers: {len(USERS)}\n\nCommands:\n/broadcast sako"
    )

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Misali: /broadcast Hello")
        return

    msg = " ".join(context.args)
    sent = 0

    for uid in list(USERS):
        try:
            await context.bot.send_message(uid, msg)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass

    await update.message.reply_text(f"✅ An tura zuwa users {sent}")

# ================= AUTO POST =================
async def auto_post(app):
    await asyncio.sleep(20)
    while True:
        try:
            coin = "BTC"
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT", timeout=10)
            p = float(r.json()["price"])

            text = f"📊 Auto Signal\n\n🪙 BTC\n💰 Price: ${p:,.2f}\n⚠️ Wannan analysis ne kawai."

            await app.bot.send_message(CHANNEL_USERNAME, text)
        except:
            pass

        await asyncio.sleep(3600)  # 1 hour

# ================= MAIN =================
def main():
    print("🚀 Bot yana gudana...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(check_join_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.job_queue.run_once(lambda ctx: asyncio.create_task(auto_post(app)), 10)

    app.run_polling()

if __name__ == "__main__":
    main()
