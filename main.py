import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")  # example: @Mahmudsm1

TIMEFRAME = Interval.INTERVAL_4_HOURS

# Some popular Bybit coins (you can add more)
COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT", "DOTUSDT",
    "LTCUSDT", "TRXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT",
    "OPUSDT", "ARBUSDT", "FILUSDT", "NEARUSDT", "APEUSDT"
]

logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def coins_keyboard():
    keyboard = []
    row = []
    for i, coin in enumerate(COINS, 1):
        row.append(InlineKeyboardButton(coin.replace("USDT",""), callback_data=f"coin:{coin}"))
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# ================= SIGNAL =================
def get_signal(symbol: str):
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange="BYBIT",
        interval=TIMEFRAME
    )

    analysis = handler.get_analysis()
    summary = analysis.summary

    recommendation = summary["RECOMMENDATION"]
    buy = summary["BUY"]
    sell = summary["SELL"]
    neutral = summary["NEUTRAL"]

    price = float(analysis.indicators["close"])

    if recommendation in ["BUY", "STRONG_BUY"]:
        entry = price
        sl = price * 0.98
        tp = price * 1.04
        rec = "BUY"
    elif recommendation in ["SELL", "STRONG_SELL"]:
        entry = price
        sl = price * 1.02
        tp = price * 0.96
        rec = "SELL"
    else:
        entry = price
        sl = price * 0.99
        tp = price * 1.01
        rec = "NEUTRAL"

    return {
        "symbol": symbol,
        "rec": rec,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "buy": buy,
        "sell": sell,
        "neutral": neutral
    }

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Na shiga", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"Don amfani da bot, sai ka shiga channel ɗinmu:\n{CHANNEL_USERNAME}",
            reply_markup=btn
        )
        return

    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nZaɓi coin ko ka rubuta sunan coin:",
        reply_markup=coins_keyboard()
    )

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if await is_user_in_channel(context, user_id):
        await query.edit_message_text(
            "✅ An tabbatar! Zaɓi coin:",
            reply_markup=coins_keyboard()
        )
    else:
        await query.answer("❌ Har yanzu baka shiga channel ba!", show_alert=True)

# ================= BUTTON =================
async def coin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("coin:"):
        return

    symbol = data.split(":")[1]

    try:
        s = get_signal(symbol)

        text = f"""
📊 Signal for {s['symbol']} (4H)

📈 Recommendation: {s['rec']}

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}
💰 Take Profit: {s['tp']:.4f}

🟢 Buy: {s['buy']}
🔴 Sell: {s['sell']}
⚪ Neutral: {s['neutral']}

⚠️ Not financial advice. Trade at your own risk.
"""
        await query.edit_message_text(text)

    except Exception as e:
        await query.edit_message_text("❌ An samu matsala wajen ɗauko signal.")

# ================= SEARCH =================
async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(f"Da fari sai ka shiga {CHANNEL_USERNAME}")
        return

    text = update.message.text.upper().strip()

    if not text.endswith("USDT"):
        text = text + "USDT"

    try:
        s = get_signal(text)

        msg = f"""
📊 Signal for {s['symbol']} (4H)

📈 Recommendation: {s['rec']}

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}
💰 Take Profit: {s['tp']:.4f}

🟢 Buy: {s['buy']}
🔴 Sell: {s['sell']}
⚪ Neutral: {s['neutral']}

⚠️ Not financial advice. Trade at your own risk.
"""
        await update.message.reply_text(msg)

    except:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Amfani: /broadcast saƙonka")
        return

    msg = " ".join(context.args)

    await update.message.reply_text("✅ An aika broadcast (manual sending only).")

# ================= MAIN =================
def main():
    print("Dynamic Auto Signal Bot FINAL yana gudana...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(coin_button, pattern="^coin:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    app.run_polling()

if __name__ == "__main__":
    main()
