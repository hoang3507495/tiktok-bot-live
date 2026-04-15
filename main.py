from flask import Flask, request, render_template_string
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time
import re
from datetime import datetime, timedelta

# --- CẤU HÌNH HỆ THỐNG ---
WEB_URL = "https://tiktok-bot-live.onrender.com" 

TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}

NOTIFY_TIME = 45 

app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot Hunter v6.1 (Minimalist UI) is Running!"

@app.route('/timer')
def timer():
    ts = request.args.get('ts', 0, type=int)
    w = request.args.get('w', 0, type=int)
    user = request.args.get('user', 'TikTok')
    
    elapsed = int(time.time()) - ts
    remaining = w - elapsed - 2 
    if remaining < 0: remaining = 0

    # Giao diện tối giản tuyệt đối, cả màn hình là nút bấm
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <title>Sniper Timer</title>
        <style>
            body { 
                background-color: #000; 
                color: #fff; 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                height: 100vh; 
                margin: 0; 
                overflow: hidden; 
                cursor: pointer; 
                -webkit-tap-highlight-color: transparent;
            }
            /* Chữ số khổng lồ, căn giữa tuyệt đối */
            .timer { 
                font-size: 150px; 
                font-weight: 700; 
                font-variant-numeric: tabular-nums; 
                letter-spacing: -3px; 
            }
        </style>
    </head>
    <body onclick="window.location.href='https://www.tiktok.com/@{{user}}/live'">
        
        <div class="timer" id="time">00:00</div>
        
        <script>
            var remainingSeconds = {{remaining}};
            var targetTime = Date.now() + remainingSeconds * 1000;
            var timerInterval;

            function updateDisplay() {
                var now = Date.now();
                var distance = targetTime - now;

                if (distance <= 0) {
                    document.getElementById("time").innerHTML = "00:00";
                    document.getElementById("time").style.color = "#32d74b"; // Đổi màu xanh khi về 0
                    return true;
                }

                // Tính toán số giây và phần mili-giây (hiển thị nhảy bậc 10 như 90, 80, 70...)
                var s = Math.floor(distance / 1000);
                var ms = Math.floor((distance % 1000) / 100) * 10;

                var sStr = s < 10 ? "0" + s : s;
                var msStr = ms === 0 ? "00" : ms;
                
                document.getElementById("time").innerHTML = sStr + ":" + msStr;
                return false;
            }

            function startTimer() {
                updateDisplay();
                // Quét cực nhanh 50ms/lần để số nhảy mượt
                timerInterval = setInterval(function() {
                    if (updateDisplay()) clearInterval(timerInterval);
                }, 50);
            }

            startTimer();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, remaining=remaining, user=user)

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

# --- LOGIC QUÉT ---
async def start_tracking(username, loop):
    if username in ACTIVE_CLIENTS: return
    clean_name = username.replace("@", "").strip()
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã vào phòng:</b> @{clean_name}\nĐang trực rương...")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            raw_data = str(vars(event))
            
            match_coins = re.search(r"string_value='(\d+)'", raw_data)
            coins = match_coins.group(1) if match_coins else "0"
            if coins == "0":
                alt_coins = re.search(r"['\"]?(?:coin|score|diamond_count)['\"]?[:=]\s*(\d+)", raw_data, re.I)
                coins = alt_coins.group(1) if alt_coins else "0"
            if coins == "0": return

            match_people = re.search(r"(?:can_win_count|winner_count|winner_num|people_count)[:=]\s*(\d+)", raw_data, re.I)
            people = match_people.group(1) if match_people else "Nhiều"

            flag = "🇻🇳" 
            m_region = re.search(r"['\"]?(?:region|country|country_code)['\"]?[:=]\s*['\"]([a-zA-Z]{2})['\"]", raw_data, re.I)
            if m_region:
                code = m_region.group(1).upper()
                try: flag = chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)
                except: pass

            wait_sec = 0
            current_ms = int(time.time() * 1000)

            all_13_digits = re.findall(r"\b(17\d{11})\b", raw_data)
            for ts_str in all_13_digits:
                diff_sec = (int(ts_str) - current_ms) / 1000
                if 10 < diff_sec <= 600: 
                    wait_sec = int(diff_sec)
                    break

            if wait_sec == 0:
                m_exact = re.search(r"(?:wait_time|duration)['\"]?[:=]\s*(\d{2,4})\b", raw_data, re.I)
                if m_exact: wait_sec = int(m_exact.group(1))
            
            if wait_sec == 0:
                m_common = re.search(r"time['\"]?[:=]\s*(300|180|120|600)\b", raw_data, re.I)
                if m_common: wait_sec = int(m_common.group(1))

            if wait_sec == 0 or wait_sec > 1000: wait_sec = 300 

            event_ts = int(time.time())
            delay_time = wait_sec - NOTIFY_TIME 
            
            if delay_time > 0:
                await asyncio.sleep(delay_time)

            current_elapsed = int(time.time()) - event_ts
            actual_remaining = wait_sec - current_elapsed
            if actual_remaining < 0: actual_remaining = 0

            if actual_remaining > 0:
                timer_url = f"{WEB_URL}/timer?ts={event_ts}&w={wait_sec}&user={clean_name}"
                
                room_id = getattr(client, 'room_id', 'Chưa rõ')
                viewers = getattr(client, 'viewer_count', '...')
                
                vn_time = datetime.utcnow() + timedelta(hours=7)
                time_str = vn_time.strftime("%H:%M:%S")

                msg = (f"👤 <b>KÊNH :</b> @{clean_name} ({room_id})\n"
                       f"🎁 <b>RƯƠNG :</b> {coins} /{people} {flag}\n"
                       f"⏱ <b>Mở Sau :</b> {actual_remaining}s - {time_str}\n"
                       f"👀 <b>:</b> {viewers}\n"
                       f"👉 <a href='{timer_url}'><b>ĐỒNG HỒ ĐẾM NGƯỢC</b></a>\n"
                       f"› tiktok.com/share/live/{room_id}")
                
                send_tele(msg)
        except Exception as e:
            print(f"Lỗi: {e}")

    try: await client.start()
    except: ACTIVE_CLIENTS.pop(username, None)

def tele_worker(loop):
    last_id = 0
    send_tele(f"🚀 <b>Hệ thống v6.1 (Minimalist UI) Online!</b>\nGiao diện web đã được dọn dẹp tối giản.")
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
                            send_tele(f"📝 Đang xem: " + ", ".join(names) if names else "Trống")
                        elif text.startswith("@") or (len(text) > 2 and " " not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
        except: time.sleep(2)
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    tiktok_loop = asyncio.new_event_loop()
    Thread(target=lambda: (asyncio.set_event_loop(tiktok_loop), tiktok_loop.run_forever()), daemon=True).start()
    tele_worker(tiktok_loop)
