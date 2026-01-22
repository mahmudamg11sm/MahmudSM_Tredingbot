import os
import time
import requests
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from tradingview_ta import TA_Handler, Interval
import threading
from io import BytesIO
from PIL import Image

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("SIGNAL_CHAT_ID")
PERCENT_THRESHOLD = 2.0  # Smart Threshold %
AUTO_CHECK_INTERVAL = 300  # seconds

bot = Bot(token=BOT_TOKEN)

# ===== GLOBAL =====
COINS = {}
last_prices = {}
last_daily_summary = datetime.now() - timedelta(days=1)

# ===== GET TOP COINS =====
def get_top_coins(limit=100):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return {coin["symbol"].upper(): coin["id"] for coin in data}
    except:
        return {}

# ===== GET PRICE =====
def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return data.get(coin_id, {}).get("usd")
    except:
        return None

# ===== GET COIN IMAGE =====
def get_coin_image(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    try:
        r = requests.get(url, timeout=10).json()
        img_url = r.get("image", {}).get("large")
        if img_url:
            resp = requests.get(img_url, timeout=10)
            return BytesIO(resp.content)
        return None
    except:
        return None

# ===== SEND SIGNAL =====
def send_signal(symbol, price_now, extra_note="", multi_interval={}):
    text = f"""
🪙 Coin: {symbol}
💰 Price yanzu: ${price_now}

⚠️ Wannan hasashe ne na analysis kawai.
{extra_note}
"""
    for interval, rec in multi_interval.items():
        text += f"{interval}: {rec}\n"

    text += f"\n📈 Trend chart: https://www.tradingview.com/symbols/{symbol}USDT/"

    img_data = get_coin_image(COINS.get(symbol))
    if img_data:
        bot.send_photo(chat_id=CHAT_ID, photo=img_data, caption=text)
    else:
        bot.send_message(chat_id=CHAT_ID, text=text)

# ===== BUTTONS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global COINS
    COINS = get_top_coins(limit=100)
    last_prices.update({coin: 0 for coin in COINS.keys()})
    keyboard = [[InlineKeyboardButton(coin, callback_data=coin) for coin in list(COINS.keys())[i:i+3]] for i in range(0, len(COINS), 3)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Zaɓi coin ko rubuta symbol:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    coin = query.data
    await process_coin(coin, triggered="button")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.strip().upper()
    if coin in COINS:
        await process_coin(coin, triggered="user")
    else:
        await update.message.reply_text(f"❌ Coin {coin} ba a samu ba")

async def process_coin(coin, triggered="user"):
    coin_id = COINS.get(coin)
    if not coin_id:
        return
    price_now = get_price(coin_id)
    if not price_now:
        return

    multi_interval = {}
    for interval in [Interval.INTERVAL_1_HOUR, Interval.INTERVAL_4_HOURS, Interval.INTERVAL_1_DAY]:
        handler = TA_Handler(symbol=coin + "USDT", screener="crypto", exchange="BINANCE", interval=interval)
        try:
            analysis = handler.get_analysis()
            multi_interval[interval] = analysis.summary["RECOMMENDATION"]
        except:
            multi_interval[interval] = "N/A"

    extra_note = f"✅ Triggered by {triggered}"
    send_signal(coin, price_now, extra_note=extra_note, multi_interval=multi_interval)

# ===== AUTO SIGNAL LOOP =====
def auto_signal_loop():
    global last_prices, last_daily_summary
    while True:
        COINS_LOCAL = get_top_coins(limit=100)
        for coin, coin_id in COINS_LOCAL.items():
            price_now = get_price(coin_id)
            if price_now is None:
                continue

            last_price = last_prices.get(coin, 0)
            if last_price == 0 or abs(price_now - last_price)/last_price*100 >= PERCENT_THRESHOLD:
                multi_interval = {}
                for interval in [Interval.INTERVAL_1_HOUR, Interval.INTERVAL_4_HOURS, Interval.INTERVAL_1_DAY]:
                    handler = TA_Handler(symbol=coin + "USDT", screener="crypto", exchange="BINANCE", interval=interval)
                    try:
                        analysis = handler.get_analysis()
                        multi_interval[interval] = analysis.summary["RECOMMENDATION"]
                    except:
                        multi_interval[interval] = "N/A"
                send_signal(coin, price_now, extra_note="🔔 Auto smart price alert", multi_interval=multi_interval)
                last_prices[coin] = price_now

        # Daily summary
        now = datetime.now()
        if now - last_daily_summary >= timedelta(hours=24):
            summary_text = "📅 Daily Crypto Summary (Top 100)\n\n"
            for coin, coin_id in COINS_LOCAL.items():
                price_now = get_price(coin_id)
                if price_now:
                    multi_interval = {}
                    for interval in [Interval.INTERVAL_1_HOUR, Interval.INTERVAL_4_HOURS, Interval.INTERVAL_1_DAY]:
                        handler = TA_Handler(symbol=coin + "USDT", screener="crypto", exchange="BINANCE", interval=interval)
                        try:
                            analysis = handler.get_analysis()
                            multi_interval[interval] = analysis.summary["RECOMMENDATION"]
                        except:
                            multi_interval[interval] = "N/A"
                    summary_text += f"{coin}: ${price_now} | {multi_interval}\n"
            bot.send_message(chat_id=CHAT_ID, text=summary_text)
            last_daily_summary = now

        time.sleep(AUTO_CHECK_INTERVAL)

# ===== MAIN =====
def main():
    global COINS
    COINS = get_top_coins(limit=100)
    last_prices.update({coin: 0 for coin in COINS.keys()})

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    threading.Thread(target=auto_signal_loop, daemon=True).start()

    print("Dynamic Auto Signal Bot v2.8 yana gudana...")
    app.run_polling()

if __name__ == "__main__":
    main()
