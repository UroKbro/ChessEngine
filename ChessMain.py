import os
import time
import queue
import threading
import ChessEngine

import pygame as pg
from ChessEngine import GameState
import socketio

BOARD_SIZE  = 512
PANEL_WIDTH = 140
WIDTH       = BOARD_SIZE + PANEL_WIDTH
HEIGHT      = BOARD_SIZE
DIMENSION   = 8
SQ_SIZE     = BOARD_SIZE // DIMENSION
MAX_FPS     = 60
IMAGES      = {}
ANIMATION_FRAMES = 6

CLOCK_START_SECONDS = 10 * 60

PANEL_BG    = (248, 248, 246)
TEXT_DARK   = (28,  28,  28)
TEXT_MID    = (102, 102, 102)
TEXT_DIM    = (165, 165, 160)
ACTIVE_DOT  = (60,  60,  60)
LOW_COLOR   = (174, 67,  54)
DIVIDER     = (224, 224, 219)

_FONTS = {}

sio = socketio.Client()
SERVER_URL = os.environ.get("CHESS_SERVER_URL", "http://localhost:5000")

incoming_moves = queue.Queue()
my_color = None  # 'white' or 'black' — assigned by server

@sio.on('color')
def on_color(data):
    global my_color
    my_color = data['color']
    print(f"You are playing as {my_color.upper()}")

@sio.on('move')
def on_move(data):
    incoming_moves.put(data)

def _connect():
    try:
        sio.connect(SERVER_URL, transports=['websocket', 'polling'])
    except Exception as e:
        print(f"[Network] Could not connect to server: {e}")

threading.Thread(target=_connect, daemon=True).start()

