import os

# توكن البوت - احصل عليه من @BotFather
TOKEN = "ضع_توكن_البوت_هنا"

# مجلد التحميلات
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "downloads")

# إعدادات yt-dlp
YTDL_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'geo_bypass': True
}