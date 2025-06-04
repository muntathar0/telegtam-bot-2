import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from yt_dlp import YoutubeDL
import requests
from io import BytesIO
from PIL import Image
import magic

# إعدادات التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توكن البوت - استبدله بتوكنك الخاص
TOKEN = "8053122524:AAHaARpDd2ehY10CdvXlGTamtbPjpNDaB3E"

# مجلد التحميلات
DOWNLOAD_FOLDER = "downloads/"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ========== دوال البوت ========== #

def start(update: Update, context: CallbackContext) -> None:
    """يعرض رسالة ترحيبية عند استخدام الأمر /start"""
    update.message.reply_text("🎬 **مرحبًا! أنا بوت التحميل الذكي**\n\n"
                            "📸 أرسل لي رابط:\n"
                            "- صورة: سأحملها لك بأعلى جودة\n"
                            "- فيديو: سأعطيك خيارات التحميل (فيديو/صوت)")

def handle_url(update: Update, context: CallbackContext) -> None:
    """يتعرف على نوع المحتوى من الرابط"""
    url = update.message.text
    
    try:
        # الكشف عن نوع الملف
        mime = magic.Magic(mime=True)
        response = requests.get(url, stream=True, timeout=10)
        file_type = mime.from_buffer(response.raw.read(2048))
        
        if 'image' in file_type:
            handle_image(update, context, url)
        elif 'video' in file_type:
            handle_video(update, context, url)
        else:
            update.message.reply_text("⚠️ لم أتعرف على نوع الملف. تأكد من الرابط!")
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ حدث خطأ! قد يكون الرابط غير صحيح أو الموقع محظور.")

def handle_image(update: Update, context: CallbackContext, url: str) -> None:
    """يحمل الصور بأعلى جودة"""
    try:
        update.message.reply_text("⏳ جاري تحميل الصورة...")
        response = requests.get(url, timeout=15)
        img = Image.open(BytesIO(response.content))
        
        # حفظ الصورة
        file_path = os.path.join(DOWNLOAD_FOLDER, f"image_{update.message.message_id}.jpg")
        img.save(file_path, quality=95, optimize=True)
        
        # إرسالها
        with open(file_path, 'rb') as photo:
            update.message.reply_photo(photo, caption="✅ تم التحميل بنجاح!")
        
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Image Error: {e}")
        update.message.reply_text("❌ فشل تحميل الصورة!")

def handle_video(update: Update, context: CallbackContext, url: str) -> None:
    """يعرض خيارات تحميل الفيديو"""
    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        
        context.user_data['video_url'] = url
        
        # لوحة خيارات
        keyboard = [
            [InlineKeyboardButton("🎥 فيديو", callback_data='video'),
            InlineKeyboardButton("🎵 صوت فقط", callback_data='audio')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "📹 **اختر طريقة التحميل:**",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Video Error: {e}")
        update.message.reply_text("❌ لا يمكن تحميل هذا الفيديو!")

def video_options(update: Update, context: CallbackContext) -> None:
    """يعالج اختيارات المستخدم"""
    query = update.callback_query
    query.answer()
    
    if query.data == 'video':
        # خيارات جودة الفيديو
        keyboard = [
            [InlineKeyboardButton("🌟 عالية (1080p)", callback_data='quality_best')],
            [InlineKeyboardButton("⚖️ متوسطة (720p)", callback_data='quality_medium')],
            [InlineKeyboardButton("📱 منخفضة (480p)", callback_data='quality_low')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("اختر جودة الفيديو:", reply_markup=reply_markup)
    
    elif query.data == 'audio':
        download_audio(update, context)
    
    elif query.data.startswith('quality_'):
        download_video(update, context, query.data.replace('quality_', ''))

def download_video(update: Update, context: CallbackContext, quality: str) -> None:
    """يحمل الفيديو بالجودة المحددة"""
    query = update.callback_query
    url = context.user_data['video_url']
    
    query.edit_message_text("⏳ جاري التحميل... (قد يأخذ وقتًا للفيديوهات الطويلة)")
    
    try:
        ydl_opts = {
            'format': {
                'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'medium': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'low': 'bestvideo[height<=480]+bestaudio/best[height<=480]'
            }[quality],
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        # إرسال الفيديو
        with open(file_path, 'rb') as video:
            context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video,
                caption=f"✅ تم التحميل بنجاح! ({'عالية' if quality == 'best' else 'متوسطة' if quality == 'medium' else 'منخفضة'})",
                supports_streaming=True,
                timeout=100
            )
        
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Video DL Error: {e}")
        query.edit_message_text("❌ فشل التحميل! قد يكون الفيديو محميًا أو طويلًا جدًا.")

def download_audio(update: Update, context: CallbackContext) -> None:
    """يحمل الصوت من الفيديو"""
    query = update.callback_query
    url = context.user_data['video_url']
    
    query.edit_message_text("⏳ جاري تحويل الفيديو إلى صوت...")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'quiet': True
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
        
        # إرسال الصوت
        with open(file_path, 'rb') as audio:
            context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio,
                caption="✅ تم تحويل الفيديو إلى صوت بنجاح!",
                timeout=100
            )
        
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Audio Error: {e}")
        query.edit_message_text("❌ فشل تحويل الفيديو إلى صوت!")

def error_handler(update: Update, context: CallbackContext) -> None:
    """يتعامل مع الأخطاء العامة"""
    logger.error(msg="Error:", exc_info=context.error)
    if update and update.message:
        update.message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.")

# ========== تشغيل البوت ========== #

def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # تسجيل المعالجين
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url))
    dispatcher.add_handler(CallbackQueryHandler(video_options))
    dispatcher.add_error_handler(error_handler)

    # بدء البوت
    updater.start_polling()
    print("✅ البوت يعمل الآن...")
    updater.idle()

if __name__ == '__main__':
    main()