def _font(size, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pg.font.SysFont(["SF Pro Display", "Helvetica Neue", "Arial", "sans-serif"], size, bold)
    return _FONTS[key]

def load_images():
    pieces = ['wP','wR','wN','wB','wQ','wK','bP','bR','bN','bB','bQ','bK']
    for p in pieces:
        path = os.path.join(os.path.dirname(__file__), "images", p + ".png")
        IMAGES[p] = pg.transform.scale(pg.image.load(path), (SQ_SIZE, SQ_SIZE))

def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Chess")
    clock = pg.time.Clock()

    gs           = GameState()
    validMoves   = gs.getValidMoves()
    moveMade     = False
    animate      = False
    sq_Selected  = ()
    playerClicks = []
    game_over    = False
    load_images()

    player_time = {True: float(CLOCK_START_SECONDS), False: float(CLOCK_START_SECONDS)}
    last_tick   = time.monotonic()

    while True:
        now       = time.monotonic()
        delta     = now - last_tick
        last_tick = now

        if not game_over:
            player_time[gs.whiteToMove] -= delta
            if player_time[gs.whiteToMove] <= 0:
                player_time[gs.whiteToMove] = 0
                game_over = True
                loser = "White" if gs.whiteToMove else "Black"
                gs.drawReason = f"{loser} ran out of time"
                gs.draw = True

        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
                return

            elif e.type == pg.MOUSEBUTTONDOWN and not game_over:
                is_my_turn = (my_color is None or
                              (my_color == 'white' and gs.whiteToMove) or
                              (my_color == 'black' and not gs.whiteToMove))
                if not is_my_turn:
                    continue
                col = pg.mouse.get_pos()[0] // SQ_SIZE
                row = pg.mouse.get_pos()[1] // SQ_SIZE
                if col >= DIMENSION or row >= DIMENSION or col < 0 or row < 0:
                    continue

                if sq_Selected == (row, col):
                    sq_Selected  = ()
                    playerClicks = []
                else:
                    sq_Selected = (row, col)
                    playerClicks.append(sq_Selected)

                if len(playerClicks) == 1:
                    piece = gs.board[playerClicks[0][0]][playerClicks[0][1]]
                    if (piece == "--"
                            or (gs.whiteToMove and piece[0] == 'b')
                            or (not gs.whiteToMove and piece[0] == 'w')):
                        sq_Selected  = ()
                        playerClicks = []

                if len(playerClicks) == 2:
                    move    = ChessEngine.Move(playerClicks[0], playerClicks[1], gs.board)
                    matched = False
                    for vm in validMoves:
                        if move == vm:
                            gs.makeMove(vm)
                            print(vm.getChessNotation())
                            moveMade = matched = animate = True
                            if sio.connected:
                                sio.emit('move', {
                                    'startRow': vm.startRow, 'startCol': vm.startCol,
                                    'endRow':   vm.endRow,   'endCol':   vm.endCol
                                })
                            break
                    if not matched:
                        piece = gs.board[row][col]
                        if piece != "--" and (
                                (gs.whiteToMove and piece[0] == 'w') or
                                (not gs.whiteToMove and piece[0] == 'b')):
                            sq_Selected  = (row, col)
                            playerClicks = [sq_Selected]
                        else:
                            sq_Selected  = ()
                            playerClicks = []
                    else:
                        sq_Selected  = ()
                        playerClicks = []

            elif e.type == pg.KEYDOWN:
                if e.key == pg.K_z:
                    gs.undoMove()
                    moveMade  = True
                    animate   = False
                    game_over = False
                elif e.key == pg.K_r:
                    gs           = GameState()
                    validMoves   = gs.getValidMoves()
                    sq_Selected  = ()
                    playerClicks = []
                    moveMade     = False
                    animate      = False
                    game_over    = False
                    player_time  = {True: float(CLOCK_START_SECONDS),
                                    False: float(CLOCK_START_SECONDS)}
                    last_tick    = time.monotonic()

        # Process incoming network moves from opponent
        while not incoming_moves.empty():
            data = incoming_moves.get()
            net_move = ChessEngine.Move(
                (data['startRow'], data['startCol']),
                (data['endRow'],   data['endCol']),
                gs.board
            )
            for vm in validMoves:
                if net_move == vm:
                    animate_move(vm, screen, gs.board, clock)
                    gs.makeMove(vm)
                    validMoves = gs.getValidMoves()
                    break

        if moveMade:
            if animate and gs.moveLog:
                animate_move(gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.getValidMoves()
            moveMade   = False

        screen.fill(PANEL_BG)
        draw_game_state(screen, gs, validMoves, sq_Selected)
        draw_panel(screen, gs, player_time)

        if gs.checkmate:
            game_over = True
            winner = "Black" if gs.whiteToMove else "White"
            draw_end_overlay(screen, f"{winner} wins", "checkmate  ·  press R to restart")
        elif gs.draw:
            game_over = True
            draw_end_overlay(screen, "Draw", f"{gs.drawReason}  ·  press R to restart")

        clock.tick(MAX_FPS)
        pg.display.flip()


def animate_move(move, screen, board, clock):
    dr = move.endRow  - move.startRow
    dc = move.endCol  - move.startCol
    for frame in range(ANIMATION_FRAMES + 1):
        t = frame / ANIMATION_FRAMES
        screen.fill(PANEL_BG)
        draw_board(screen)
        for sq in [(move.startRow, move.startCol), (move.endRow, move.endCol)]:
            hl = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            hl.fill((180, 160, 100, 80))
            screen.blit(hl, (sq[1] * SQ_SIZE, sq[0] * SQ_SIZE))
        for r in range(DIMENSION):
            for c in range(DIMENSION):
                piece = board[r][c]
                if piece != "--":
                    if frame < ANIMATION_FRAMES and r == move.endRow and c == move.endCol:
                        continue
                    screen.blit(IMAGES[piece], pg.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))
        if move.pieceMoved in IMAGES:
            screen.blit(IMAGES[move.pieceMoved],
                        pg.Rect((move.startCol + dc*t)*SQ_SIZE,
                                (move.startRow + dr*t)*SQ_SIZE, SQ_SIZE, SQ_SIZE))
        pg.display.flip()
        clock.tick(MAX_FPS)


def draw_game_state(screen, gs, validMoves, sq_Selected=()):
    draw_board(screen)
    highlight_squares(screen, gs, validMoves, sq_Selected)
    draw_pieces(screen, gs.board)


def highlight_squares(screen, gs, validMoves, sq_Selected):
    if gs.moveLog:
        last = gs.moveLog[-1]
        for sq in [(last.startRow, last.startCol), (last.endRow, last.endCol)]:
            s = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            s.fill((180, 160, 80, 70))
            screen.blit(s, (sq[1]*SQ_SIZE, sq[0]*SQ_SIZE))

    if sq_Selected:
        r, c = sq_Selected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'):
            sel = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            sel.fill((80, 120, 200, 90))
            screen.blit(sel, (c*SQ_SIZE, r*SQ_SIZE))
            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    dot = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
                    pg.draw.circle(dot, (40, 40, 40, 90),
                                   (SQ_SIZE//2, SQ_SIZE//2), SQ_SIZE//7)
                    screen.blit(dot, (move.endCol*SQ_SIZE, move.endRow*SQ_SIZE))

    if gs.inCheck():
        king = gs.whiteKingLocation if gs.whiteToMove else gs.blackKingLocation
        ks = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
        ks.fill((200, 50, 50, 110))
        screen.blit(ks, (king[1]*SQ_SIZE, king[0]*SQ_SIZE))


def draw_board(screen):
    light = (235, 228, 215)
    dark  = (175, 160, 135)
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = light if (r + c) % 2 == 0 else dark
            pg.draw.rect(screen, color, pg.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))


def draw_pieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], pg.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))


