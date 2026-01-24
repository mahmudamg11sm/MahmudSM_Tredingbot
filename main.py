import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # misali: @Mahmudsm1
ADMIN_ID = int(os.getenv("CHAT_ID"))  # naka Telegram ID

logging.basicConfig(level=logging.INFO)

# ================== COINS ==================
COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
}

# ================== KEYBOARDS ==================
def coin_keyboard():
    buttons = []
    row = []
    for c in COINS.keys():
        row.append(InlineKeyboardButton(c, callback_data=f"coin_{c}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("📢 Social Links", callback_data="social")])
    return InlineKeyboardMarkup(buttons)

def social_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Telegram Channel", url="https://t.me/Mahmudsm1")],
        [InlineKeyboardButton("🐦 X (Twitter)", url="https://x.com/Mahmud_sm1")],
        [InlineKeyboardButton("📘 Facebook", url="https://www.facebook.com/profile.php?id=61580620438042")],
    ])

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("✅ Na shiga (Check)", callback_data="check_join")]
    ])

# ================== HELPERS ==================
def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    r = requests.get(url, timeout=10)
    data = r.json()
    if coin_id in data:
        return data[coin_id]["usd"]
    return None

async def is_user_joined(bot, user_id: int):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    joined = await is_user_joined(context.bot, user.id)
    if not joined:
        await update.message.reply_text(
            "❗ Dole ka shiga channel ɗin mu kafin amfani da bot.\n\nDa fatan ka shiga:",
            reply_markup=join_keyboard()
        )
        return

    await update.message.reply_text(
        "🚀 Barka da zuwa *Dynamic Auto Signal Bot*\n\nZaɓi coin:",
        parse_mode="Markdown",
        reply_markup=coin_keyboard()
    )

# ================== BUTTON HANDLER ==================
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # check join
    if query.data == "check_join":
        joined = await is_user_joined(context.bot, user.id)
        if not joined:
            await query.edit_message_text(
                "❌ Har yanzu baka shiga channel ba.\nDa fatan ka shiga:",
                reply_markup=join_keyboard()
            )
            return

        await query.edit_message_text(
            "✅ Ka shiga! Yanzu zaɓi coin:",
            reply_markup=coin_keyboard()
        )
        return

    if query.data == "social":
        await query.message.reply_text(
            "📢 Bi mu a shafukanmu:",
            reply_markup=social_buttons()
        )
        return

    if query.data.startswith("coin_"):
        symbol = query.data.replace("coin_", "")
        await send_signal(query, context, symbol)

# ================== SIGNAL FUNCTION ==================
async def send_signal(query, context, symbol):
    if symbol not in COINS:
        await query.message.reply_text("❌ Ban san wannan coin ba.")
        return

    coin_id = COINS[symbol]
    price_now = get_price(coin_id)

    if price_now is None:
        await query.message.reply_text("❌ Kuskure wajen ɗauko price.")
        return

    # Fake simple trend (for now)
    import random
    trend_type = random.choice(["bull", "bear", "side"])

    if trend_type == "bull":
        trend = "📈 Kasuwa na kokarin hawa (Bullish)"
        target_up = round(price_now * 1.05, 2)
        target_down = round(price_now * 0.97, 2)
    elif trend_type == "bear":
        trend = "📉 Kasuwa na kokarin sauka (Bearish)"
        target_up = round(price_now * 1.03, 2)
        target_down = round(price_now * 0.95, 2)
    else:
        trend = "➖ Kasuwa na tafiya a tsakiya (Sideways)"
        target_up = round(price_now * 1.03, 2)
        target_down = round(price_now * 0.97, 2)

    text = f"""
🪙 Coin: {symbol}
💰 Price yanzu: ${price_now}

📊 Trend:
{trend}

🎯 Hasashe:
Zai iya hawa zuwa: ~ ${target_up}
Ko ya sauka zuwa: ~ ${target_down}

⚠️ Wannan hasashe ne na analysis kawai.
"""

    await query.message.reply_text(text)

# ================== PRICE COMMAND ==================
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Rubuta: /price BTC")
        return

    symbol = context.args[0].upper()
    if symbol not in COINS:
        await update.message.reply_text("❌ Ban san wannan coin ba.")
        return

    p = get_price(COINS[symbol])
    await update.message.reply_text(f"💰 Farashin {symbol} yanzu: ${p}")

# ================== BROADCAST (ADMIN) ==================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Rubuta: /broadcast sakonka")
        return

    text = " ".join(context.args)
    await update.message.reply_text("✅ An tura sakon (demo).")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(on_button))

    print("Dynamic Auto Signal Bot yana gudana...")
    app.run_polling()

if __name__ == "__main__":
    main()
