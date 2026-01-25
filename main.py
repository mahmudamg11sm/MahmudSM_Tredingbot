import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from tradingview_ta import TA_Handler, Interval
import nest_asyncio

nest_asyncio.apply()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

COINS = sorted([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT"
])

TIMEFRAMES = {"1H": Interval.INTERVAL_1_HOUR, "4H": Interval.INTERVAL_4_HOURS, "1D": Interval.INTERVAL_1_DAY}

USERS_FILE = "users.txt"

# ================= HELPERS =================
def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            f.write("\n".join(str(u) for u in users))

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE) as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]

async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

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
    if row: keyboard.append(row)

    nav = []
    if start > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if end < len(COINS): nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))
    if nav: keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)

# ================= SIGNAL LOGIC =================
def get_signal(symbol: str, exchanger="BINANCE"):
    for tf_name in ["1H", "4H", "1D"]:
        handler = TA_Handler(symbol=symbol, screener="crypto", exchange=exchanger, interval=TIMEFRAMES[tf_name])
        try:
            analysis = handler.get_analysis()
        except:
            continue
        rec = analysis.summary["RECOMMENDATION"]
        if rec not in ["STRONG_BUY", "STRONG_SELL"]:
            return None
        price = float(analysis.indicators["close"])
        if rec == "STRONG_BUY":
            signal = {"rec": "BUY", "entry": price, "sl": price * 0.97, "tp1": price * 1.05, "tp2": price * 1.12, "tp3": price * 1.30}
        else:
            signal = {"rec": "SELL", "entry": price, "sl": price * 1.03, "tp1": price * 0.95, "tp2": price * 0.88, "tp3": price * 0.70}
        signal["symbol"] = symbol
        signal["tf"] = tf_name
        signal["exchanger"] = exchanger
        return signal
    return None

def get_multi_exchange_signal(symbol):
    # Try Binance first, then Bybit
    sig = get_signal(symbol, "BINANCE")
    if sig: return sig
    sig = get_signal(symbol, "BYBIT")
    return sig

# ================= COMMANDS & CALLBACKS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ I joined", callback_data="check_join")]
        ])
        await update.message.reply_text(f"Join {CHANNEL_USERNAME} first", reply_markup=btn)
        return
    await update.message.reply_text("Select coin:", reply_markup=coins_keyboard())

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_in_channel(context, query.from_user.id):
        await query.edit_message_text("✅ Verified! Select coin:", reply_markup=coins_keyboard())
    else:
        await query.answer("❌ Not joined channel yet!", show_alert=True)

async def coin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.split(":")[1]
    sig = get_multi_exchange_signal(symbol)
    if not sig:
        await query.edit_message_text(f"⚠️ Signal for {symbol} is not STRONG or unavailable.")
        return
    msg = f"""
📊 Signal {sig['symbol']} ({sig['tf']}) {sig['exchanger']}
📈 {sig['rec']}
🎯 Entry: {sig['entry']:.4f} | SL: {sig['sl']:.4f}
💰 TP1: {sig['tp1']:.4f} | TP2: {sig['tp2']:.4f} | TP3: {sig['tp3']:.4f}
"""
    await query.edit_message_text(msg)

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(f"Join {CHANNEL_USERNAME} first")
        return
    text = update.message.text.upper()
    if not text.endswith("USDT"): text += "USDT"
    sig = get_multi_exchange_signal(text)
    if not sig:
        await update.message.reply_text(f"⚠️ Signal for {text} not STRONG or unavailable")
        return
    if text not in COINS:
        COINS.append(text)
        COINS.sort()
    msg = f"""
📊 Signal {sig['symbol']} ({sig['tf']}) {sig['exchanger']}
📈 {sig['rec']}
🎯 Entry: {sig['entry']:.4f} | SL: {sig['sl']:.4f}
💰 TP1: {sig['tp1']:.4f} | TP2: {sig['tp2']:.4f} | TP3: {sig['tp3']:.4f}
"""
    await update.message.reply_text(msg)

# ================= ADMIN =================
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users = load_users()
    await update.message.reply_text(f"Total users: {len(users)}\nIDs:\n{users}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    users = load_users()
    for uid in users:
        try: await context.bot.send_message(uid, msg)
        except: pass
    await update.message.reply_text("✅ Broadcast sent!")

# ================= AUTO POST 4H STRONG =================
async def auto_post_4h(app):
    while True:
        for coin in COINS:
            sig = get_multi_exchange_signal(coin)
            if not sig: continue
            msg = f"""
📊 AUTO 4H STRONG SIGNAL
📈 {sig['symbol']} ({sig['tf']}) {sig['exchanger']}
🎯 Entry: {sig['entry']:.4f} | SL: {sig['sl']:.4f}
💰 TP1: {sig['tp1']:.4f} | TP2: {sig['tp2']:.4f} | TP3: {sig['tp3']:.4f}
"""
            try:
                await app.bot.send_message(CHANNEL_USERNAME, msg)
            except: pass
        await asyncio.sleep(14400)  # 4H

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(coin_callback, pattern="coin:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))

    asyncio.create_task(auto_post_4h(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
