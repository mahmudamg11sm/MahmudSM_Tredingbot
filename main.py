import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_USERNAME = "@Mahmudsm1"

TP1_PERCENT = 50
TP2_PERCENT = 75
TP3_PERCENT = 100
SL_PERCENT = 20

COIN_FILE = "coins.txt"

# ================ LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================ HELPERS =================
def load_coins():
    with open(COIN_FILE, "r") as f:
        return [line.strip().upper() for line in f if line.strip()]

COINS = load_coins()

def join_channel_check(update: Update):
    try:
        member = update.effective_chat.get_member(update.effective_user.id)
        return True
    except:
        return False

# ================ COMMANDS =================
def start(update: Update, context: CallbackContext):
    if not join_channel_check(update):
        keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        update.message.reply_text("Join our channel first!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = [
        [InlineKeyboardButton("Search Coin", callback_data="search_coin")],
        [InlineKeyboardButton("Admin Dashboard", callback_data="admin_dashboard")]
    ]
    update.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "search_coin":
        query.edit_message_text("Send coin symbol (e.g., BTCUSDT):")
        context.user_data["awaiting_coin"] = True

    elif data == "admin_dashboard" and update.effective_user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("View Coins", callback_data="view_coins")],
            [InlineKeyboardButton("Reload Coins", callback_data="reload_coins")]
        ]
        query.edit_message_text("Admin Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "view_coins":
        query.edit_message_text("Coins whitelist:\n" + "\n".join(COINS))

    elif data == "reload_coins":
        global COINS
        COINS = load_coins()
        query.edit_message_text("Coins reloaded!")

def handle_message(update: Update, context: CallbackContext):
    if context.user_data.get("awaiting_coin"):
        coin = update.message.text.upper()
        context.user_data["awaiting_coin"] = False
        if coin not in COINS:
            update.message.reply_text(f"{coin} is not in the whitelist.")
            return
        try:
            handler = TA_Handler(
                symbol=coin,
                screener="CRYPTO",
                exchange="BINANCE",
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis().summary
            signal_text = f"{coin} Signal:\nBuy: {analysis['BUY']}\nSell: {analysis['SELL']}\nNeutral: {analysis['NEUTRAL']}"
            signal_text += f"\n\nTP1: +{TP1_PERCENT}%\nTP2: +{TP2_PERCENT}%\nTP3: +{TP3_PERCENT}%\nSL: -{SL_PERCENT}%"
            update.message.reply_text(signal_text)
        except Exception as e:
            update.message.reply_text(f"Error fetching signal: {e}")

# ================ MAIN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    logger.info("Bot started...")
    updater.idle()

if __name__ == "__main__":
    main()
