import telebot
from telebot import types
import os
import requests
from flask import Flask
from threading import Thread

# ================== WEB SERVER (FOR RENDER) ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ================== BOT CONFIG ==================
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise Exception("TOKEN not found in environment variables")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================== COINGECKO API ==================
BASE_URL = "https://api.coingecko.com/api/v3"

# ================== MENUS ==================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📈 Trending")
    markup.add("🏆 Top Coins")
    markup.add("💰 Price")
    markup.add("🔎 Search")
    markup.add("ℹ️ About")
    return markup

# ================== HELPERS ==================
def get_trending():
    url = f"{BASE_URL}/search/trending"
    r = requests.get(url, timeout=10).json()
    coins = r.get("coins", [])
    return coins

def get_top():
    url = f"{BASE_URL}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1"
    r = requests.get(url, timeout=10).json()
    return r

def get_price(coin_id):
    url = f"{BASE_URL}/simple/price?ids={coin_id}&vs_currencies=usd"
    r = requests.get(url, timeout=10).json()
    return r

def search_coin(query):
    url = f"{BASE_URL}/search?query={query}"
    r = requests.get(url, timeout=10).json()
    return r.get("coins", [])

# ================== COMMANDS ==================
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "🤖 <b>Welcome to Crypto Trending Bot!</b>\n\n"
        "You can:\n"
        "📈 See trending coins\n"
        "🏆 See top coins\n"
        "💰 Check price\n"
        "🔎 Search any coin",
        reply_markup=main_menu()
    )

# ================== MAIN HANDLER ==================
user_state = {}

@bot.message_handler(func=lambda m: True)
def handle(msg):
    chat_id = msg.chat.id
    text = msg.text.strip()

    # ===== Buttons =====
    if text == "📈 Trending":
        coins = get_trending()
        if not coins:
            bot.send_message(chat_id, "Failed to get trending coins.")
            return

        message = "🔥 <b>Trending Coins:</b>\n\n"
        for i, item in enumerate(coins[:10], 1):
            coin = item["item"]
            message += f"{i}. {coin['name']} ({coin['symbol'].upper()})\n"

        bot.send_message(chat_id, message)
        return

    if text == "🏆 Top Coins":
        coins = get_top()
        if not coins:
            bot.send_message(chat_id, "Failed to get top coins.")
            return

        message = "🏆 <b>Top 10 Coins by Market Cap:</b>\n\n"
        for i, coin in enumerate(coins, 1):
            message += f"{i}. {coin['name']} (${coin['current_price']})\n"

        bot.send_message(chat_id, message)
        return

    if text == "💰 Price":
        bot.send_message(chat_id, "Send coin id (example: bitcoin, ethereum, solana)")
        user_state[chat_id] = "price"
        return

    if text == "🔎 Search":
        bot.send_message(chat_id, "Send coin name to search (example: doge, pepe, shiba)")
        user_state[chat_id] = "search"
        return

    if text == "ℹ️ About":
        bot.send_message(
            chat_id,
            "ℹ️ <b>Crypto Trending Bot</b>\n"
            "Data source: CoinGecko (free API)\n"
            "Features:\n"
            "- Trending coins\n"
            "- Top coins\n"
            "- Price check\n"
            "- Search coins"
        )
        return

    # ===== Waiting for user input =====
    if chat_id in user_state:
        mode = user_state[chat_id]

        if mode == "price":
            coin_id = text.lower().replace(" ", "-")
            data = get_price(coin_id)
            if coin_id not in data:
                bot.send_message(chat_id, "❌ Coin not found. Try: bitcoin, ethereum, solana")
            else:
                price = data[coin_id]["usd"]
                bot.send_message(chat_id, f"💰 <b>{coin_id.upper()}</b> price: <b>${price}</b>")
            user_state.pop(chat_id, None)
            return

        if mode == "search":
            results = search_coin(text)
            if not results:
                bot.send_message(chat_id, "❌ No results found.")
            else:
                message = "🔎 <b>Search Results:</b>\n\n"
                for coin in results[:10]:
                    message += f"- {coin['name']} ({coin['symbol'].upper()}) | id: <code>{coin['id']}</code>\n"
                bot.send_message(chat_id, message)
            user_state.pop(chat_id, None)
            return

    # ===== Default =====
    bot.send_message(chat_id, "Please use the menu buttons.", reply_markup=main_menu())

# ================== RUN ==================
print("Crypto Bot is running...")
bot.infinity_polling(skip_pending=True)
