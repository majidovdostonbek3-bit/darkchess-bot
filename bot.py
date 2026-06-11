from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8957247374:AAH_kUAXw9p8pvv99FxrZ9h7UizcPQSwZko"
WEBAPP_URL = "https://majidovdostonbek3-bit.github.io/darkchess-bot"

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♟ O'yin boshlash", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📢 Do'stga yuborish", switch_inline_query="UzChess o'ynaylik!")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "♟ *UzChess ga xush kelibsiz!*\n\nRasmli shaxmat o'ynash uchun tugmani bosing!",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "♟ *UzChess yordam*\n\n"
        "/start - Botni boshlash\n"
        "O'yin boshlash tugmasini bosing — rasmli taxta ochiladi!",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