def fmt_time(seconds):
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def draw_panel(screen, gs, player_time):
    px = BOARD_SIZE
    pg.draw.rect(screen, PANEL_BG, pg.Rect(px, 0, PANEL_WIDTH, HEIGHT))
    pg.draw.line(screen, DIVIDER, (px, 0), (px, HEIGHT), 1)

    cx = px + PANEL_WIDTH // 2

    title = _font(12, bold=True).render("STATUS", True, TEXT_DIM)
    screen.blit(title, (cx - title.get_width() // 2, 18))

    def draw_clock(secs, label, active, y_top):
        low   = secs < 30
        color = LOW_COLOR if low else (TEXT_DARK if active else TEXT_MID)

        name  = _font(12, bold=True).render(label.upper(), True, TEXT_MID)
        screen.blit(name, (cx - name.get_width()//2, y_top))

        time_str = fmt_time(secs)
        clk = _font(24, bold=True).render(time_str, True, color)
        screen.blit(clk, (cx - clk.get_width()//2, y_top + 18))

        if active:
            pg.draw.circle(screen, color, (cx, y_top + 52), 3)

        if low and active:
            warn = _font(10, bold=True).render("LOW", True, LOW_COLOR)
            screen.blit(warn, (cx - warn.get_width()//2, y_top + 60))

    draw_clock(player_time[False], "black", not gs.whiteToMove, HEIGHT//2 - 94)
    draw_clock(player_time[True],  "white", gs.whiteToMove,     HEIGHT//2 + 18)

    pg.draw.line(screen, DIVIDER, (px + 18, HEIGHT//2), (px + PANEL_WIDTH - 18, HEIGHT//2), 1)

    turn_text = "WHITE TO MOVE" if gs.whiteToMove else "BLACK TO MOVE"
    turn = _font(10, bold=True).render(turn_text, True, TEXT_MID)
    screen.blit(turn, (cx - turn.get_width()//2, HEIGHT//2 - 8))

    for i, hint in enumerate(["z  undo", "r  reset"]):
        h = _font(10).render(hint.upper(), True, TEXT_DIM)
        screen.blit(h, (cx - h.get_width()//2, HEIGHT - 32 + i*14))


def draw_end_overlay(screen, title, subtitle=""):
    veil = pg.Surface((BOARD_SIZE, HEIGHT), pg.SRCALPHA)
    veil.fill((245, 245, 242, 210))
    screen.blit(veil, (0, 0))

    t_surf = _font(26, bold=True).render(title, True, TEXT_DARK)
    s_surf = _font(12).render(subtitle, True, TEXT_MID)

    pad    = 28
    box_w  = max(t_surf.get_width(), s_surf.get_width()) + pad * 2
    box_h  = t_surf.get_height() + s_surf.get_height() + pad * 2
    box_x  = BOARD_SIZE // 2 - box_w // 2
    box_y  = HEIGHT // 2 - box_h // 2

    pg.draw.rect(screen, (255, 255, 253), pg.Rect(box_x, box_y, box_w, box_h), 0, 6)
    pg.draw.rect(screen, DIVIDER,         pg.Rect(box_x, box_y, box_w, box_h), 1, 6)

    screen.blit(t_surf, (BOARD_SIZE//2 - t_surf.get_width()//2, box_y + pad))
    screen.blit(s_surf, (BOARD_SIZE//2 - s_surf.get_width()//2,
                         box_y + pad + t_surf.get_height() + 8))


if __name__ == "__main__":
    main()
