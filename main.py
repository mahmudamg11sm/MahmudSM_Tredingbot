import os
import requests
from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ================= COINS =================
COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
}

# ================= COINGECKO PRICE =================
def get_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        r = requests.get(url, timeout=10)
        data = r.json()
        return data.get(coin_id, {}).get("usd", None)
    except:
        return None

# ================= BUTTONS =================
def coin_buttons():
    keyboard = [
        [InlineKeyboardButton(symbol, callback_data=symbol) for symbol in COINS]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👋 Barka da zuwa Dynamic Auto Signal Bot!\n\nZaɓi coin daga buttons ko amfani da /price <coin> ko /signal <coin>\n\n⚠️ Wannan analysis ne kawai, ba shawarar saka kudi ba."
    await update.message.reply_text(text, reply_markup=coin_buttons())

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Rubuta misali: /price BTC")
        return
    symbol = context.args[0].upper()
    await send_price(update, context, symbol)

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Rubuta misali: /signal BTC")
        return
    symbol = context.args[0].upper()
    await send_signal(update, context, symbol)

# ================= CALLBACK QUERY =================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.upper()
    await send_signal(update, context, symbol)

# ================= SEND FUNCTIONS =================
async def send_price(update, context, symbol):
    if symbol not in COINS:
        await update.message.reply_text("❌ Ban san wannan coin ba.")
        return
    coin_id = COINS[symbol]
    price = get_price(coin_id)
    if price is None:
        await update.message.reply_text("❌ Kuskure wajen ɗauko price.")
        return
    await update.message.reply_text(f"💰 Farashin {symbol} yanzu: ${price}")

async def send_signal(update, context, symbol):
    if symbol not in COINS:
        await update.message.reply_text("❌ Ban san wannan coin ba.")
        return
    coin_id = COINS[symbol]
    price_now = get_price(coin_id)
    if price_now is None:
        await update.message.reply_text("❌ Kuskure wajen ɗauko price.")
        return

    # TradingView Analysis
    handler = TA_Handler(
        symbol=symbol + "USDT",
        screener="crypto",
        exchange="BINANCE",
        interval=Interval.INTERVAL_1_HOUR
    )
    analysis = handler.get_analysis()
    recommend = analysis.summary["RECOMMENDATION"]

    if recommend in ["BUY", "STRONG_BUY"]:
        trend = "📈 Kasuwa na kokarin hawa (Bullish)"
        target_up = round(price_now * 1.05, 2)
        target_down = round(price_now * 0.97, 2)
    elif recommend in ["SELL", "STRONG_SELL"]:
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
    await update.message.reply_text(text)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("Dynamic Auto Signal Bot yana gudana...")
    app.run_polling()

if __name__ == "__main__":
    main()
