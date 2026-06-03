import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ===================== SOZLAMALAR =====================

BOT_TOKEN = "8494211778:AAHn1hINfWdd6BTI8-kYVKtb10eMs3DuPRU"  # @BotFather dan olingan token

KANAL_ID = "@KinotekaShah"  # Masalan: @mening_kanalim

ADMIN_ID = 493420924  # Telegram ID raqaming (https://t.me/userinfobot dan olasan)

# ======================================================
# KINOLAR RO'YXATI
# Format: "KOD": "TELEGRAM_FILE_ID"
# File ID ni olish uchun: /add_movie buyrug'ini ishlatasan (quyida ko'rsatilgan)
# ======================================================

MOVIES = {
    # "FILM001": "BAADBAADfileID...",
    # "FILM002": "BAADBAADfileID...",
}

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===================== YORDAMCHI FUNKSIYALAR =====================

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Foydalanuvchi kanalga obuna bo'lganmi?"""
    try:
        member = await context.bot.get_chat_member(KANAL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


def get_subscribe_keyboard():
    """Obuna tugmasi"""
    keyboard = [
        [InlineKeyboardButton("✅ Kanalga obuna bo'lish", url=f"https://t.me/{KANAL_ID.lstrip('@')}")],
        [InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ===================== KOMANDALAR =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ishga tushganda"""
    user = update.effective_user
    text = (
        f"👋 Salom, {user.first_name}!\n\n"
        f"🎬 Bu bot orqali kinolarni yuklab olishingiz mumkin.\n\n"
        f"📌 Qanday ishlaydi:\n"
        f"1️⃣ Instagramdagi videoda ko'rsatilgan **kodni** yuboring\n"
        f"2️⃣ Bot kinoni sizga yuboradi\n\n"
        f"⚠️ Kinoni olish uchun kanalimizga obuna bo'lishingiz shart!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Yordam*\n\n"
        "Kino kodini yuboring, masalan: `FILM001`\n"
        "Kodlar Instagramdagi video parchalarida ko'rsatiladi.",
        parse_mode="Markdown"
    )


# ===================== ADMIN - KINO QO'SHISH =====================

async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin kino qo'shishi uchun: /add_movie FILM001"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 Ishlatish:\n"
            "1. Birinchi `/add_movie KOD` yozing (masalan `/add_movie FILM001`)\n"
            "2. Keyin video faylni yuboring\n\n"
            "Men sizga File ID ni beraman, uni `kino_bot.py` faylidagi `MOVIES` ga qo'shasiz."
        )
        return

    code = context.args[0].upper()
    context.user_data["adding_movie_code"] = code
    await update.message.reply_text(
        f"✅ Kod: `{code}`\n\nEndi shu xabarga reply qilib video faylni yuboring.",
        parse_mode="Markdown"
    )


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin video yuborganda File ID ni qaytaradi"""
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
            f"🎬 *Kino ma'lumotlari:*\n\n"
            f"Kod: `{code}`\n"
            f"File ID: `{file_id}`\n\n"
            f"📋 `kino_bot.py` faylidagi `MOVIES` ga qo'shing:\n"
            f'`"{code}": "{file_id}"`',
            parse_mode="Markdown"
        )
        context.user_data.pop("adding_movie_code", None)
    else:
        await update.message.reply_text(
            f"📁 File ID: `{file_id}`",
            parse_mode="Markdown"
        )


async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun: barcha kinolar ro'yxati"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    if not MOVIES:
        await update.message.reply_text("📭 Hozircha kinolar yo'q.")
        return

    text = "🎬 *Kinolar ro'yxati:*\n\n"
    for code in MOVIES:
        text += f"• `{code}`\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ===================== ASOSIY - KOD TEKSHIRISH =====================

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kod yuborganda"""
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()

    # Obuna tekshirish
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        await update.message.reply_text(
            "⚠️ Kinoni olish uchun avval kanalimizga obuna bo'ling!\n\n"
            "Obuna bo'lgach, «🔄 Tekshirish» tugmasini bosing.",
            reply_markup=get_subscribe_keyboard()
        )
        context.user_data["pending_code"] = code
        return

    # Kino mavjudmi?
    await send_movie(update, context, code)


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """Kinoni yuborish"""
    if code not in MOVIES:
        await update.message.reply_text(
            f"❌ `{code}` kodi topilmadi.\n\n"
            "Iltimos, kodni to'g'ri yozdingizmi? Instagramdagi videoni qayta tekshiring.",
            parse_mode="Markdown"
        )
        return

    file_id = MOVIES[code]
    await update.message.reply_text("⏳ Kino yuklanmoqda...")

    try:
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=file_id,
            caption=f"🎬 Kino kodi: `{code}`\n\n@{context.bot.username}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Video yuborishda xato: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )


# ===================== CALLBACK - OBUNA TEKSHIRISH =====================

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """«Tekshirish» tugmasi bosilganda"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_subscribed = await check_subscription(user_id, context)

    if not is_subscribed:
        await query.edit_message_text(
            "❌ Siz hali kanalga obuna bo'lmagansiz!\n\n"
            "Obuna bo'lib, qayta tekshiring.",
            reply_markup=get_subscribe_keyboard()
        )
        return

    # Obuna bo'lgan, kutilayotgan kodni yuborish
    pending_code = context.user_data.pop("pending_code", None)
    await query.edit_message_text("✅ Obuna tasdiqlandi!")

    if pending_code:
        # Fake message yaratib kino yuborish
        class FakeMessage:
            effective_chat = query.message.chat
            effective_user = query.from_user

            async def reply_text(self, *args, **kwargs):
                await context.bot.send_message(query.message.chat.id, *args, **kwargs)

        fake_update = Update(update.update_id, message=query.message)
        fake_update._effective_chat = query.message.chat
        fake_update._effective_user = query.from_user

        if pending_code in MOVIES:
            await context.bot.send_message(query.message.chat.id, "⏳ Kino yuklanmoqda...")
            try:
                await context.bot.send_video(
                    chat_id=query.message.chat.id,
                    video=MOVIES[pending_code],
                    caption=f"🎬 Kino kodi: `{pending_code}`\n\n@{context.bot.username}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(e)
                await context.bot.send_message(query.message.chat.id, "❌ Xatolik yuz berdi.")
        else:
            await context.bot.send_message(
                query.message.chat.id,
                f"❌ `{pending_code}` kodi topilmadi.",
                parse_mode="Markdown"
            )
    else:
        await context.bot.send_message(
            query.message.chat.id,
            "✅ Endi kino kodini yuboring!"
        )


# ===================== BOTNI ISHGA TUSHIRISH =====================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Komandalar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add_movie", add_movie))
    app.add_handler(CommandHandler("movies", list_movies))

    # Video qabul qilish (admin uchun)
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, receive_video))

    # Obuna tekshirish tugmasi
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_sub"))

    # Kod qabul qilish
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))

    print("✅ Bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
