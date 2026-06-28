import os
import time
import queue
import threading
import ChessEngine

import pygame as pg
from ChessEngine import GameState
import socketio

BOARD_SIZE  = 512
PANEL_WIDTH = 220
WIDTH       = BOARD_SIZE + PANEL_WIDTH
HEIGHT      = BOARD_SIZE
DIMENSION   = 8
SQ_SIZE     = BOARD_SIZE // DIMENSION
MAX_FPS     = 60
IMAGES      = {}
ANIMATION_FRAMES = 6

CLOCK_START_SECONDS = 10 * 60

PANEL_BG    = (20,  22,  26)
TEXT_LIGHT  = (230, 235, 245)
TEXT_MID    = (150, 155, 165)
TEXT_DIM    = (100, 105, 115)
ACTIVE_GLOW = (80,  200, 120)
LOW_COLOR   = (220, 70,  70)
DIVIDER     = (40,  45,  55)

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
        sio.connect(SERVER_URL)
    except Exception as e:
        print(f"[Network] Could not connect to server: {e}")

def logic_to_screen(r, c, my_color):
    if my_color == 'black':
        return DIMENSION - 1 - r, DIMENSION - 1 - c
    return r, c

def screen_to_logic(sr, sc, my_color):
    if my_color == 'black':
        return DIMENSION - 1 - sr, DIMENSION - 1 - sc
    return sr, sc

