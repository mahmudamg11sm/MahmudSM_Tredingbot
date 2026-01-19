import telebot
from telebot import types
import os
import requests
from flask import Flask
from threading import Thread

# ================== WEB SERVER ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto Bot v2 is running!"

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
    r = requests.get(f"{BASE_URL}/search/trending", timeout=10).json()
    return r.get("coins", [])

def get_top():
    r = requests.get(f"{BASE_URL}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1", timeout=10).json()
    return r

def get_price(coin_id):
    r = requests.get(f"{BASE_URL}/simple/price?ids={coin_id}&vs_currencies=usd", timeout=10).json()
    return r

def search_coin(query):
    r = requests.get(f"{BASE_URL}/search?query={query}", timeout=10).json()
    return r.get("coins", [])

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "🤖 <b>Welcome to Crypto Trending Bot v2!</b>\n\n"
        "Use the buttons below to get info about coins.",
        reply_markup=main_menu()
    )

# ================== INLINE BUTTON CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    coin_id = call.data
    price_data = get_price(coin_id)
    if coin_id in price_data:
        price = price_data[coin_id]["usd"]
        bot.answer_callback_query(call.id, f"{coin_id.upper()} price: ${price}")
        bot.send_message(call.message.chat.id, f"💰 <b>{coin_id.upper()}</b> price: <b>${price}</b>")
    else:
        bot.answer_callback_query(call.id, "Coin not found.")

# ================== USER STATE ==================
user_state = {}

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    chat_id = msg.chat.id
    text = msg.text.strip().lower()

    # ===== Buttons =====
    if text == "📈 trending":
        coins = get_trending()
        if not coins:
            bot.send_message(chat_id, "Failed to get trending coins.")
            return
        markup = types.InlineKeyboardMarkup()
        message = "🔥 <b>Trending Coins:</b>\n\n"
        for item in coins:
            coin = item["item"]
            message += f"- {coin['name']} ({coin['symbol'].upper()})\n"
            markup.add(types.InlineKeyboardButton(coin['name'], callback_data=coin['id']))
        bot.send_message(chat_id, message, reply_markup=markup)
        return

    if text == "🏆 top coins":
        coins = get_top()
        if not coins:
            bot.send_message(chat_id, "Failed to get top coins.")
            return
        markup = types.InlineKeyboardMarkup()
        message = "🏆 <b>Top 10 Coins:</b>\n\n"
        for coin in coins:
            message += f"- {coin['name']} (${coin['current_price']})\n"
            markup.add(types.InlineKeyboardButton(coin['name'], callback_data=coin['id']))
        bot.send_message(chat_id, message, reply_markup=markup)
        return

    if text == "💰 price":
        bot.send_message(chat_id, "Send coin name or symbol (e.g., bitcoin, solana, eth)")
        user_state[chat_id] = "price"
        return

    if text == "🔎 search":
        bot.send_message(chat_id, "Send coin name to search")
        user_state[chat_id] = "search"
        return

    if text == "ℹ️ about":
        bot.send_message(
            chat_id,
            "ℹ️ <b>Crypto Trending Bot v2</b>\n"
            "Source: CoinGecko API\n"
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
            coin_query = text.replace(" ", "-")
            data = get_price(coin_query)
            if coin_query in data:
                price = data[coin_query]["usd"]
                bot.send_message(chat_id, f"💰 <b>{coin_query.upper()}</b> price: <b>${price}</b>")
            else:
                bot.send_message(chat_id, "❌ Coin not found. Try: bitcoin, ethereum, solana")
            user_state.pop(chat_id)
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
            user_state.pop(chat_id)
            return

    # ===== Default =====
    bot.send_message(chat_id, "Please use the menu buttons.", reply_markup=main_menu())

# ================== RUN BOT ==================
print("Crypto Bot v2 is running...")
bot.infinity_polling(skip_pending=True)
