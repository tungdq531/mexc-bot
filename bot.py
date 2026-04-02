import asyncio
import aiohttp
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import time
import json
import os

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8773493912:AAHPxOkxd_x7Pd5LhuEmzKaZEIQxRTeaP8Y"  # THAY TOKEN CỦA BẠN
CHAT_ID = "1728319803"  # THAY CHAT_ID CỦA BẠN

# Dữ liệu lưu trữ
tracked_coins = {}
alerts = {}

# ==================== HÀM LẤY GIÁ ====================
async def get_price(symbol):
    """Lấy giá từ MEXC API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                return None
    except Exception as e:
        print(f"Lỗi lấy giá {symbol}: {e}")
        return None

# ==================== LỆNH BOT ====================
async def start(update, context):
    await update.message.reply_text(
        "🤖 BOT CẢNH BÁO GIÁ MEXC\n\n"
        "📌 LỆNH:\n"
        "/add <symbol> - Thêm coin (VD: /add BTCUSDT)\n"
        "/list - Xem danh sách coin\n"
        "/alert <symbol> <%> <phút> - Tạo cảnh báo\n"
        "/alerts - Xem cảnh báo\n"
        "/remove_alert <id> - Xóa cảnh báo\n"
        "/reset - Reset toàn bộ"
    )

async def add_coin(update, context):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: /add BTCUSDT")
        return
    
    symbol = context.args[0].upper()
    price = await get_price(symbol)
    
    if not price:
        await update.message.reply_text(f"❌ Không tìm thấy {symbol} trên MEXC")
        return
    
    tracked_coins[symbol] = price
    await update.message.reply_text(
        f"✅ Đã thêm {symbol}\n"
        f"💰 Giá hiện tại: {price:,.2f} USDT"
    )

async def list_coins(update, context):
    if not tracked_coins:
        await update.message.reply_text("📭 Chưa có coin nào. Dùng /add để thêm.")
        return
    
    msg = "📋 DANH SÁCH COIN THEO DÕI\n\n"
    for symbol in tracked_coins:
        current = await get_price(symbol)
        if current:
            msg += f"💰 {symbol}: {current:,.2f} USDT\n"
        else:
            msg += f"❌ {symbol}: Không lấy được giá\n"
    
    await update.message.reply_text(msg)

async def add_alert(update, context):
    if len(context.args) < 3:
        await update.message.reply_text("⚠️ Cú pháp: /alert BTCUSDT 5 10\n(5% trong 10 phút)")
        return
    
    symbol = context.args[0].upper()
    percent = float(context.args[1])
    minutes = int(context.args[2])
    
    # Kiểm tra coin tồn tại
    current_price = await get_price(symbol)
    if not current_price:
        await update.message.reply_text(f"❌ Không tìm thấy {symbol}")
        return
    
    # Tạo ID cảnh báo
    alert_id = str(int(time.time()))
    
    alerts[alert_id] = {
        'symbol': symbol,
        'percent': percent,
        'minutes': minutes,
        'base_price': current_price,
        'created_at': datetime.now()
    }
    
    await update.message.reply_text(
        f"✅ Đã tạo cảnh báo\n\n"
        f"📊 Coin: {symbol}\n"
        f"⚠️ Ngưỡng: {percent}%\n"
        f"⏰ Thời gian: {minutes} phút\n"
        f"💰 Giá tham chiếu: {current_price:,.2f} USDT\n\n"
        f"🆔 ID: {alert_id}"
    )

async def list_alerts(update, context):
    if not alerts:
        await update.message.reply_text("📭 Chưa có cảnh báo nào. Dùng /alert để tạo.")
        return
    
    msg = "🔔 DANH SÁCH CẢNH BÁO\n\n"
    for aid, alert in alerts.items():
        time_left = alert['minutes'] - (datetime.now() - alert['created_at']).total_seconds() / 60
        msg += f"🆔 <code>{aid}</code>\n"
        msg += f"📊 {alert['symbol']} | {alert['percent']}% / {alert['minutes']}p\n"
        msg += f"💰 {alert['base_price']:,.2f} USDT\n"
        msg += f"⏰ Còn: {int(time_left)} phút\n"
        msg += "➖➖➖➖➖➖\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')

async def remove_alert(update, context):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: /remove_alert 1734567890")
        return
    
    alert_id = context.args[0]
    if alert_id in alerts:
        del alerts[alert_id]
        await update.message.reply_text(f"✅ Đã xóa cảnh báo {alert_id}")
    else:
        await update.message.reply_text(f"❌ Không tìm thấy cảnh báo {alert_id}")

async def reset_all(update, context):
    global tracked_coins, alerts
    tracked_coins = {}
    alerts = {}
    await update.message.reply_text("🔄 Đã reset toàn bộ dữ liệu!")

# ==================== KIỂM TRA CẢNH BÁO ====================
async def check_alerts():
    """Chạy nền, kiểm tra cảnh báo mỗi 30 giây"""
    bot = Bot(token=BOT_TOKEN)
    
    while True:
        try:
            current_time = datetime.now()
            expired_alerts = []
            
            for aid, alert in alerts.items():
                # Kiểm tra hết thời gian
                time_passed = current_time - alert['created_at']
                if time_passed > timedelta(minutes=alert['minutes']):
                    expired_alerts.append(aid)
                    continue
                
                # Lấy giá hiện tại
                current_price = await get_price(alert['symbol'])
                if current_price:
                    change = abs((current_price - alert['base_price']) / alert['base_price']) * 100
                    
                    if change >= alert['percent']:
                        direction = "📈 TĂNG" if current_price > alert['base_price'] else "📉 GIẢM"
                        msg = (
                            f"🚨 <b>CẢNH BÁO GIÁ</b>\n\n"
                            f"📊 <b>{alert['symbol']}</b>\n"
                            f"{direction} <b>{change:.2f}%</b> (ngưỡng {alert['percent']}%)\n\n"
                            f"💰 Giá cũ: {alert['base_price']:,.2f} USDT\n"
                            f"💰 Giá mới: {current_price:,.2f} USDT\n"
                            f"⏰ Trong: {alert['minutes']} phút"
                        )
                        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
                        expired_alerts.append(aid)
            
            # Xóa cảnh báo đã hết hạn hoặc đã kích hoạt
            for aid in expired_alerts:
                if aid in alerts:
                    del alerts[aid]
            
        except Exception as e:
            print(f"Lỗi kiểm tra cảnh báo: {e}")
        
        await asyncio.sleep(30)  # Kiểm tra mỗi 30 giây

# ==================== CHẠY BOT ====================
async def main():
    # Tạo application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Đăng ký lệnh
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_coin))
    app.add_handler(CommandHandler("list", list_coins))
    app.add_handler(CommandHandler("alert", add_alert))
    app.add_handler(CommandHandler("alerts", list_alerts))
    app.add_handler(CommandHandler("remove_alert", remove_alert))
    app.add_handler(CommandHandler("reset", reset_all))
    
    # Chạy kiểm tra cảnh báo song song
    asyncio.create_task(check_alerts())
    
    # Chạy bot
    print("🤖 Bot đang chạy...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())