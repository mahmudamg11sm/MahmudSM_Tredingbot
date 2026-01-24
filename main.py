import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@Mahmudsm1"
ADMIN_ID = 6648308251

# ================= USERS STORAGE =================
USERS = set()

# ================= COINS =================
COINS = [
    "BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "LTCUSDT",
    "DOTUSDT", "LINKUSDT", "BCHUSDT", "UNIUSDT", "MATICUSDT", "ATOMUSDT", "ETCUSDT",
    "XLMUSDT", "FILUSDT", "TRXUSDT", "EOSUSDT", "AAVEUSDT", "ALGOUSDT", "AVAXUSDT",
    "CHZUSDT", "CRVUSDT", "DASHUSDT", "ENJUSDT", "FTMUSDT", "ICPUSDT", "KSMUSDT",
    "NEARUSDT", "QNTUSDT", "RUNEUSDT", "SNXUSDT", "SUSHIUSDT", "THETAUSDT", "VETUSDT",
    "XMRUSDT", "YFIUSDT", "ZECUSDT", "BATUSDT", "1INCHUSDT", "AXSUSDT", "CAKEUSDT",
    "COMPUSDT", "CROUSDT", "DGBUSDT", "EGLDUSDT", "GRTUSDT", "HOTUSDT", "KNCUSDT",
    "LRCUSDT", "MANAUSDT", "NEOUSDT", "OCEANUSDT", "OMGUSDT", "PAXGUSDT", "RENUSDT",
    "RSRUSDT", "SCUSDT", "STORJUSDT", "SXPUSDT", "TFUELUSDT", "TWTUSDT", "UMAUSDT",
    "WAVESUSDT", "XEMUSDT", "XTZUSDT", "ZRXUSDT", "BALUSDT", "BELUSDT", "BNTUSDT",
    "COTIUSDT", "DIAUSDT", "GLMUSDT", "KAVAUSDT", "LINAUSDT", "OXTUSDT", "SRMUSDT",
    "WTCUSDT", "YFIIUSDT", "CTSIUSDT", "SANDUSDT"
]

COINS_PER_PAGE = 16

# ================= SOCIAL BUTTONS =================
def social_buttons():
    keyboard = [
        [InlineKeyboardButton("Telegram", url="https://t.me/Mahmudsm1")],
        [InlineKeyboardButton("X", url="https://x.com/Mahmud_sm1")],
        [InlineKeyboardButton("Facebook", url="https://www.facebook.com/profile.php?id=61580620438042")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= COIN BUTTONS PAGINATION =================
def get_coin_buttons(page: int = 0):
    start = page * COINS_PER_PAGE
    end = start + COINS_PER_PAGE
    coins_slice = COINS[start:end]

    keyboard = []
    row = []
    for i, coin in enumerate(coins_slice, 1):
        row.append(InlineKeyboardButton(coin, callback_data=f"coin_{coin}"))
        if i % 4 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
    if end < len(COINS):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USERS.add(user.id)

    # Channel verification
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ["left", "kicked"]:
            await update.message.reply_text(
                f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}"
            )
            return
    except:
        await update.message.reply_text(
            f"Don amfani da bot, sai ka shiga channel ɗinmu: {CHANNEL_USERNAME}"
        )
        return

    # Greet user
    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nBi mu a shafukanmu:",
        reply_markup=social_buttons()
    )

    # Show first page of coins
    await update.message.reply_text("Zabi coin ko rubuta sunan coin:", reply_markup=get_coin_buttons(0))

# ================= CALLBACK HANDLER =================
async def coin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("coin_"):
        coin = data.split("_")[1]
        await send_coin_price(query.message, coin, context)
    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        await query.message.edit_reply_markup(get_coin_buttons(page))

# ================= MESSAGE HANDLER (SEARCH) =================
async def coin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.upper().replace(" ", "")
    await send_coin_price(update.message, coin, context)

# ================= SEND COIN PRICE + SIGNAL =================
async def send_coin_price(message, coin, context):
    try:
        handler = TA_Handler(
            symbol=coin,
            screener="crypto",
            exchange="BYBIT",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        price = analysis.indicators.get("close", "N/A")
        signal = analysis.summary.get("RECOMMENDATION", "N/A")
        await message.reply_text(f"{coin} Price: {price}\nSignal: {signal}")
    except Exception as e:
        await message.reply_text(f"Ba a samu coin ba: {coin}")

# ================= ADMIN / BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Ba kai bane admin!")
        return
    if not context.args:
        await update.message.reply_text("Rubuta saƙo bayan /broadcast")
        return
    text = " ".join(context.args)
    for user in USERS:
        try:
            await context.bot.send_message(chat_id=user, text=text)
        except:
            continue
    await update.message.reply_text("Broadcast ya tafi!")

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coin_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), coin_search))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("Dynamic Auto Signal Bot v7 yana gudana...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
