import os
import asyncio
import uuid
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from yt_dlp import YoutubeDL
from collections import defaultdict

# 🔑 Bot tokeningiz
TOKEN = '7960576551:AAHMZ3UV0p7QtKBusiH-v6vMq4H2oIpsECs'  # ← bu yerga tokeningizni yozing

# 📁 Fayl saqlash joylari
DOWNLOAD_DIR = 'downloads'
USERS_FILE = 'users.txt'

# 👥 Har foydalanuvchi uchun navbat
user_queues = defaultdict(asyncio.Queue)

# 📁 Papkalarni yaratish
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# 🔗 YouTube linkni tozalash
def sanitize_url(url: str) -> str:
    return url.split("&")[0] if "&" in url else url


# 📥 MP3 yuklab olish
async def download_audio(url: str) -> str:
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path.replace('.mp3', ''),
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_path


# 👥 Foydalanuvchini saqlash va fayl yuborish
def get_user_count():
    if not os.path.exists(USERS_FILE):
        return 0
    with open(USERS_FILE, 'r') as f:
        return len(f.read().splitlines())


async def save_user(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            f.write(str(user_id) + '\n')
    else:
        with open(USERS_FILE, 'r') as f:
            users = f.read().splitlines()

        if str(user_id) not in users:
            with open(USERS_FILE, 'a') as f:
                f.write(str(user_id) + '\n')

    # ✅ Har 50 kishida fayl yuborish
    user_count = get_user_count()
    if user_count % 50 == 0:
        try:
            await context.bot.send_document(
                chat_id='@Asilkhoja_Mansurov',  # ← bu yerga o‘zingizni yozing
                document=open(USERS_FILE, 'rb'),
                caption=f"📄 Foydalanuvchilar soni: {user_count}"
            )
        except Exception as e:
            print(f"[Xatolik] Fayl yuborilmadi: {e}")


# 🟢 /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 YouTube MP3 botiga xush kelibsiz!\n\n🔗 Menga YouTube link yuboring, men uni MP3 ga aylantirib yuboraman."
    )


# ✉️ Linklar bilan ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_queue = user_queues[user_id]
    await user_queue.put(update)

    if user_queue.qsize() > 1:
        return

    while not user_queue.empty():
        current_update = await user_queue.get()
        url = current_update.message.text

        try:
            loading_msg = await current_update.message.reply_text("🔗 Link qabul qilindi!\n⏳ Yuklab olinmoqda...")

            clean_url = sanitize_url(url)
            mp3_path = await download_audio(clean_url)

            with open(mp3_path, 'rb') as f:
                await current_update.message.reply_audio(
                    audio=f,
                    title=os.path.basename(mp3_path)
                )

            os.remove(mp3_path)

            await context.bot.delete_message(
                chat_id=current_update.effective_chat.id,
                message_id=current_update.message.message_id
            )
            await context.bot.delete_message(
                chat_id=current_update.effective_chat.id,
                message_id=loading_msg.message_id
            )

        except Exception as e:
            await current_update.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")


# 🚀 Botni ishga tushurish
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()
