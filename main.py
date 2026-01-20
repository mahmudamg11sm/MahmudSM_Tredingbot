import telebot
from telebot import types
import os
import requests
from flask import Flask
from threading import Thread
import time

# ================= WEB SERVER FOR RENDER =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto Bot v2 is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ================= KEEP ALIVE =================
def keep_alive():
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL") or "https://mahmudsm-tredingbot.onrender.com"
            requests.get(url)
        except:
            pass
        time.sleep(300)

Thread(target=keep_alive).start()

# ================= BOT CONFIG =================
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise Exception("BOT TOKEN not found!")

ADMIN_ID = 6648308251
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= MENU =================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📈 Trending", "🏆 Top Coins")
    markup.add("💰 Price", "🔍 Search")
    markup.add("ℹ️ About")
    return markup

# ================= API HELPERS =================
COINGECKO_API = "https://api.coingecko.com/api/v3"

def get_top(limit=10):
    try:
        r = requests.get(f"{COINGECKO_API}/coins/markets", params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
        })
        return r.json()
    except:
        return []

def get_trending():
    try:
        r = requests.get(f"{COINGECKO_API}/search/trending")
        return r.json().get("coins", [])
    except:
        return []

def get_price(coin_id):
    try:
        r = requests.get(f"{COINGECKO_API}/simple/price", params={
            "ids": coin_id,
            "vs_currencies": "usd"
        })
        return r.json().get(coin_id, {}).get("usd")
    except:
        return None

# ================= HANDLERS =================
@bot.message_handler(commands=["start"])
def start(msg):
    chat_id = msg.chat.id
    bot.send_message(chat_id, "Welcome to Crypto Bot v2!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle(msg):
    chat_id = msg.chat.id
    text = msg.text.strip()

    if text == "ℹ️ About":
        bot.send_message(chat_id, "Crypto Bot v2\nTop Coins, Trending, Price, Search.\nOwner: @MHSM5")
        return

    if text == "🏆 Top Coins":
        coins = get_top()
        if not coins:
            bot.send_message(chat_id, "Failed to fetch top coins.")
            return
        markup = types.InlineKeyboardMarkup()
        message = "<b>Top 10 Coins:</b>\n\n"
        for coin in coins:
            coin_id = coin.get("id")
            coin_name = coin.get("name")
            coin_price = coin.get("current_price")
            if coin_id and coin_name and coin_price is not None:
                message += f"- {coin_name} (${coin_price})\n"
                markup.add(types.InlineKeyboardButton(coin_name, callback_data=coin_id))
        bot.send_message(chat_id, message, reply_markup=markup)
        return

    if text == "📈 Trending":
        trending = get_trending()
        if not trending:
            bot.send_message(chat_id, "Failed to fetch trending coins.")
            return
        markup = types.InlineKeyboardMarkup()
        message = "<b>Trending Coins:</b>\n\n"
        for t in trending:
            item = t.get("item", {})
            coin_id = item.get("id")
            coin_name = item.get("name")
            coin_symbol = item.get("symbol")
            if coin_id and coin_name:
                message += f"- {coin_name} ({coin_symbol})\n"
                markup.add(types.InlineKeyboardButton(coin_name, callback_data=coin_id))
        bot.send_message(chat_id, message, reply_markup=markup)
        return

    if text == "💰 Price":
        bot.send_message(chat_id, "Send coin id or symbol (example: bitcoin, solana, eth)")
        bot.register_next_step_handler(msg, price_step)
        return

    if text == "🔍 Search":
        bot.send_message(chat_id, "Send coin id or name to search")
        bot.register_next_step_handler(msg, search_step)
        return

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    coin_id = call.data
    price = get_price(coin_id)
    if price is None:
        bot.answer_callback_query(call.id, f"Price not found for {coin_id}")
    else:
        bot.answer_callback_query(call.id, f"${price} USD", show_alert=True)

# ================= NEXT STEP HANDLERS =================
def price_step(msg):
    coin_id = msg.text.strip().lower()
    price = get_price(coin_id)
    if price is None:
        bot.send_message(msg.chat.id, f"Coin not found: {coin_id}")
    else:
        bot.send_message(msg.chat.id, f"{coin_id} price: ${price} USD")

def search_step(msg):
    coin_id = msg.text.strip().lower()
    try:
        r = requests.get(f"{COINGECKO_API}/coins/{coin_id}")
        data = r.json()
        name = data.get("name")
        price = data.get("market_data", {}).get("current_price", {}).get("usd")
        if not name:
            bot.send_message(msg.chat.id, f"Coin not found: {coin_id}")
        else:
            bot.send_message(msg.chat.id, f"{name}: ${price} USD")
    except:
        bot.send_message(msg.chat.id, f"Error fetching coin: {coin_id}")

# ================= RUN BOT =================
print("Crypto Bot v2 is running...")
bot.infinity_polling(skip_pending=True)
