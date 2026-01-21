import os
from flask import Flask
from threading import Thread
import telebot

from utils.coins import fetch_top_coins

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Mahmud Crypto Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask).start()

# ================== TELEGRAM BOT ==================

@bot.message_handler(commands=["start"])
def start(message):
    text = "👋 Barka da zuwa *Mahmud Crypto Bot*\n\nZaɓi abinda kake so 👇"

    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("🏆 Top Coins", callback_data="topcoins")
    markup.add(btn1)

    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ================== BUTTON HANDLER ==================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "topcoins":
        bot.answer_callback_query(call.id, "⏳ Ana dauko coins...")

        coins = fetch_top_coins(5)

        if not coins:
            bot.send_message(call.message.chat.id, "❌ Failed to load top coins")
            return

        msg = "🏆 *Top Coins*\n\n"

        i = 1
        for coin in coins:
            msg += (
                f"{i}. *{coin['name']}* ({coin['symbol']})\n"
                f"💰 Price: ${coin['price']}\n"
                f"📊 24h: {coin['change']}%\n\n"
            )
            i += 1

        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

# ================== RUN BOT ==================

print("Bot is running...")
bot.infinity_polling()
