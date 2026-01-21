import os
import telebot
from flask import Flask
from threading import Thread

from utils.coins import fetch_top_coins

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

bot = telebot.TeleBot(BOT_TOKEN)

# ================== FLASK KEEP ALIVE ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask).start()

# ================== BOT COMMANDS ==================
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id

    text = (
        "👋 Barka da zuwa Mahmud Crypto Bot\n\n"
        "Zabi abinda kake so 👇"
    )

    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("🏆 Top Coins", callback_data="topcoins")
    markup.add(btn1)

    bot.send_message(chat_id, text, reply_markup=markup)

# ================== CALLBACK HANDLER ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id

    if call.data == "topcoins":
        bot.answer_callback_query(call.id, "⏳ Ana dauko coins...")

        try:
            coins = fetch_top_coins()

            if not coins:
                bot.send_message(chat_id, "❌ Failed to load top coins")
                return

            msg = "🏆 *Top Crypto Coins:*\n\n"

            for i, coin in enumerate(coins, start=1):
                name = coin.get("name", "N/A")
                symbol = coin.get("symbol", "").upper()
                price = coin.get("price", "N/A")

                msg += f"{i}. *{name}* ({symbol}) — ${price}\n"

            bot.send_message(chat_id, msg, parse_mode="Markdown")

        except Exception as e:
            bot.send_message(chat_id, "❌ Error while loading coins")
            print("ERROR:", e)

# ================== START BOT ==================
print("🤖 Bot is running...")
bot.infinity_polling(skip_pending=True)
