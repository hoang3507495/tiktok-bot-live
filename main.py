from flask import Flask
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time

# --- CẤU HÌNH WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot X-Ray is Active!"

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
        send_tele(f"✅ <b>Đã vào phòng:</b> @{clean_name}\nĐang bật máy quét X-Quang...")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            # LẤY TOÀN BỘ DỮ LIỆU THÔ (RAW DATA)
            # Quét tất cả các thuộc tính bên trong gói tin rương/túi
            raw_dict = str(vars(event))
            
            msg = (f"🛠 <b>[X-QUANG] BẮT ĐƯỢC GÓI TIN!</b>\n\n"
                   f"👤 <b>Kênh:</b> @{clean_name}\n"
                   f"🔍 <b>DỮ LIỆU GỐC TỪ TIKTOK:</b>\n"
                   f"<code>{raw_dict[:1500]}</code>\n\n"
                   f"<i>👆 Hãy copy đoạn mã tiếng Anh loằng ngoằng ở trên gửi cho tôi!</i>")
            send_tele(msg)
        except Exception as e:
            send_tele(f"⚠️ Lỗi trích xuất dữ liệu: {e}")

    try:
        await client.start()
    except Exception as e:
        ACTIVE_CLIENTS.pop(username, None)
        send_tele(f"❌ <b>Mất kết nối với:</b> @{clean_name}")

# --- QUÉT LỆNH TELEGRAM ---
def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống X-Quang đã sẵn sàng!</b>\nNhắn <code>@ten_kenh</code> để quét dữ liệu.")
    
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
                            status = "📝 <b>Danh sách:</b>\n" + "\n".join([f"• {n}" for n in names]) if names else "Trống"
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
