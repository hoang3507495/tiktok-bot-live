from flask import Flask
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os

# --- CẤU HÌNH MÁY THỞ ĐỂ TREO 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy trực tuyến!"

def run():
    # Render yêu cầu chạy trên cổng 8080 hoặc lấy từ môi trường
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CẤU HÌNH BOT TELEGRAM & TIKTOK ---
# Thay thông tin của bạn vào 3 dòng dưới đây
TIKTOK_USERNAME = "@ten_kenh_ban_muon_theo_doi" 
TELEGRAM_TOKEN = "ĐIỀN_TOKEN_BOT_CỦA_BẠN"
TELEGRAM_CHAT_ID = "ĐIỀN_ID_CHAT_CỦA_BẠN"

client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except:
        pass

@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Đã kết nối Live: {event.unique_id}")
    send_tele(f"✅ <b>Bot đã online!</b>\nĐang theo dõi: <code>{event.unique_id}</code>")

@client.on(EnvelopeEvent)
async def on_envelope(event: EnvelopeEvent):
    # Khi có người thả rương hoặc lì xì
    msg = (
        f"🎁 <b>PHÁT HIỆN RƯƠNG MỚI!</b>\n"
        f"📺 Kênh: {TIKTOK_USERNAME}\n"
        f"🔗 <a href='https://www.tiktok.com/{TIKTOK_USERNAME}/live'>Vào nhặt ngay!</a>"
    )
    print("Có rương!")
    send_tele(msg)

# --- CHẠY HỆ THỐNG ---
if __name__ == '__main__':
    keep_alive() # Chạy web server để Render không tắt
    try:
        print("Bot đang khởi động...")
        client.run()
    except Exception as e:
        print(f"Lỗi kết nối: {e}")

