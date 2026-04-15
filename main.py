from flask import Flask
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time
import re  # Thư viện quét từ khóa siêu mạnh

# --- CẤU HÌNH WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Hunter Pro v4 is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CẤU HÌNH CHÍNH ---
TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

# --- THEO DÕI TIKTOK ---
async def start_tracking(username, loop):
    if username in ACTIVE_CLIENTS:
        return
    
    clean_name = username.replace("@", "").strip()
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã vào phòng:</b> @{clean_name}\nĐang trực rương...")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            # Chuyển toàn bộ dữ liệu rương thành văn bản để quét
            raw_data = str(vars(event))
            
            # 1. Quét tìm Số Xu
            coins = "0"
            # Thử tìm trong chuỗi string_value (giống cái X-Quang bạn gửi)
            match_coins = re.search(r"string_value='(\d+)'", raw_data)
            if not match_coins:
                # Nếu không có, tìm bằng các từ khóa dự phòng của TikTok
                match_coins = re.search(r"['\"]?(?:coin|coins|diamond_count)['\"]?[:=]\s*(\d+)", raw_data, re.IGNORECASE)
            
            if match_coins:
                coins = match_coins.group(1)

            # BỎ QUA RƯƠNG ẢO HOẶC 0 XU (Chống spam)
            if coins == "0": 
                return

            # 2. Quét tìm Số Người Nhặt
            people = "..."
            match_people = re.search(r"['\"]?(?:can_win_count|people_count|total_people_count)['\"]?[:=]\s*(\d+)", raw_data, re.IGNORECASE)
            if match_people:
                people = match_people.group(1)
                
            # 3. Quét tìm Thời gian chờ (giây)
            wait_time = "..."
            match_time = re.search(r"['\"]?(?:wait_time|time)['\"]?[:=]\s*(\d+)", raw_data, re.IGNORECASE)
            if match_time and len(match_time.group(1)) < 5: # Lọc bỏ các dãy số timestamp quá dài
                wait_time = match_time.group(1)

            # GỬI TIN NHẮN CHUẨN ĐẸP VỀ TELEGRAM
            msg = (f"🎁 <b>PHÁT HIỆN RƯƠNG!</b>\n\n"
                   f"👤 <b>Kênh:</b> @{clean_name}\n"
                   f"💰 <b>Trị giá:</b> {coins} Xu / {people} người\n"
                   f"⏳ <b>Chờ mở:</b> {wait_time}s\n"
                   f"🔗 <a href='https://www.tiktok.com/@{clean_name}/live'>BẤM VÀO ĐÂY NHẶT NGAY</a>")
            send_tele(msg)
            
        except Exception as e:
            pass # Lỗi đọc thì bỏ qua, không làm phiền Telegram

    try:
        await client.start()
    except Exception as e:
        ACTIVE_CLIENTS.pop(username, None)

# --- QUÉT LỆNH TELEGRAM ---
def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống Săn Rương v4 Sẵn Sàng!</b>\n\n- Nhắn <code>@ten_kenh</code> để săn.\n- Nhắn <code>/list</code> để xem danh sách.")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            if "result" in r:
                for update in r["result"]:
                    last_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        
                        if text == "/list":
                            names = list(ACTIVE_CLIENTS.keys())
                            if names:
                                status = "📝 <b>Danh sách đang theo dõi:</b>\n" + "\n".join([f"• {n}" for n in names])
                            else:
                                status = "📝 Hiện tại chưa theo dõi kênh nào."
                            send_tele(status)
                        
                        elif text.startswith("@") or (len(text) > 2 and " " not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
        except:
            time.sleep(2)
        time.sleep(1)

# --- KHỞI CHẠY TỔNG HỢP ---
if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    
    tiktok_loop = asyncio.new_event_loop()
    def run_tiktok_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    Thread(target=run_tiktok_loop, args=(tiktok_loop,), daemon=True).start()
    
    tele_worker(tiktok_loop)
