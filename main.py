import os
import asyncio
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from static_ffmpeg import run

# បញ្ជាឱ្យប្រព័ន្ធទាញយក និងកំណត់ទីតាំង FFmpeg ស្វ័យប្រវត្តលើ Cloud
ffmpeg_path, ffprobe_path = run.get_or_fetch_platform_executables_and_set_env()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# លេខ Token របស់បង
BOT_TOKEN = "80904144736:AAFxXkbfY1vUkJQ710SfelvxLrp5Th-vkEA"

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running alive!")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 សួស្តី! ខ្ញុំជា MeyDownloaderBot រត់នៅលើ Cloud Free ២៤ ម៉ោងជោគជ័យហើយ!")

def generate_hashtags(title, platform):
    base_hashtags = ["#foryou", "#fyp", "#viral", "#trending"]
    if "tiktok" in platform: base_hashtags.extend(["#tiktok"])
    elif "youtube" in platform: base_hashtags.extend(["#youtube", "#shorts"])
    elif "facebook" in platform: base_hashtags.extend(["#facebookreels"])
    clean_title = re.sub(r'[^\w\s]', '', title)
    words = clean_title.split()
    extra_hashtags = [f"#{w.lower()}" for w in words if len(w) > 3]
    all_hashtags = extra_hashtags[:3] + base_hashtags
    return " ".join(all_hashtags[:7])

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")): return
    
    status_message = await update.message.reply_text("⏳ កំពុងទាញយកវីដេអូ... សូមរង់ចាំបន្តិច។")
    download_dir = '/tmp/downloads'
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{download_dir}/%(id)s.%(ext)s',
        'noplaylist': True, 
        'quiet': True,
    }
    
    try:
        platform = "video"
        if "tiktok.com" in url: platform = "tiktok"
        elif "youtube.com" in url or "youtu.be" in url: platform = "youtube"
        elif "facebook.com" in url or "fb.watch" in url: platform = "facebook"

        def extract_and_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'Video')

        loop = asyncio.get_running_loop()
        file_path, video_title = await loop.run_in_executor(None, extract_and_download)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await status_message.edit_text(f"⚠️ វីដេអូនេះមានទំហំ {file_size_mb:.1f}MB ធំជាងលីមីត 50MB របស់ Telegram Cloud ហើយ។")
            if os.path.exists(file_path): os.remove(file_path)
            return

        generated_hashtags = generate_hashtags(video_title, platform)
        caption_text = f"🎬 **{video_title}**\n\n🎯 **Hashtags:**\n{generated_hashtags}"

        await status_message.edit_text("🚀 ទាញយកជោគជ័យ! កំពុងបង្ហោះចូល Telegram...")
        
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption=caption_text, parse_mode="Markdown")

        if os.path.exists(file_path): os.remove(file_path)
        await status_message.delete()
        
    except Exception as e:
        await status_message.edit_text(f"❌ មិនអាចទាញយកបានទេ៖ {str(e)}")

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send_video))
    app.run_polling()

if __name__ == '__main__':
    main()
