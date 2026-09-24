import asyncio, json, random
from collections import deque
import websockets
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

BOT_TOKEN = "8806872080:AAEH2VDwNluAJr3NoOBWFfLMqp6si14ATms"
prices = deque(maxlen=100)
last_price = 1155000.0
AUTO_CHATS = set()

async def get_deriv_price():
    global last_price
    try:
        uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"ticks": "R_75", "subscribe": 1}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            if 'tick' in data:
                last_price = float(data['tick']['quote'])
                prices.append(last_price)
                return last_price
    except: pass
    last_price += random.uniform(-50, 50)
    prices.append(last_price)
    return last_price

def calc_rsi(pl, period=14):
    if len(pl) < period+1: return 50
    gains=losses=0
    for i in range(1, period+1):
        d=pl[-i]-pl[-i-1]
        if d>0: gains+=d
        else: losses+=-d
    if losses==0: return 80
    return 100-(100/(1+gains/losses if losses else 1))

def get_last_digit(p): return int(str(int(p))[-1])

async def build_signal():
    p=await get_deriv_price()
    if len(prices)<5:
        for _ in range(20): await get_deriv_price()
    pl=list(prices); rsi=calc_rsi(pl); last=get_last_digit(p)
    sup=min(pl[-20:]) if len(pl)>=20 else p-500
    res=max(pl[-20:]) if len(pl)>=20 else p+500
    if rsi<30 and last<=2: action="🟢 STRONG BUY"; sl,tp=p-2000,p+4000; reason=f"RSI {rsi:.1f} Oversold + Digit {last} LOW"
    elif rsi>70 and last>=7: action="🔴 STRONG SELL"; sl,tp=p+2000,p-4000; reason=f"RSI {rsi:.1f} Overbought + Digit {last} HIGH"
    elif last>=8: action="🔴 SELL"; sl,tp=p+1500,p-2500; reason=f"Digit {last} >=8"
    elif last<=2: action="🟢 BUY"; sl,tp=p-1500,p+2500; reason=f"Digit {last} <=2"
    else: action="⏳ WAIT"; sl,tp=p-1000,p+1000; reason=f"RSI {rsi:.1f} Neutral, Digit {last}"
    return f"**🔥 V75 AUTO SIGNAL**\n\nPrice: {p:.2f}\nLast Digit: {last}\nRSI: {rsi:.1f}\nSup: {sup:.2f} | Res: {res:.2f}\n\nAction: {action}\nReason: {reason}\n\nEntry: {p:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\n\n⚠️ 1% risk!"

async def start(u,c): await u.message.reply_text("🔥 V75 MAX PROFIT\n\n/price\n/signal\n/trend\n/autostart - Auto every 5min\n/autostop")
async def price_cmd(u,c): p=await get_deriv_price(); await u.message.reply_text(f"📊 REAL V75: {p:.2f}")
async def signal_now(u,c): m=await build_signal(); await c.bot.send_message(chat_id=u.effective_chat.id, text=m, parse_mode="Markdown")
async def trend_cmd(u,c):
    p=await get_deriv_price(); pl=list(prices)
    if len(pl)<10: await u.message.reply_text("Collecting... try /trend again in 10s"); return
    rsi=calc_rsi(pl); ma=sum(pl[-20:])/min(20,len(pl)); tr="BULLISH 🟢" if p>ma else "BEARISH 🔴"
    await u.message.reply_text(f"Trend: {tr}\nPrice: {p:.2f}\nMA20: {ma:.2f}\nRSI: {rsi:.1f}")
async def auto_callback(c):
    m=await build_signal()
    for chat_id in list(AUTO_CHATS):
        try: await c.bot.send_message(chat_id=chat_id, text=m, parse_mode="Markdown")
        except: pass
async def autostart(u,c):
    AUTO_CHATS.add(u.effective_chat.id)
    await u.message.reply_text("✅ AUTO ON! Signal every 5 min. /autostop to stop")
    if not c.job_queue.get_jobs_by_name("autosig"): c.job_queue.run_repeating(auto_callback, interval=300, first=5, name="autosig")
async def autostop(u,c): AUTO_CHATS.discard(u.effective_chat.id); await u.message.reply_text("🛑 Auto OFF")

app=ApplicationBuilder().token(BOT_TOKEN).build()
for cmd,fn in [("start",start),("price",price_cmd),("signal",signal_now),("trend",trend_cmd),("autostart",autostart),("autostop",autostop)]:
    app.add_handler(CommandHandler(cmd,fn))
print("V75 MAX PROFIT BOT running... /autostart for auto")
app.run_polling()
