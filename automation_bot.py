import os
import logging
from io import BytesIO
import feedparser
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Web Server for Render Health Check
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_health_check_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# Configuration
BOT_TOKEN = "8779428741:AAHCd-ICROKeXk3CKfgBiGrPXcSJ-I1jBIA"
CHANNEL_ID = "@Midirock_Online"
RSS_URL = "https://feeds.feedburner.com/TechCrunch/"
WATERMARK_TEXT = "@Midirock"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def add_watermark(image_bytes, text):
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    font_size = int(image.size[0] * 0.08)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        
    x = int(image.size[0] * 0.05)
    y = int(image.size[1] * 0.85)
    
    draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, 200))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 230))
    
    watermarked = Image.alpha_composite(image, txt_layer)
    output = BytesIO()
    watermarked.convert("RGB").save(output, format="JPEG")
    output.seek(0)
    return output

last_rss_link = None

async def fetch_and_post_rss(context: ContextTypes.DEFAULT_TYPE):
    global last_rss_link
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        latest_entry = feed.entries[0]
        if latest_entry.link != last_rss_link:
            last_rss_link = latest_entry.link
            message = f"📢 **አዲስ መረጃ!**\n\n🔹 **{latest_entry.title}**\n\n🔗 [ሙሉውን ለማንበብ ይጫኑ]({latest_entry.link})"
            await context.bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="Markdown")

async def daily_scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    daily_message = f"🌟 **መልካም ቀን ለቻናላችን ተከታታዮች!**\n\nዛሬም አዳዲስ እና ጠቃሚ መረጃዎችን ይዘንላችሁ እንቀርባለን። ከእኛ ጋር ይቆዩ! ✨"
    await context.bot.send_message(chat_id=CHANNEL_ID, text=daily_message, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Selam! Midirock Content Automation Bot ዝግጁ ነው። ፎቶ ሲልኩልኝ ዋተርማርክ አድርጌ ወደ ቻናል እልካለሁ!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        await update.message.reply_text("⏳ ፎቶውን በመቀበል ላይ... ዋተርማርክ እየተደረገበት ነው...")
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        processed_photo = add_watermark(photo_bytes, WATERMARK_TEXT)
        caption = update.message.caption or f"📸 {WATERMARK_TEXT}"
        
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=processed_photo, caption=caption)
        await update.message.reply_text("✅ ፎቶው በስኬት ዋተርማርክ ተደርጎ ወደ ቻናሉ ተልኳል!")

async def post_init(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_post_rss, 'interval', minutes=30)
    scheduler.add_job(daily_scheduled_post, 'cron', hour=8, minute=0)
    scheduler.start()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
