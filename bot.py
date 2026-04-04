import requests
import time
import json
from datetime import datetime, timedelta
import threading

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8773493912:AAHPxOkxd_x7Pd5LhuEmzKaZEIQxRTeaP8Y"
CHAT_ID = "1728319803"

# Dữ liệu lưu trữ
tracked_coins = {}
alerts = {}

# ==================== HÀM LẤY GIÁ ====================
def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

# ==================== GỬI TIN NHẮN ====================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
    except:
        pass

# ==================== XỬ LÝ LỆNH ====================
def process_command(chat_id, text):
    if not text or chat_id != int(CHAT_ID):
        if chat_id != int(CHAT_ID):
            send_message(chat_id, "⚠️ Bot chỉ phục vụ chủ nhân!")
        return
    
    cmd = text.split()[0].lower() if text else ""
    args = text.split()[1:] if len(text.split()) > 1 else []
    
    if cmd == '/start' or cmd == '/help':
        send_message(chat_id, 
            "🤖 <b>BOT CẢNH BÁO GIÁ MEXC</b>\n\n"
            "/add BTCUSDT - Thêm coin\n"
            "/list - Xem danh sách\n"
            "/alert BTCUSDT 5 10 - Tạo cảnh báo\n"
            "/alerts - Xem cảnh báo\n"
            "/remove_alert &lt;id&gt; - Xóa cảnh báo\n"
            "/reset - Reset tất cả")
    
    elif cmd == '/add':
        if not args:
            send_message(chat_id, "⚠️ /add BTCUSDT")
            return
        symbol = args[0].upper()
        price = get_price(symbol)
        if not price:
            send_message(chat_id, f"❌ Không tìm thấy {symbol}")
            return
        tracked_coins[symbol] = price
        send_message(chat_id, f"✅ Đã thêm {symbol}\n💰 {price:,.2f} USDT")
    
    elif cmd == '/list':
        if not tracked_coins:
            send_message(chat_id, "📭 Chưa có coin")
            return
        msg = "📋 <b>DANH SÁCH COIN</b>\n\n"
        for s in tracked_coins:
            p = get_price(s)
            if p:
                msg += f"💰 {s}: {p:,.2f} USDT\n"
        send_message(chat_id, msg)
    
    elif cmd == '/alert':
        if len(args) < 3:
            send_message(chat_id, "⚠️ /alert BTCUSDT 5 10")
            return
        symbol = args[0].upper()
        try:
            percent = float(args[1])
            minutes = int(args[2])
        except:
            send_message(chat_id, "❌ Sai định dạng số")
            return
        price = get_price(symbol)
        if not price:
            send_message(chat_id, f"❌ Không tìm thấy {symbol}")
            return
        aid = str(int(time.time()))
        alerts[aid] = {
            'symbol': symbol, 'percent': percent, 'minutes': minutes,
            'base_price': price, 'created_at': datetime.now()
        }
        send_message(chat_id, f"✅ Đã tạo cảnh báo {symbol}\n⚠️ {percent}% / {minutes}p\n🆔 {aid}")
    
    elif cmd == '/alerts':
        if not alerts:
            send_message(chat_id, "📭 Chưa có cảnh báo")
            return
        msg = "🔔 <b>CẢNH BÁO</b>\n\n"
        for aid, a in alerts.items():
            msg += f"🆔 <code>{aid}</code>\n📊 {a['symbol']} | {a['percent']}% / {a['minutes']}p\n💰 {a['base_price']:,.2f} USDT\n➖➖➖\n"
        send_message(chat_id, msg)
    
    elif cmd == '/remove_alert':
        if not args:
            send_message(chat_id, "⚠️ /remove_alert 123456")
            return
        if args[0] in alerts:
            del alerts[args[0]]
            send_message(chat_id, f"✅ Đã xóa {args[0]}")
        else:
            send_message(chat_id, f"❌ Không tìm thấy {args[0]}")
    
    elif cmd == '/reset':
        tracked_coins.clear()
        alerts.clear()
        send_message(chat_id, "🔄 Đã reset toàn bộ!")

# ==================== KIỂM TRA CẢNH BÁO ====================
def alert_worker():
    while True:
        try:
            now = datetime.now()
            to_remove = []
            for aid, a in alerts.items():
                if now - a['created_at'] > timedelta(minutes=a['minutes']):
                    to_remove.append(aid)
                    continue
                current = get_price(a['symbol'])
                if current:
                    change = abs((current - a['base_price']) / a['base_price']) * 100
                    if change >= a['percent']:
                        direction = "📈 TĂNG" if current > a['base_price'] else "📉 GIẢM"
                        send_message(CHAT_ID, 
                            f"🚨 <b>CẢNH BÁO {a['symbol']}</b>\n{direction} {change:.2f}%\n💰 {a['base_price']:,.2f} → {current:,.2f} USDT")
                        to_remove.append(aid)
            for aid in to_remove:
                if aid in alerts:
                    del alerts[aid]
        except:
            pass
        time.sleep(30)

# ==================== NHẬN TIN NHẮN ====================
def main():
    # Chạy thread kiểm tra cảnh báo
    threading.Thread(target=alert_worker, daemon=True).start()
    
    print("🤖 Bot đang chạy...")
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            r = requests.get(url, params={'offset': last_id + 1, 'timeout': 30}, timeout=35)
            for u in r.json().get('result', []):
                if 'message' in u and 'text' in u['message']:
                    process_command(u['message']['chat']['id'], u['message']['text'])
                if u['update_id'] > last_id:
                    last_id = u['update_id']
        except:
            pass
        time.sleep(1)

if __name__ == "__main__":
    main()
