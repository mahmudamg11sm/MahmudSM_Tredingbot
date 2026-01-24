import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
)
from tradingview_ta import TA_Handler, Interval

# ====== CONFIG ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # Example: @YourChannel
ADMIN_ID = int(os.environ.get("CHAT_ID"))  # Your Telegram ID

# ====== LOGGING ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== COINS ======
COINS = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE"]

# ====== SOCIAL BUTTONS ======
def social_buttons():
    buttons = [
        [InlineKeyboardButton("Telegram", url="https://t.me/Mahmudsm1")],
        [InlineKeyboardButton("X", url="https://x.com/Mahmud_sm1")],
        [InlineKeyboardButton("Facebook", url="https://www.facebook.com/profile.php?id=61580620438042")]
    ]
    return InlineKeyboardMarkup(buttons)

# ====== COINS BUTTONS ======
def coins_buttons():
    keyboard = []
    row = []
    for i, coin in enumerate(COINS, 1):
        row.append(InlineKeyboardButton(coin, callback_data=f"coin_{coin}"))
        if i % 4 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# ====== JOIN CHANNEL CHECK ======
async def check_membership(user_id, application):
    try:
        member = await application.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status != "left"
    except:
        return False

# ====== START COMMAND ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    joined = await check_membership(user_id, context.application)
    
    if not joined:
        await update.message.reply_text(
            f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}"
        )
        return
    
    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nBi mu a shafukanmu:",
        reply_markup=social_buttons()
    )
    await update.message.reply_text(
        "Zaɓi coin daga kasa don samun Price/Signal:",
        reply_markup=coins_buttons()
    )

# ====== CALLBACK QUERY HANDLER ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("coin_"):
        coin = data.split("_")[1]
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BINANCE",
            interval=Interval.INTERVAL_1_DAY
        )
        try:
            analysis = handler.get_analysis()
            trend = analysis.summary["RECOMMENDATION"]
            price_now = analysis.indicators["close"]
            high = analysis.indicators.get("high", price_now)
            low = analysis.indicators.get("low", price_now)
            text = (
                f"Coin: {coin}\n"
                f"💰 Price yanzu: ${price_now}\n"
                f"📊 Trend: {trend}\n"
                f"🎯 Hasashe:\n ~Hawa: ${high}\n ~Sauka: ${low}\n"
                f"⚠ Wannan hasashe ne na analysis kawai."
            )
            await query.edit_message_text(text)
        except Exception as e:
            await query.edit_message_text(f"Ba a samu coin ba: {coin}")

# ====== BROADCAST ======
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Ba kai admin bane.")
        return

    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Rubuta sako bayan /broadcast")
        return
    
    # NOTE: You can extend this to all users
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
        await update.message.reply_text("Sako an aika!")
    except Exception as e:
        await update.message.reply_text(f"An samu matsala: {e}")

# ====== MAIN ======
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    # CallbackQuery
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Run bot
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import sys

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    # CallbackQuery
    app.add_handler(CallbackQueryHandler(button_handler))

    # Railway / environment da event loop riga yana running
    try:
        # Idan loop riga yana running (Railway), yi run_polling() da sync wrapper
        loop = asyncio.get_event_loop()
        loop.create_task(app.run_polling())
        loop.run_forever()
    except RuntimeError:
        # fallback, idan environment ya bari
        app.run_polling()
