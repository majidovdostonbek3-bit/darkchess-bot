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

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

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
