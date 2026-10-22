import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

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

import logging
from io import BytesIO
import feedparser
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ---------------- CONFIGURATION ----------------
BOT_TOKEN = "8779428741:AAHCd-ICROKeXk3CkFgBiGrPXcSJ-I1jBIA"  
CHANNEL_ID = "@Midirock_Online"  
RSS_URL = "https://feeds.feedburner.com/TechCrunch/"  
WATERMARK_TEXT = "@Midirock"  
# -----------------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def add_watermark(image_bytes, text):
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
    
    draw = ImageDraw.Draw(txt_layer)
    font_size = int(image.size[0] * 0.05)
    
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    textwidth = bbox[2] - bbox[0]
    textheight = bbox[3] - bbox[1]
    
    x = image.size[0] - textwidth - 20
    y = image.size[1] - textheight - 20

    draw.text((x, y), text, font=font, fill=(255, 255, 255, 180))
    
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
            title = latest_entry.title
            link = latest_entry.link
            
            message = f"📢 **አዲስ መረጃ!**\n\n🔹 **{title}**\n\n🔗 [ሙሉውን ለማንበብ ይጫኑ]({link})\n\n---\nከእኛ ጋር ይቆዩ: {CHANNEL_ID}"
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )

async def daily_scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    daily_message = f"🌟 **መልካም ቀን ለቻናላችን ተከታታዮች!**\n\nለዛሬ የተዘጋጁ አዳዲስ መረጃዎችን እና ይዘቶችን ይዘንላችሁ እንቀርባለን።\n\n📌 ቻናላችንን ይጎብኙ: {CHANNEL_ID}"
    await context.bot.send_message(chat_id=CHANNEL_ID, text=daily_message, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Selam! Midirock Content Automation Bot ዝግጁ ነው።")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        processed_photo = add_watermark(photo_bytes, WATERMARK_TEXT)
        caption = update.message.caption or f"ያልተቋረጡ መረጃዎችን ለማግኘት፡ {CHANNEL_ID}"
        
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=processed_photo,
            caption=caption
        )
        await update.message.reply_text("✅ ፎቶው በስኬት Watermark ተደርጎ ወደ ቻናሉ ተፖስቷል!")

# ቦቱ ሲነሳ Scheduler አብሮ እንዲነሳ የሚያደርግ function
async def post_init(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_post_rss, 'interval', minutes=30, args=[application])
    scheduler.add_job(daily_scheduled_post, 'cron', hour=5, minute=0, args=[application])
    scheduler.start()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot runs successfully...")
    app.run_polling()

if __name__ == '__main__':
    main()

