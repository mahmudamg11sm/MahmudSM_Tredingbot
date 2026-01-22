import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tradingview_ta import TA_Handler, Interval

# ============ CONFIG ============
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ============ COINGECKO ============
def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    r = requests.get(url, timeout=10)
    data = r.json()
    if coin_id in data:
        return data[coin_id]["usd"]
    return None

# ============ COIN MAP ============
COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
}

# ============ COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
👋 Barka da zuwa Crypto Signal Bot (Hausa)

🪙 Umarnai:
 /price BTC  → farashin coin
 /signal ETH → signal & hasashe

📌 Coins:
BTC, ETH, SOL, BNB, XRP, ADA, DOGE

⚠️ Wannan analysis ne kawai, ba shawarar saka kudi ba.
"""
    await update.message.reply_text(text)

# -------- PRICE --------
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("❗ Rubuta misali: /price BTC")
        return

    symbol = context.args[0].upper()

    if symbol not in COINS:
        await update.message.reply_text("❌ Ban san wannan coin ba.")
        return

    coin_id = COINS[symbol]
    p = get_price(coin_id)

    if p is None:
        await update.message.reply_text("❌ Kuskure wajen ɗauko price.")
        return

    await update.message.reply_text(f"💰 Farashin {symbol} yanzu: ${p}")

# -------- SIGNAL --------
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("❗ Rubuta misali: /signal ETH")
        return

    symbol = context.args[0].upper()

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
    summary = analysis.summary

    recommend = summary["RECOMMENDATION"]

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

# ============ MAIN ============
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))

    print("Bot yana gudana...")
    app.run_polling()

if __name__ == "__main__":
    main()
