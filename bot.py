import logging
import chess
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8700268528:AAHNLSBSnKsihPUcL7hhdPbB9U4-RzkWME8")

PIECES = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
}

games = {}
waiting_games = {}

def board_to_text(board):
    lines = []
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            sq = chess.square(file, rank)
            piece = board.piece_at(sq)
            if piece:
                row.append(PIECES[piece.symbol()])
            else:
                row.append('⬛' if (rank + file) % 2 == 0 else '⬜')
        lines.append(f"{rank + 1} {''.join(row)}")
    lines.append("  ａｂｃｄｅｆｇｈ")
    return '\n'.join(lines)
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤖 AI bilan o'ynash", callback_data="mode_ai")],
        [InlineKeyboardButton("👥 Do'st bilan o'ynash", callback_data="mode_pvp")],
    ]
    await update.message.reply_text(
        "♟ *Telegram Shaxmat Botiga Xush Kelibsiz!*\n\nQanday o'ynashni tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mode_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    if query.data == "mode_ai":
        keyboard = [
            [InlineKeyboardButton("🟢 Oson", callback_data="ai_1"),
             InlineKeyboardButton("🟡 O'rta", callback_data="ai_3")],
            [InlineKeyboardButton("🔴 Qiyin", callback_data="ai_5"),
             InlineKeyboardButton("⚫ Master", callback_data="ai_8")],
        ]
        await query.edit_message_text("🤖 *AI Darajasini Tanlang:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "mode_pvp":
        if chat_id in waiting_games:
            white_id = waiting_games.pop(chat_id)
            black_id = user_id
            if white_id == black_id:
                await query.edit_message_text("❌ O'zingiz bilan o'ynay olmaysiz!")
                return
            board = chess.Board()
            games[chat_id] = {'board': board, 'mode': 'pvp', 'players': {chess.WHITE: white_id, chess.BLACK: black_id}}
            await query.edit_message_text(f"✅ *O'yin boshlandi!*\n\n{board_to_text(board)}\n\n⬜ Oq yurish qiladi!\nFormat: `e2e4`", parse_mode="Markdown")
        else:
            waiting_games[chat_id] = user_id
            keyboard = [[InlineKeyboardButton("🎮 O'yinga qo'shilish", callback_data="mode_pvp")]]
            await query.edit_message_text("⏳ *Raqib kutilmoqda...*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
