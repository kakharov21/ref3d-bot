import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

WAITING_DIMS = 1
user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men 3D Ref Analyzer botman 🧊\n\n"
        "Ishlash tartibi:\n"
        "1. Menga referens rasm yuboring\n"
        "2. O'lchamlarni yozing (masalan: 150 75 42)\n"
        "3. Men tahlil qilib beraman!\n\n"
        "Boshlash uchun rasm yuboring 👇"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    user_images[update.effective_user.id] = bytes(file_bytes)
    await update.message.reply_text(
        "Rasm qabul qilindi! ✅\n\n"
        "Endi o'lchamlarni yozing (sm da):\n"
        "Format: `uzunlik balandlik chuqurlik`\n"
        "Misol: `150 75 42`",
        parse_mode="Markdown"
    )
    return WAITING_DIMS

async def handle_dims(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_images:
        await update.message.reply_text("Avval rasm yuboring! 🖼️")
        return ConversationHandler.END

    text = update.message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("Format noto'g'ri. Misol: `150 75 42`", parse_mode="Markdown")
        return WAITING_DIMS

    w, h = parts[0], parts[1]
    d = parts[2] if len(parts) > 2 else "?"
    dims = f"W:{w}sm × H:{h}sm × D:{d}sm"

    await update.message.reply_text("Tahlil qilinmoqda... ⏳")

    prompt = f"""Sen professional 3D modeler uchun referens tahlilchisisisan.

Quyidagi formatda javob ber:

🧊 *OBYEKT TAHLILI*
• Obyekt nomi: ...
• Uslub: ...
• Material: ...

📐 *TEXNIK SPESIFIKATSIYA*
• O'lchamlar: {dims}
• Tavsiya poly count: ...
• UV tavsiyasi: ...
• Texture resolution: ...
• Texture maps: ...

📋 *MODELING BOSQICHLARI*
1. ...
2. ...
3. ...
4. ...
5. ...

⚠️ *MURAKKAB QISMLAR*
• ...

💡 *BLENDER/3DS MAX MASLAHATLAR*
• ...

🏷️ *CGTRADER TEGLAR*
...

Barcha javoblar o'zbek tilida bo'lsin. Aniq va amaliy ma'lumot ber."""

    try:
        import PIL.Image
        import io
        img = PIL.Image.open(io.BytesIO(user_images[user_id]))
        response = model.generate_content([prompt, img])
        result = response.text
        del user_images[user_id]

        if len(result) > 4096:
            for i in range(0, len(result), 4096):
                await update.message.reply_text(result[i:i+4096], parse_mode="Markdown")
        else:
            await update.message.reply_text(result, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Xatolik yuz berdi: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_images.pop(update.effective_user.id, None)
    await update.message.reply_text("Bekor qilindi. Yangi rasm yuboring.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_photo)],
        states={WAITING_DIMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dims)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    logger.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
