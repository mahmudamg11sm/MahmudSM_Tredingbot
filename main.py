import telebot
from telebot import types
import requests
import os
from flask import Flask
from threading import Thread

# ================= FLASK FOR RENDER =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ================= BOT =================
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise Exception("TOKEN not found in environment variables")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

print("Crypto Bot v2 is running...")

# ================= MENUS =================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top Coins", "🔥 Trending")
    kb.add("💰 Price", "🔍 Search")
    kb.add("ℹ️ About")
    return kb

# ================= START =================
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id, "👋 Welcome to Crypto Bot!\n\nChoose an option:", reply_markup=main_menu())

# ================= COINGECKO =================
def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1
    }
    r = requests.get(url, params=params, timeout=20)
    return r.json()

def get_trending():
    url = "https://api.coingecko.com/api/v3/search/trending"
    r = requests.get(url, timeout=20)
    return r.json()

def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    r = requests.get(url, timeout=20)
    return r.json()

# ================= HANDLERS =================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    text = msg.text.strip()
    chat_id = msg.chat.id

    if text == "🏆 Top Coins":
        data = get_top_coins()
        if not isinstance(data, list):
            bot.send_message(chat_id, "❌ Failed to load top coins.")
            return

        kb = types.InlineKeyboardMarkup()
        message = "🏆 <b>Top 10 Coins</b>\n\n"

        for coin in data:
            name = coin.get("name")
            price = coin.get("current_price")
            coin_id = coin.get("id")

            message += f"• {name} - ${price}\n"
            kb.add(types.InlineKeyboardButton(text=name, callback_data=f"price:{coin_id}"))

        bot.send_message(chat_id, message, reply_markup=kb)
        return

    if text == "🔥 Trending":
        data = get_trending()
        coins = data.get("coins", [])

        kb = types.InlineKeyboardMarkup()
        message = "🔥 <b>Trending Coins</b>\n\n"

        for item in coins[:10]:
            coin = item["item"]
            name = coin["name"]
            coin_id = coin["id"]
            message += f"• {name}\n"
            kb.add(types.InlineKeyboardButton(text=name, callback_data=f"price:{coin_id}"))

        bot.send_message(chat_id, message, reply_markup=kb)
        return

    if text == "💰 Price":
        bot.send_message(chat_id, "Send me the coin name. Example: bitcoin")
        bot.register_next_step_handler(msg, price_step)
        return

    if text == "🔍 Search":
        bot.send_message(chat_id, "Send me the coin name to search:")
        bot.register_next_step_handler(msg, price_step)
        return

    if text == "ℹ️ About":
        bot.send_message(chat_id, "🤖 Crypto Bot\nData from CoinGecko\nBy Mahmud")
        return

    bot.send_message(chat_id, "Use the menu buttons.", reply_markup=main_menu())

# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data.startswith("price:"):
        coin_id = call.data.split(":", 1)[1]
        data = get_price(coin_id)

        if coin_id in data:
            price = data[coin_id]["usd"]
            bot.send_message(call.message.chat.id, f"💰 <b>{coin_id.upper()}</b>\nPrice: ${price}")
        else:
            bot.send_message(call.message.chat.id, "❌ Price not found.")

# ================= PRICE STEP =================
def price_step(msg):
    coin = msg.text.strip().lower()
    data = get_price(coin)

    if coin in data:
        price = data[coin]["usd"]
        bot.send_message(msg.chat.id, f"💰 <b>{coin.upper()}</b>\nPrice: ${price}")
    else:
        bot.send_message(msg.chat.id, "❌ Coin not found.")

# ================= RUN =================
bot.infinity_polling(skip_pending=True)
