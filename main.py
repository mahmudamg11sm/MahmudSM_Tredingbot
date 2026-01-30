import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from tradingview_ta import TA_Handler, Interval
import nest_asyncio

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

COINS = sorted([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
])

TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

USERS_FILE = "users.txt"

# ================= HELPERS =================
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE) as f:
        return [int(x) for x in f.read().splitlines() if x.isdigit()]

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            f.write("\n".join(map(str, users)))

async def is_user_in_channel(context, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= SIGNAL LOGIC =================
def build_signal(rec, price):
    if rec == "STRONG_BUY":
        return {
            "rec": "BUY",
            "entry": price,
            "sl": price * 0.80,
            "tp1": price * 1.50,
            "tp2": price * 1.75,
            "tp3": price * 2.00
        }
    else:
        return {
            "rec": "SELL",
            "entry": price,
            "sl": price * 1.20,
            "tp1": price * 0.50,
            "tp2": price * 0.25,
            "tp3": price * 0.00
        }

def get_signal(symbol, exchange):
    for tf_name, tf in TIMEFRAMES.items():
        try:
            handler = TA_Handler(symbol=symbol, screener="crypto", exchange=exchange, interval=tf)
            analysis = handler.get_analysis()
            rec = analysis.summary["RECOMMENDATION"]
            if rec in ["STRONG_BUY", "STRONG_SELL"]:
                price = float(analysis.indicators["close"])
                sig = build_signal(rec, price)
                sig.update({"symbol": symbol, "tf": tf_name, "exchange": exchange})
                return sig
        except:
            continue
    return None

def get_multi_exchange_signal(symbol):
    for ex in ["BINANCE","BYBIT"]:
        sig = get_signal(symbol, ex)
        if sig:
            return sig
    return None

# ================= COINS BUTTON =================
def coins_keyboard(page=0, per_page=9):
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

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")]])
        await update.message.reply_text("Da fari ka shiga channel:", reply_markup=btn)
        return

    await update.message.reply_text("Select coin:", reply_markup=coins_keyboard())

async def coin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("coin:"):
        symbol = query.data.split(":")[1]
        sig = get_multi_exchange_signal(symbol)
        if not sig:
            await query.edit_message_text(f"⚠️ Signal for {symbol} is not STRONG or unavailable.")
            return
        msg = f"📊 SIGNAL {sig['symbol']} ({sig['tf']})\n📈 {sig['rec']} @ {sig['exchange']}\n🎯 Entry: {sig['entry']:.4f}\n🛑 SL: {sig['sl']:.4f}\n💰 TP1: {sig['tp1']:.4f}\n💰 TP2: {sig['tp2']:.4f}\n💰 TP3: {sig['tp3']:.4f}"
        await query.edit_message_text(msg)
    elif query.data.startswith("page:"):
        page = int(query.data.split(":")[1])
        await query.edit_message_text("Select coin:", reply_markup=coins_keyboard(page))

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    text = update.message.text.upper().strip()
    if not text.endswith("USDT"):
        text += "USDT"

    sig = get_multi_exchange_signal(text)
    if not sig:
        await update.message.reply_text("⚠️ Signal ba STRONG ba ko babu.")
        return

    msg = f"📊 SIGNAL {sig['symbol']} ({sig['tf']})\n📈 {sig['rec']} @ {sig['exchange']}\n🎯 Entry: {sig['entry']:.4f}\n🛑 SL: {sig['sl']:.4f}\n💰 TP1: {sig['tp1']:.4f}\n💰 TP2: {sig['tp2']:.4f}\n💰 TP3: {sig['tp3']:.4f}"
    await update.message.reply_text(msg)

# ================= ADMIN =================
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_users()
    await update.message.reply_text(f"Total users: {len(users)}\nIDs:\n{users}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    users = load_users()
    for uid in users:
        try:
            await context.bot.send_message(uid, msg)
        except:
            pass
    await update.message.reply_text("✅ Broadcast sent!")

# ================= AUTO POST =================
async def auto_post(app):
    sent = set()
    while True:
        for coin in COINS:
            sig = get_multi_exchange_signal(coin)
            if not sig:
                continue
            key = f"{coin}-{sig['tf']}-{sig['rec']}"
            if key in sent:
                continue
            msg = f"🚨 NEW SIGNAL\n{sig['symbol']} ({sig['tf']})\n{sig['rec']} @ {sig['exchange']}\nEntry: {sig['entry']:.4f}"
            try:
                await app.bot.send_message(CHANNEL_USERNAME, msg)
                sent.add(key)
            except:
                pass
        await asyncio.sleep(14400)  # 4H

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coin_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))

    # Start auto_post in background
    asyncio.create_task(auto_post(app))

    # Run bot polling
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(main())
