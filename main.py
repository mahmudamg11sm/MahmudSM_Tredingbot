import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

# Timeframes
TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

# Coins list (starter pack)
COINS = sorted([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
    "AVAXUSDT","MATICUSDT","DOTUSDT","LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT",
    "UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT","SUIUSDT"
])

# Winrate storage
WINRATE = {}  # {"BTCUSDT": {"win":0,"loss":0,"neutral":0}}

logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def coins_keyboard(page=0, per_page=15):
    start = page * per_page
    end = start + per_page
    chunk = COINS[start:end]

    keyboard = []
    row = []

    for i, coin in enumerate(chunk, 1):
        row.append(InlineKeyboardButton(coin.replace("USDT",""), callback_data=f"coin:{coin}"))
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if end < len(COINS):
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))

    if nav:
        keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)

def get_signal(symbol: str, strong_only=True):
    """Return STRONG signals across 1H, 4H, 1D"""
    summary = {}
    for tf_name, tf in TIMEFRAMES.items():
        handler = TA_Handler(
            symbol=symbol,
            screener="crypto",
            exchange="BYBIT",
            interval=tf
        )
        analysis = handler.get_analysis().summary
        rec = analysis["RECOMMENDATION"]
        if strong_only and rec not in ["STRONG_BUY", "STRONG_SELL"]:
            rec = "NEUTRAL"
        summary[tf_name] = rec
    return summary
    # ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Na shiga", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"Don amfani da bot, sai ka shiga channel ɗinmu:\n{CHANNEL_USERNAME}",
            reply_markup=btn
        )
        return

    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\nZaɓi coin ko ka rubuta sunansa:",
        reply_markup=coins_keyboard(0)
    )

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_in_channel(context, query.from_user.id):
        await query.edit_message_text("✅ An tabbatar! Zaɓi coin:", reply_markup=coins_keyboard(0))
    else:
        await query.answer("❌ Har yanzu baka shiga channel ba!", show_alert=True)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = " ".join(context.args)
    for user_id in WINRATE.keys():  # WINRATE keys store all users interacted
        try:
            await context.bot.send_message(user_id, text)
        except:
            continue
    await update.message.reply_text("✅ Broadcast sent!")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = list(WINRATE.keys())
    await update.message.reply_text(f"👥 Total users: {len(users)}\n{users}")

# ================= CALLBACKS =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("page:"):
        page = int(data.split(":")[1])
        await query.edit_message_reply_markup(reply_markup=coins_keyboard(page))
    elif data.startswith("coin:"):
        symbol = data.split(":")[1]
        signals = get_signal(symbol)
        text = f"📊 Signals for {symbol}\n\n"
        for tf, rec in signals.items():
            text += f"{tf}: {rec}\n"
        await query.edit_message_text(text)

# ================= SEARCH =================
async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(f"Da fari sai ka shiga {CHANNEL_USERNAME}")
        return
    text = update.message.text.upper().strip()
    if not text.endswith("USDT"):
        text += "USDT"
    signals = get_signal(text)
    msg = f"📊 Signals for {text}\n"
    for tf, rec in signals.items():
        msg += f"{tf}: {rec}\n"
    # Track users
    if user_id not in WINRATE:
        WINRATE[user_id] = {"win":0,"loss":0,"neutral":0}
    await update.message.reply_text(msg)

# ================= AUTO-POST TASK =================
async def auto_scan_and_post(app):
    """Auto post strong 4H signals to channel every 4H"""
    for coin in COINS:
        signals = get_signal(coin)
        rec_4h = signals["4H"]
        if rec_4h in ["STRONG_BUY", "STRONG_SELL"]:
            text = f"📊 {coin} (4H STRONG signal)\nRecommendation: {rec_4h}\n⏰ {datetime.utcnow()} UTC"
            try:
                await app.bot.send_message(CHANNEL_USERNAME, text)
            except Exception as e:
                logging.warning(f"Cannot send {coin}: {e}")

# ================= MAIN =================
async def main():
    logging.info("Dynamic Auto Signal Bot PRO yana gudana...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", list_users))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))

    # Search
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # Background task: auto 4H signal post
    async def background_task():
        while True:
            await auto_scan_and_post(app)
            await asyncio.sleep(14400)  # 4 hours
    app.create_task(background_task())

    # Start bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.idle()

# ================= RUN =================
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # avoids "event loop already running"
    asyncio.run(main())
