import os
import requests
import telebot
from telebot import types
from flask import Flask, request
from threading import Thread

# ================= CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
bot = telebot.TeleBot(TOKEN)

# Flask app for Render
app = Flask(__name__)

# ================= DATA ==================
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
VS_CURRENCY = "usd"
TOP_N = 10

# =================== FUNCTIONS ===================

def fetch_top_coins():
    try:
        response = requests.get(COINGECKO_URL, params={
            "vs_currency": VS_CURRENCY,
            "order": "market_cap_desc",
            "per_page": TOP_N,
            "page": 1,
            "price_change_percentage": "24h"
        })
        data = response.json()
        top_coins_msg = "🏆 Top Coins:\n\n"
        for coin in data:
            top_coins_msg += f"- {coin['name']} (${coin['current_price']})\n"
        return top_coins_msg
    except Exception as e:
        return "❌ Failed to load top coins"

def fetch_coin_price(coin_id):
    try:
        response = requests.get(COINGECKO_URL, params={
            "vs_currency": VS_CURRENCY,
            "ids": coin_id
        })
        data = response.json()
        if len(data) == 0:
            return None
        coin = data[0]
        msg = f"{coin['name']} (${coin['current_price']})\n24h Change: {coin['price_change_percentage_24h']:.2f}%"
        return msg
    except:
        return None

def fetch_coin_analysis(coin_id):
    """
    Educational signal analysis in Hausa
    """
    try:
        response = requests.get(COINGECKO_URL, params={
            "vs_currency": VS_CURRENCY,
            "ids": coin_id
        })
        data = response.json()
        if len(data) == 0:
            return "❌ Coin ba a samu ba"
        coin = data[0]

        # Simple educational signals
        price = coin['current_price']
        high = coin['high_24h']
        low = coin['low_24h']
        change_pct = coin['price_change_percentage_24h']

        trend = "Tana tashi" if change_pct > 0 else "Tana sauka"
        rsi_indicator = "Oversold" if change_pct < -3 else "Overbought" if change_pct > 3 else "Neutral"

        msg = f"📊 {coin['name']} ({coin['symbol'].upper()}) Analysis\n\n"
        msg += f"🔹 Trend: {trend}\n"
        msg += f"🔹 RSI: {rsi_indicator}\n"
        msg += f"🔹 Farashin yanzu: ${price}\n"
        msg += f"🔹 High 24h: ${high}\n"
        msg += f"🔹 Low 24h: ${low}\n\n"
        msg += "🧠 Fahimta:\nKasuwancin na iya yin tashi ko sauka, amma wannan kawai koyarwa ce.\n"
        msg += "⚠️ Wannan ba shawarar saka jari ba."

        return msg
    except:
        return "❌ An samu matsala wajen analysis"

# =================== BOT HANDLERS ===================

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏆 Top Coins", "🔥 Trending", "📊 Analysis")
    bot.send_message(chat_id, "Barka da zuwa Crypto Bot! Zaɓi wani abu daga menu:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle(message):
    chat_id = message.chat.id
    text = message.text.strip().lower()

    if text == "🏆 top coins":
        bot.send_message(chat_id, fetch_top_coins())
    elif text == "📊 analysis":
        # Show coin list
        markup = types.InlineKeyboardMarkup()
        try:
            response = requests.get(COINGECKO_URL, params={
                "vs_currency": VS_CURRENCY,
                "order": "market_cap_desc",
                "per_page": TOP_N,
                "page": 1
            })
            coins = response.json()
            for coin in coins:
                markup.add(types.InlineKeyboardButton(coin['name'], callback_data=f"analysis_{coin['id']}"))
            bot.send_message(chat_id, "Zaɓi coin don analysis:", reply_markup=markup)
        except:
            bot.send_message(chat_id, "❌ An samu matsala wajen ɗauko coins")
    elif text == "🔥 trending":
        bot.send_message(chat_id, "🔥 Trending coins feature na zuwa nan gaba")
    else:
        # Try coin lookup
        coin_msg = fetch_coin_price(text)
        if coin_msg:
            bot.send_message(chat_id, coin_msg)
        else:
            bot.send_message(chat_id, "❌ Ba a samu coin ba ko zaɓi mara kyau")

@bot.callback_query_handler(func=lambda call: call.data.startswith("analysis_"))
def callback_analysis(call):
    coin_id = call.data.replace("analysis_", "")
    msg = fetch_coin_analysis(coin_id)
    bot.send_message(call.message.chat.id, msg)

# =================== FLASK APP ===================
@app.route("/", methods=["GET"])
def home():
    return "Crypto Bot v2 is running!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run).start()

# =================== BOT START ===================
if __name__ == "__main__":
    # Infinity polling
    bot.infinity_polling(skip_pending=True)
