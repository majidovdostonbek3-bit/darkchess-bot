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
async def ai_level_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    level = int(query.data.split("_")[1])
    board = chess.Board()
    games[chat_id] = {'board': board, 'mode': 'ai', 'players': {chess.WHITE: user_id}, 'ai_level': level}
    await query.edit_message_text(f"✅ *O'yin boshlandi! (AI darajasi: {level})*\n\n{board_to_text(board)}\n\n⬜ Siz oq rangdasiz!\nFormat: `e2e4`", parse_mode="Markdown")

PIECE_VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000}

def evaluate(board):
    if board.is_checkmate():
        return -99999 if board.turn == chess.BLACK else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for pt, val in PIECE_VALUES.items():
        score += len(board.pieces(pt, chess.WHITE)) * val
        score -= len(board.pieces(pt, chess.BLACK)) * val
    return score

def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
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
            if beta <= alpha:
                break
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
            if beta <= alpha:
                break
        return min_eval, best_move

def get_ai_move(board, level):
    depth = min(level // 2 + 1, 4)
    _, move = minimax(board, depth, float('-inf'), float('inf'), True)
    return move if move else list(board.legal_moves)[0]

async def handle_move(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    text = update.message.text.strip().lower()
    if chat_id not in games:
        await update.message.reply_text("O'yin yo'q. /start bilan boshlang.")
        return
    game = games[chat_id]
    board = game['board']
    if game['mode'] == 'pvp':
        if game['players'].get(board.turn) != user_id:
            await update.message.reply_text("⏳ Sizning navbatingiz emas!")
            return
    elif board.turn == chess.BLACK:
        return
    try:
        move = chess.Move.from_uci(text)
        if move not in board.legal_moves:
            move = board.parse_san(text)
    except:
        await update.message.reply_text("❌ Noto'g'ri yurish! Masalan: `e2e4`", parse_mode="Markdown")
        return
    board.push(move)
    if board.is_game_over():
        r = board.result()
        w = "⬜ Oq g'alaba!" if r=="1-0" else ("⬛ Qora g'alaba!" if r=="0-1" else "🤝 Durrang!")
        await update.message.reply_text(f"{board_to_text(board)}\n\n🏁 *O'yin tugadi!*\n{w}", parse_mode="Markdown")
        del games[chat_id]
        return
    extra = ""
    if game['mode'] == 'ai' and board.turn == chess.BLACK:
        ai_move = get_ai_move(board, game['ai_level'])
        board.push(ai_move)
        extra = f"\n🤖 AI: `{ai_move.uci()}`"
        if board.is_game_over():
            r = board.result()
            w = "🤖 AI g'alaba!" if r=="0-1" else ("🎉 Siz g'alabadingiz!" if r=="1-0" else "🤝 Durrang!")
            await update.message.reply_text(f"{board_to_text(board)}\n\n🏁 *O'yin tugadi!*\n{w}", parse_mode="Markdown")
            del games[chat_id]
            return
    turn = "⬜ Oq" if board.turn == chess.WHITE else "⬛ Qora"
    check = " ⚠️ Shoh ostida!" if board.is_check() else ""
    await update.message.reply_text(f"{board_to_text(board)}\n\n{turn} navbati{check}{extra}", parse_mode="Markdown")

async def stop_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in games:
        del games[chat_id]
        await update.message.reply_text("🛑 O'yin to'xtatildi.")
    else:
        await update.message.reply_text("Faol o'yin yo'q.")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("♟ *Shaxmat Bot*\n\n/start — Yangi o'yin\n/stop — To'xtatish\n\nYurish: `e2e4`, `g1f3`", parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop_game))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(mode_select, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(ai_level_select, pattern="^ai_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_move))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
