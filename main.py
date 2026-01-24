import os
import asyncio
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@Mahmudsm1"
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
COIN_REFRESH_INTERVAL = 30  # seconds

# ================= HELPERS =================
async def fetch_coins():
    coins = []
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://api.bybit.com/v2/public/tickers")
            data = r.json()
            if "result" in data:
                for item in data["result"]:
                    symbol = item["symbol"]
                    price = item.get("last_price", "N/A")
                    coins.append({"symbol": symbol, "price": price})
        except Exception as e:
            print("Error fetching coins:", e)
    return coins

def build_coins_keyboard(coins, per_row=4):
    keyboard = []
    row = []
    for idx, coin in enumerate(coins, start=1):
        row.append(InlineKeyboardButton(coin["symbol"], callback_data=f"coin:{coin['symbol']}"))
        if idx % per_row == 0:
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

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    coins = await fetch_coins()
    context.application_data["coins"] = coins
    await update.message.reply_text(
        "Zaɓi coin daga list ɗin:",
        reply_markup=build_coins_keyboard(coins)
    )

async def coin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, symbol = query.data.split(":")
    coins = context.application_data.get("coins", [])
    coin = next((c for c in coins if c["symbol"] == symbol), None)
    if coin:
        await query.edit_message_text(f"Signal/Price don {symbol}: {coin['price']}", reply_markup=build_coins_keyboard(coins))
    else:
        await query.edit_message_text("Ba a samu coin ba.", reply_markup=build_coins_keyboard(coins))

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    coins = context.application_data.get("coins", [])
    matches = [c for c in coins if text in c["symbol"]]
    if matches:
        await update.message.reply_text(
            "An samu coins:\n" + "\n".join([f"{c['symbol']}: {c['price']}" for c in matches]),
            reply_markup=build_coins_keyboard(coins)
        )
    else:
        await update.message.reply_text("Ba a samu coin ba.", reply_markup=build_coins_keyboard(coins))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Kai ba admin bane!")
        return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Rubuta sako bayan /broadcast")
        return
    await update.message.reply_text(f"[Broadcast]: {msg}")

# ================= AUTO REFRESH TASK =================
async def refresh_coins_task(application):
    while True:
        try:
            coins = await fetch_coins()
            application.application_data["coins"] = coins
        except Exception as e:
            print("Error refreshing coins:", e)
        await asyncio.sleep(COIN_REFRESH_INTERVAL)

# ================= MAIN =================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coin_button, pattern=r"^coin:"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search_coin))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("Dynamic Auto Signal Bot v12 yana gudana...")

    # Start auto-refresh coins
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(refresh_coins_task(app)), interval=COIN_REFRESH_INTERVAL, first=0)

    # Start polling
    app.run_polling()
