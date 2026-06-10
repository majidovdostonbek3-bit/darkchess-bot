import logging
import chess
import io
import os
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

games = {}
waiting_games = {}

# ---- Doska rasmi chizish ----
def draw_board(board: chess.Board, selected=None, last_move=None) -> bytes:
    SIZE = 400
    SQ = SIZE // 8
    img = Image.new("RGB", (SIZE + 40, SIZE + 40), (40, 40, 40))
    draw = ImageDraw.Draw(img)

    LIGHT = (240, 217, 181)
    DARK = (181, 136, 99)
    SELECTED = (246, 246, 105)
    LAST_MOVE = (205, 210, 106)
    PIECES_UNICODE = {
        'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
        'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
    }

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", SQ - 8)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    last_squares = []
    if last_move:
        last_squares = [last_move.from_square, last_move.to_square]

    for rank in range(7, -1, -1):
        for file in range(8):
            sq = chess.square(file, rank)
            x = file * SQ + 20
            y = (7 - rank) * SQ + 20

            if selected == sq:
                color = SELECTED
            elif sq in last_squares:
                color = LAST_MOVE
            elif (rank + file) % 2 == 0:
                color = DARK
            else:
                color = LIGHT

            draw.rectangle([x, y, x + SQ, y + SQ], fill=color)

            piece = board.piece_at(sq)
            if piece:
                symbol = PIECES_UNICODE[piece.symbol()]
                piece_color = (255, 255, 255) if piece.color == chess.WHITE else (0, 0, 0)
                draw.text((x + 4, y + 2), symbol, fill=piece_color, font=font)

    # Harflar va raqamlar
    for i in range(8):
        draw.text((i * SQ + 20 + SQ//2 - 5, SIZE + 22), "abcdefgh"[i], fill=(200, 200, 200), font=label_font)
        draw.text((4, (7 - i) * SQ + 20 + SQ//2 - 7), str(i + 1), fill=(200, 200, 200), font=label_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ---- Yurish tugmalari ----
def move_keyboard(board: chess.Board, selected=None):
    if selected is None:
        # Harakatlanishi mumkin bo'lgan donalar
        pieces = set()
        for move in board.legal_moves:
            pieces.add(move.from_square)
        rows = []
        row = []
        files = "abcdefgh"
        for sq in sorted(pieces):
            piece = board.piece_at(sq)
            if piece:
                label = f"{chess.PIECE_SYMBOLS[piece.piece_type].upper()}{files[chess.square_file(sq)]}{chess.square_rank(sq)+1}"
                row.append(InlineKeyboardButton(label, callback_data=f"sel_{sq}"))
                if len(row) == 4:
                    rows.append(row)
                    row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("🏳️ Taslim", callback_data="resign")])
        return InlineKeyboardMarkup(rows)
    else:
        # Tanlangan donaning yurishlari
        moves = [m for m in board.legal_moves if m.from_square == selected]
        rows = []
        row = []
        files = "abcdefgh"
        for move in moves:
            to_sq = move.to_square
            label = f"{files[chess.square_file(to_sq)]}{chess.square_rank(to_sq)+1}"
            row.append(InlineKeyboardButton(label, callback_data=f"move_{move.uci()}"))
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back")])
        return InlineKeyboardMarkup(rows)


async def send_board(update_or_query, game, text="", edit=False):
    board = game['board']
    last_move = board.peek() if board.move_stack else None
    img_bytes = draw_board(board, last_move=last_move)
    keyboard = move_keyboard(board)

    turn = "⬜ Oq" if board.turn == chess.WHITE else "⬛ Qora"
    check = " ⚠️ Shoh!" if board.is_check() else ""
    caption = f"{turn} navbati{check}"
    if text:
        caption = text + "\n" + caption

    if edit and hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_photo(
            photo=img_bytes, caption=caption, reply_markup=keyboard
        )
    elif hasattr(update_or_query, 'message'):
        await update_or_query.message.reply_photo(
            photo=img_bytes, caption=caption, reply_markup=keyboard
        )
    else:
        await update_or_query.edit_message_caption(
            caption=caption, reply_markup=keyboard
        )


# ---- /start ----
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤖 AI bilan o'ynash", callback_data="mode_ai")],
        [InlineKeyboardButton("👥 Do'st bilan o'ynash", callback_data="mode_pvp")],
    ]
    await update.message.reply_text(
        "♟ *Darkchess Botiga Xush Kelibsiz!*\n\nO'yin rejimini tanlang:",
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
        await query.edit_message_text(
            "🤖 *AI darajasini tanlang:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "mode_pvp":
        if chat_id in waiting_games and waiting_games[chat_id] != user_id:
            white_id = waiting_games.pop(chat_id)
            board = chess.Board()
            games[chat_id] = {
                'board': board, 'mode': 'pvp',
                'players': {chess.WHITE: white_id, chess.BLACK: user_id},
            }
            await query.edit_message_text("✅ O'yin boshlandi!")
            await send_board(query, games[chat_id])
        else:
            waiting_games[chat_id] = user_id
            keyboard = [[InlineKeyboardButton("🎮 Qo'shilish", callback_data="mode_pvp")]]
            await query.edit_message_text(
                "⏳ *Raqib kutilmoqda...*\nDo'stingiz shu tugmani bossin!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def ai_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    level = int(query.data.split("_")[1])
    board = chess.Board()
    games[chat_id] = {
        'board': board, 'mode': 'ai',
        'players': {chess.WHITE: user_id},
        'ai_level': level,
    }
    await query.edit_message_text(f"✅ AI bilan o'yin (daraja: {level})")
    await send_board(query, games[chat_id])


async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id

    if chat_id not in games:
        await query.answer("O'yin yo'q! /start bosing", show_alert=True)
        return

    game = games[chat_id]
    board = game['board']

    if game['mode'] == 'pvp':
        if game['players'].get(board.turn) != user_id:
            await query.answer("Sizning navbatingiz emas!", show_alert=True)
            return

    data = query.data
