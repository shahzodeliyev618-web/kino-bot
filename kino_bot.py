import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ===================== SOZLAMALAR =====================

BOT_TOKEN = "8494211778:AAHn1hINfWdd6BTI8-kYVKtb10eMs3DuPRU"

KANAL_ID = "@KinotekaShah"

ADMIN_ID = 493420924

# ======================================================
# KINOLAR RO'YXATI
# ======================================================

MOVIES = {
    # "FILM001": "BAADBAADfileID...",
    # "FILM002": "BAADBAADfileID...",
}

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(KANAL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


def get_subscribe_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Kanalga obuna bo'lish", url=f"https://t.me/{KANAL_ID.lstrip('@')}")],
        [InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Salom, {user.first_name}!\n\n"
        f"🎬 Bu bot orqali kinolarni yuklab olishingiz mumkin.\n\n"
        f"📌 Qanday ishlaydi:\n"
        f"1️⃣ Instagramdagi videoda ko'rsatilgan kodni yuboring\n"
        f"2️⃣ Bot kinoni sizga yuboradi\n\n"
        f"⚠️ Kinoni olish uchun kanalimizga obuna bo'lishingiz shart!"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kino kodini yuboring, masalan: FILM001\n"
        "Kodlar Instagramdagi video parchalarida ko'rsatiladi."
    )


async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    if not context.args:
        await update.message.reply_text(
            "Ishlatish:\n"
            "1. /add_movie FILM001 yozing\n"
            "2. Keyin video faylni yuboring"
        )
        return

    code = context.args[0].upper()
    context.user_data["adding_movie_code"] = code
    await update.message.reply_text(f"Kod: {code}\n\nEndi video faylni yuboring.")


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    code = context.user_data.get("adding_movie_code")

    if update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        return

    if code:
        await update.message.reply_text(
            f"Kino ma'lumotlari:\n\n"
            f"Kod: {code}\n"
            f"File ID: {file_id}\n\n"
            f"MOVIES ga qo'shing:\n"
            f'"{code}": "{file_id}"'
        )
        context.user_data.pop("adding_movie_code", None)
    else:
        await update.message.reply_text(f"File ID: {file_id}")


async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    if not MOVIES:
        await update.message.reply_text("Hozircha kinolar yo'q.")
        return

    text = "Kinolar ro'yxati:\n\n"
    for code in MOVIES:
        text += f"• {code}\n"

    await update.message.reply_text(text)


async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()

    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        await update.message.reply_text(
            "⚠️ Kinoni olish uchun avval kanalimizga obuna bo'ling!\n\n"
            "Obuna bo'lgach, Tekshirish tugmasini bosing.",
            reply_markup=get_subscribe_keyboard()
        )
        context.user_data["pending_code"] = code
        return

    await send_movie(update, context, code)


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    if code not in MOVIES:
        await update.message.reply_text(
            f"{code} kodi topilmadi.\n\n"
            "Kodni to'g'ri yozdingizmi? Instagramdagi videoni qayta tekshiring."
        )
        return

    file_id = MOVIES[code]
    await update.message.reply_text("⏳ Kino yuklanmoqda...")

    try:
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=file_id,
            caption=f"🎬 Kino kodi: {code}"
        )
    except Exception as e:
        logger.error(f"Video yuborishda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.")


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_subscribed = await check_subscription(user_id, context)

    if not is_subscribed:
        await query.edit_message_text(
            "❌ Siz hali kanalga obuna bo'lmagansiz!\n\nObuna bo'lib, qayta tekshiring.",
            reply_markup=get_subscribe_keyboard()
        )
        return

    pending_code = context.user_data.pop("pending_code", None)
    await query.edit_message_text("✅ Obuna tasdiqlandi!")

    if pending_code and pending_code in MOVIES:
        await context.bot.send_message(query.message.chat.id, "⏳ Kino yuklanmoqda...")
        try:
            await context.bot.send_video(
                chat_id=query.message.chat.id,
                video=MOVIES[pending_code],
                caption=f"🎬 Kino kodi: {pending_code}"
            )
        except Exception as e:
            logger.error(e)
            await context.bot.send_message(query.message.chat.id, "❌ Xatolik yuz berdi.")
    elif pending_code:
        await context.bot.send_message(
            query.message.chat.id,
            f"{pending_code} kodi topilmadi."
        )
    else:
        await context.bot.send_message(query.message.chat.id, "✅ Endi kino kodini yuboring!")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_movie", add_movie))
    application.add_handler(CommandHandler("movies", list_movies))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, receive_video))
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_sub"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))

    print("✅ Bot ishga tushdi!")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