def draw_menu(screen):
    screen.fill((20, 22, 26))
    title = _font(56, bold=True).render("GRANDMASTER", True, (240, 245, 255))
    subtitle = _font(24).render("CHESS", True, (150, 155, 165))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3 - 30))
    screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//3 + 30))

    buttons = [("Play Local", (HEIGHT//2 + 20)), ("Play Online", (HEIGHT//2 + 90))]
    rects = []
    
    mouse_pos = pg.mouse.get_pos()
    for label, y in buttons:
        btn_w, btn_h = 260, 55
        btn_x = WIDTH//2 - btn_w//2
        rect = pg.Rect(btn_x, y, btn_w, btn_h)
        
        color = (50, 55, 65) if rect.collidepoint(mouse_pos) else (35, 40, 48)
        
        pg.draw.rect(screen, color, rect, border_radius=6)
        pg.draw.rect(screen, (70, 75, 85), rect, width=1, border_radius=6)
        
        btn_surf = _font(20, bold=True).render(label.upper(), True, (230, 235, 245))
        screen.blit(btn_surf, (btn_x + btn_w//2 - btn_surf.get_width()//2, y + btn_h//2 - btn_surf.get_height()//2))
        rects.append((rect, label))
        
    return rects

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
    in_menu      = True
    load_images()

    player_time = {True: float(CLOCK_START_SECONDS), False: float(CLOCK_START_SECONDS)}
    last_tick   = time.monotonic()

    while True:
        now       = time.monotonic()
        delta     = now - last_tick
        last_tick = now

        if not in_menu and not game_over:
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

            elif e.type == pg.MOUSEBUTTONDOWN:
                if in_menu:
                    rects = draw_menu(screen)
                    for rect, label in rects:
                        if rect.collidepoint(e.pos):
                            if label == "Play Local":
                                global my_color
                                my_color = None
                                in_menu = False
                            elif label == "Play Online":
                                in_menu = False
                                threading.Thread(target=_connect, daemon=True).start()
                    continue

                if game_over:
                    continue

                is_my_turn = (my_color is None or
                              (my_color == 'white' and gs.whiteToMove) or
                              (my_color == 'black' and not gs.whiteToMove))
                if not is_my_turn:
                    continue
                col = pg.mouse.get_pos()[0] // SQ_SIZE
                row = pg.mouse.get_pos()[1] // SQ_SIZE
                if col >= DIMENSION or row >= DIMENSION or col < 0 or row < 0:
                    continue
                row, col = screen_to_logic(row, col, my_color)

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
                                    'endRow': vm.endRow, 'endCol': vm.endCol,
                                'whiteTime': player_time[True], 'blackTime': player_time[False]
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

        if in_menu:
            draw_menu(screen)
            pg.display.flip()
            clock.tick(MAX_FPS)
            continue

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
    s_startRow, s_startCol = logic_to_screen(move.startRow, move.startCol, my_color)
    s_endRow, s_endCol = logic_to_screen(move.endRow, move.endCol, my_color)
    dr = s_endRow - s_startRow
    dc = s_endCol - s_startCol
    for frame in range(ANIMATION_FRAMES + 1):
        t = frame / ANIMATION_FRAMES
        screen.fill(PANEL_BG)
        draw_board(screen)
        for sq in [(move.startRow, move.startCol), (move.endRow, move.endCol)]:
            sr, sc = logic_to_screen(sq[0], sq[1], my_color)
            hl = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            hl.fill((180, 160, 100, 80))
            screen.blit(hl, (sc * SQ_SIZE, sr * SQ_SIZE))
        for r in range(DIMENSION):
            for c in range(DIMENSION):
                piece = board[r][c]
                if piece != "--":
                    if frame < ANIMATION_FRAMES and r == move.endRow and c == move.endCol:
                        continue
                    sr, sc = logic_to_screen(r, c, my_color)
                    screen.blit(IMAGES[piece], pg.Rect(sc*SQ_SIZE, sr*SQ_SIZE, SQ_SIZE, SQ_SIZE))
        if move.pieceMoved in IMAGES:
            screen.blit(IMAGES[move.pieceMoved],
                        pg.Rect((s_startCol + dc*t)*SQ_SIZE,
                                (s_startRow + dr*t)*SQ_SIZE, SQ_SIZE, SQ_SIZE))
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
            sr, sc = logic_to_screen(sq[0], sq[1], my_color)
            s = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            s.fill((180, 160, 80, 70))
            screen.blit(s, (sc*SQ_SIZE, sr*SQ_SIZE))

    if sq_Selected:
        r, c = sq_Selected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'):
            sr, sc = logic_to_screen(r, c, my_color)
            sel = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            sel.fill((80, 120, 200, 90))
            screen.blit(sel, (sc*SQ_SIZE, sr*SQ_SIZE))
            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    er, ec = logic_to_screen(move.endRow, move.endCol, my_color)
                    dot = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
                    pg.draw.circle(dot, (40, 40, 40, 90),
                                   (SQ_SIZE//2, SQ_SIZE//2), SQ_SIZE//7)
                    screen.blit(dot, (ec*SQ_SIZE, er*SQ_SIZE))

    if gs.inCheck():
        king = gs.whiteKingLocation if gs.whiteToMove else gs.blackKingLocation
        kr, kc = logic_to_screen(king[0], king[1], my_color)
        ks = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
        ks.fill((200, 50, 50, 110))
        screen.blit(ks, (kc*SQ_SIZE, kr*SQ_SIZE))


def draw_board(screen):
    light = (220, 220, 220)
    dark  = (140, 45,  50)
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = light if (r + c) % 2 == 0 else dark
            sr, sc = logic_to_screen(r, c, my_color)
            pg.draw.rect(screen, color, pg.Rect(sc*SQ_SIZE, sr*SQ_SIZE, SQ_SIZE, SQ_SIZE))


def draw_pieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                sr, sc = logic_to_screen(r, c, my_color)
                screen.blit(IMAGES[piece], pg.Rect(sc*SQ_SIZE, sr*SQ_SIZE, SQ_SIZE, SQ_SIZE))


def fmt_time(seconds):
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def draw_panel(screen, gs, player_time):
    px = BOARD_SIZE
    pg.draw.rect(screen, PANEL_BG, pg.Rect(px, 0, PANEL_WIDTH, HEIGHT))
    pg.draw.line(screen, DIVIDER, (px, 0), (px, HEIGHT), 1)

    is_white_bottom = (my_color != 'black')

    def draw_player_card(is_white, is_bottom):
        y_center = HEIGHT - 80 if is_bottom else 80
        
        card_rect = pg.Rect(px + 16, y_center - 50, PANEL_WIDTH - 32, 100)
        pg.draw.rect(screen, (30, 33, 40), card_rect, border_radius=8)
        pg.draw.rect(screen, DIVIDER, card_rect, width=1, border_radius=8)
        
        active = (gs.whiteToMove == is_white)
        secs = player_time[is_white]
        low = secs < 30
        
        color = LOW_COLOR if low else (TEXT_LIGHT if active else TEXT_DIM)
        
        label = "WHITE" if is_white else "BLACK"
        if my_color is not None:
            label += " (YOU)" if (my_color == 'white') == is_white else " (OPP)"
            
        name = _font(12, bold=True).render(label, True, TEXT_MID)
        screen.blit(name, (px + 24, y_center - 36))
        
        time_str = fmt_time(secs)
        clk = _font(36, bold=True).render(time_str, True, color)
        screen.blit(clk, (px + 24, y_center - 10))
        
        if active:
            pg.draw.circle(screen, ACTIVE_GLOW, (px + PANEL_WIDTH - 32, y_center + 12), 6)
            pg.draw.circle(screen, (200, 255, 200), (px + PANEL_WIDTH - 32, y_center + 12), 3)

    draw_player_card(not is_white_bottom, is_bottom=False)
    draw_player_card(is_white_bottom, is_bottom=True)
    
    pg.draw.line(screen, DIVIDER, (px + 16, HEIGHT//2 - 40), (px + PANEL_WIDTH - 16, HEIGHT//2 - 40), 1)
    pg.draw.line(screen, DIVIDER, (px + 16, HEIGHT//2 + 40), (px + PANEL_WIDTH - 16, HEIGHT//2 + 40), 1)
    
    status_title = _font(10, bold=True).render("GAME STATUS", True, TEXT_DIM)
    screen.blit(status_title, (px + 20, HEIGHT//2 - 30))
    
    turn_text = "WHITE TO MOVE" if gs.whiteToMove else "BLACK TO MOVE"
    turn = _font(13, bold=True).render(turn_text, True, TEXT_LIGHT)
    screen.blit(turn, (px + 20, HEIGHT//2 - 10))
    
    for i, hint in enumerate(["z: Undo", "r: Reset"]):
        h = _font(11).render(hint, True, TEXT_MID)
        screen.blit(h, (px + 20, HEIGHT//2 + 10 + i*16))


def draw_end_overlay(screen, title, subtitle=""):
    veil = pg.Surface((BOARD_SIZE, HEIGHT), pg.SRCALPHA)
    veil.fill((10, 12, 15, 200))
    screen.blit(veil, (0, 0))

    t_surf = _font(36, bold=True).render(title, True, TEXT_LIGHT)
    s_surf = _font(14).render(subtitle, True, TEXT_MID)

    pad    = 30
    box_w  = max(t_surf.get_width(), s_surf.get_width()) + pad * 2
    box_h  = t_surf.get_height() + s_surf.get_height() + pad * 2
    box_x  = BOARD_SIZE // 2 - box_w // 2
    box_y  = HEIGHT // 2 - box_h // 2

    pg.draw.rect(screen, (25, 28, 35), pg.Rect(box_x, box_y, box_w, box_h), 0, 10)
    pg.draw.rect(screen, DIVIDER,      pg.Rect(box_x, box_y, box_w, box_h), 1, 10)

    screen.blit(t_surf, (BOARD_SIZE//2 - t_surf.get_width()//2, box_y + pad))
    screen.blit(s_surf, (BOARD_SIZE//2 - s_surf.get_width()//2,
                         box_y + pad + t_surf.get_height() + 10))


if __name__ == "__main__":
    main()
