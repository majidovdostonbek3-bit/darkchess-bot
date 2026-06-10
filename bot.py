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

TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))
DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")

games = {}
waiting_games = {}

def draw_board(board):
    SIZE = 400
    SQ = SIZE // 8
    img = Image.new("RGB", (SIZE + 40, SIZE + 40), (40, 40, 40))
    draw = ImageDraw.Draw(img)
    LIGHT = (240, 217, 181)
    DARK = (181, 136, 99)
    LAST = (205, 210, 106)
    UNICODE = {
        'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
        'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
    }
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", SQ - 8)
        lfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()
        lfont = font

    last_squares = []
    if board.move_stack:
        lm = board.peek()
        last_squares = [lm.from_square, lm.to_square]

    for rank in range(7, -1, -1):
        for file in range(8):
            sq = chess.square(file, rank)
            x = file * SQ + 20
            y = (7 - rank) * SQ + 20
            if sq in last_squares:
                color = LAST
            elif (rank + file) % 2 == 0:
                color = DARK
            else:
                color = LIGHT
            draw.rectangle([x, y, x+SQ, y+SQ], fill=color)
            piece = board.piece_at(sq)
            if piece:
                sym = UNICODE[piece.symbol()]
                pc = (255,255,255) if piece.color == chess.WHITE else (10,10,10)
                draw.text((x+4, y+2), sym, fill=pc, font=font)

    for i in range(8):
        draw.text((i*SQ+20+SQ//2-5, SIZE+22), "abcdefgh"[i], fill=(200,200,200), font=lfont)
        draw.text((4, (7-i)*SQ+20+SQ//2-7), str(i+1), fill=(200,200,200), font=lfont)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def move_keyboard(board, selected=None):
    files = "abcdefgh"
    if selected is None:
        pieces = set(m.from_square for m in board.legal_moves)
        rows = []
        row = []
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
        moves = [m for m in board.legal_moves if m.from_square == selected]
        rows = []
        row = []
        for move in moves:
            to = move.to_square
            label = f"{files[chess.square_file(to)]}{chess.square_rank(to)+1}"
            row.append(InlineKeyboardButton(label, callback_data=f"move_{move.uci()}"))
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back")])
        return InlineKeyboardMarkup(rows)


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
        await query.edit_message_text("🤖 *AI darajasini tanlang:*", parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "mode_pvp":
        if chat_id in waiting_games and waiting_games[chat_id] != user_id:
            white_id = waiting_games.pop(chat_id)
            board = chess.Board()
            games[chat_id] = {'board': board, 'mode': 'pvp',
                               'players': {chess.WHITE: white_id, chess.BLACK: user_id}}
            await query.edit_message_text("✅ O'yin boshlandi!")
            img = draw_board(board)
            turn = "⬜ Oq navbati"
            await query.message.reply_photo(photo=img, caption=turn,
                                             reply_markup=move_keyboard(board))
        else:
            waiting_games[chat_id] = user_id
            kb = [[InlineKeyboardButton("🎮 Qo'shilish", callback_data="mode_pvp")]]
            await query.edit_message_text("⏳ *Raqib kutilmoqda...*",
                                           parse_mode="Markdown",
                                           reply_markup=InlineKeyboardMarkup(kb))


async def ai_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    level = int(query.data.split("_")[1])
    board = chess.Board()
    games[chat_id] = {'board': board, 'mode': 'ai',
                       'players': {chess.WHITE: user_id}, 'ai_level': level}
    await query.edit_message_text(f"✅ AI bilan o'yin (daraja: {level})")
    img = draw_board(board)
    await query.message.reply_photo(photo=img, caption="⬜ Siz oq rangdasiz. Dona tanlang!",
                                     reply_markup=move_keyboard(board))


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

    if game['mode'] == 'pvp' and game['players'].get(board.turn) != user_id:
        await query.answer("Sizning navbatingiz emas!", show_alert=True)
        return

    data = query.data

    if data == "resign":
        del games[chat_id]
        await query.edit_message_caption(caption="🏳️ Taslim bo'ldingiz! /start")
        return

    if data == "back":
        await query.edit_message_reply_markup(reply_markup=move_keyboard(board))
        return

    if data.startswith("sel_"):
        sq = int(data.split("_")[1])
        await query.edit_message_reply_markup(reply_markup=move_keyboard(board, selected=sq))
        return

    if data.startswith("move_"):
        uci = data.split("_")[1]
        move = chess.Move.from_uci(uci)
        board.push(move)

        if board.is_game_over():
            r = board.result()
            w = "⬜ Oq g'alaba!" if r=="1-0" else ("⬛ Qora g'alaba!" if r=="0-1" else "🤝 Durrang!")
            img = draw_board(board)
            await query.message.reply_photo(photo=img, caption=f"🏁 O'yin tugadi!\n{w}")
            del games[chat_id]
            return

        if game['mode'] == 'ai' and board.turn == chess.BLACK:
            ai_move = get_ai_move(board, game['ai_level'])
            board.push(ai_move)
            if board.is_game_over():
                r = board.result()
                w = "🤖 AI g'alaba!" if r=="0-1" else ("🎉 Siz g'alabadingiz!" if r=="1-0" else "🤝 Durrang!")
                img = draw_board(board)
                await query.message.reply_photo(photo=img, caption=f"🏁 O'yin tugadi!\n{w}")
                del games[chat_id]
                return

        img = draw_board(board)
        turn = "⬜ Oq" if board.turn == chess.WHITE else "⬛ Qora"
        check = " ⚠️ Shoh!" if board.is_check() else ""
        await query.message.reply_photo(photo=img, caption=f"{turn} navbati{check}",
                                         reply_markup=move_keyboard(board))


PIECE_VALUES = {chess.PAWN:100, chess.KNIGHT:320, chess.BISHOP:330,
                chess.ROOK:500, chess.QUEEN:900, chess.KING:20000}

def evaluate(board):
    if board.is_checkmate():
        return -99999 if board.turn==chess.BLACK else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for pt, val in PIECE_VALUES.items():
        score += len(board.pieces(pt, chess.WHITE)) * val
        score -= len(board.pieces(pt, chess.BLACK)) * val
    return score

def minimax(board, depth, alpha, beta, maximizing):
    if depth==0 or board.is_game_over():
        return evaluate(board), None
    best_move = None
    if maximizing:
        max_eval = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            ev, _ = minimax(board, depth-1, alpha, beta, False)
            board.pop()
            if ev > max_eval:
                max_eval, best_move = ev, move
            alpha = max(alpha, ev)
            if beta <= alpha: break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            ev, _ = minimax(board, depth-1, alpha, beta, True)
            board.pop()
            if ev < min_eval:
                min_eval, best_move = ev, move
            beta = min(beta, ev)
            if beta <= alpha: break
        return min_eval, best_move

def get_ai_move(board, level):
    depth = min(level//2+1, 3)
    _, move = minimax(board, depth, float('-inf'), float('inf'), False)
    return move if move else list(board.legal_moves)[0]


async def stop_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    games.pop(chat_id, None)
    waiting_games.pop(chat_id, None)
    await update.message.reply_text("🛑 O'yin to'xtatildi. /start")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_game))
    app.add_handler(CallbackQueryHandler(mode_select, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(ai_start, pattern="^ai_"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(sel_|move_|resign|back)"))
    print(f"Bot webhook rejimida ishga tushdi! Port: {PORT}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://{DOMAIN}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
