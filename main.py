from flask import Flask
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time

# --- CẤU HÌNH HỆ THỐNG ---
app = Flask('')
@app.route('/')
def home(): return "Bot Hunter Pro is Running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

WATCHING_CHANNELS = [] 
ACTIVE_CLIENTS = {} 

TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": False})
    except:
        pass

# --- LOGIC THEO DÕI TIKTOK ---
async def start_tracking(username):
    if username in ACTIVE_CLIENTS: return
    
    clean_username = username.replace("@", "")
    client = TikTokLiveClient(unique_id=clean_username)
    ACTIVE_CLIENTS[username] = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã kết nối:</b> @{clean_username}")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        # Lấy thời gian chờ của rương (thường tính bằng giây)
        wait_time = event.envelope.wait_time if hasattr(event, 'envelope') else "Không xác định"
        
        # Tạo đường link trực tiếp đến phiên Live
        live_link = f"https://www.tiktok.com/@{clean_username}/live"
        
        msg = (
            f"🎁 <b>PHÁT HIỆN RƯƠNG MỚI!</b>\n\n"
            f"👤 <b>Kênh:</b> @{clean_username}\n"
            f"⏳ <b>Mở sau:</b> {wait_time} giây\n"
            f"🔗 <b>Link:</b> <a href='{live_link}'>BẤM VÀO ĐÂY ĐỂ VÀO LIVE</a>\n\n"
            f"<i>Ghi chú: Hãy vào nhanh để kịp đếm ngược!</i>"
        )
        print(f"Phát hiện rương tại @{clean_username}")
        send_tele(msg)

    try:
        await client.start()
    except Exception as e:
        print(f"Lỗi kênh {username}: {e}")
        ACTIVE_CLIENTS.pop(username, None)

# --- ĐIỀU KHIỂN QUA TELEGRAM ---
def check_telegram_updates():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(url).json()
            if "result" in response:
                for update in response["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        
                        if text.startswith("@") or (len(text) > 2 and " " not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang thử kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target), loop)
                        
                        elif text == "/list":
                            list_txt = "\n".join(ACTIVE_CLIENTS.keys())
                            send_tele(f"📝 Danh sách đang theo dõi:\n{list_txt if list_txt else 'Chưa theo dõi kênh nào'}")
        except Exception as e:
            print(f"Lỗi Tele: {e}")
        time.sleep(2)

# --- KHỞI CHẠY ---
loop = asyncio.new_event_loop()
def run_async_loop(loop):
    asyncio.set_event_loop(loop)
    for channel in WATCHING_CHANNELS:
        loop.create_task(start_tracking(channel))
    loop.run_forever()

if __name__ == '__main__':
    send_tele("🚀 <b>Bot Săn Rương đã sẵn sàng!</b>\nGửi ID TikTok để bắt đầu.")
    Thread(target=run).start() 
    Thread(target=check_telegram_updates).start()
    run_async_loop(loop)
