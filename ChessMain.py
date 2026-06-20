import os
import ChessEngine
import pygame as pg
from ChessEngine import GameState

WIDTH = 512
HEIGHT = 512

DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 60 
IMAGES = {}
ANIMATION_FRAMES = 8

def load_images():
    pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
    for piece in pieces:
        path = os.path.join(os.path.dirname(__file__), "images", piece + ".png")
        IMAGES[piece] = pg.transform.scale(pg.image.load(path), (SQ_SIZE, SQ_SIZE))

def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Chess")
    clock = pg.time.Clock()
    screen.fill(pg.Color("white"))
    gs = GameState()
    validMoves = gs.getValidMoves()
    moveMade = False # flag variable for when a move is made
    load_images()
    running = True
    animate = False 
    sq_Selected = ()  
    playerClicks = [] 
    game_over = False

    while running:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            elif e.type == pg.MOUSEBUTTONDOWN:
                if not game_over:
                    location = pg.mouse.get_pos()
                    col = location[0] // SQ_SIZE
                    row = location[1] // SQ_SIZE
                    if sq_Selected == (row, col) or col >= 8 or row >= 8 or col < 0 or row < 0: 
                        sq_Selected = ()
                        playerClicks = []
                    else:
                        sq_Selected = (row, col)
                        playerClicks.append(sq_Selected)
                    if len(playerClicks) == 1:
                        # Make sure they click their own piece
                        piece = gs.board[playerClicks[0][0]][playerClicks[0][1]]
                        if piece == "--" or (gs.whiteToMove and piece[0] == 'b') or (not gs.whiteToMove and piece[0] == 'w'):
                            sq_Selected = ()
                            playerClicks = []
                    if len(playerClicks) == 2:
                        move = ChessEngine.Move(playerClicks[0], playerClicks[1], gs.board)
                        for i in range(len(validMoves)):
                            if move == validMoves[i]:
                                gs.makeMove(validMoves[i])
                                print(validMoves[i].getChessNotation())
                                moveMade = True
                                animate = True
                                break
                        if not moveMade:
                            # If they click on another of their own pieces, make that the new selection
                            piece = gs.board[row][col]
                            if piece != "--" and ((gs.whiteToMove and piece[0] == 'w') or (not gs.whiteToMove and piece[0] == 'b')):
                                sq_Selected = (row, col)
                                playerClicks = [sq_Selected]
                            else:
                                sq_Selected = ()
                                playerClicks = []
                        else:
                            playerClicks = []
                            sq_Selected = ()
            elif e.type == pg.KEYDOWN:
                if e.key == pg.K_z: # undo move
                    gs.undoMove()
                    moveMade = True
                    animate = False
                    game_over = False
                elif e.key == pg.K_r: # reset board
                    gs = GameState()
                    validMoves = gs.getValidMoves()
                    sq_Selected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    game_over = False

        if moveMade:
            if animate and len(gs.moveLog) > 0:
                animate_move(gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.getValidMoves()
            moveMade = False

        draw_game_state(screen, gs, validMoves, sq_Selected)

        if gs.checkmate:
            game_over = True
            if gs.whiteToMove:
                draw_end_game_text(screen, "Black wins by checkmate")
            else:
                draw_end_game_text(screen, "White wins by checkmate")
        elif gs.stalemate:
            game_over = True
            draw_end_game_text(screen, "Stalemate")

        clock.tick(MAX_FPS)
        pg.display.flip()

def animate_move(move, screen, board, clock):
    d_row = move.endRow - move.startRow
    d_col = move.endCol - move.startCol

    for frame in range(ANIMATION_FRAMES + 1):
        t = frame / ANIMATION_FRAMES  

        screen.fill(pg.Color("white"))
        draw_board(screen)

        for sq in [(move.startRow, move.startCol), (move.endRow, move.endCol)]:
            highlight = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            highlight.fill((255, 255, 100, 100))
            screen.blit(highlight, (sq[1] * SQ_SIZE, sq[0] * SQ_SIZE))

        for r in range(DIMENSION):
            for c in range(DIMENSION):
                piece = board[r][c]
                if piece != "--":
                    if frame < ANIMATION_FRAMES and r == move.endRow and c == move.endCol:
                        continue
                    screen.blit(IMAGES[piece], pg.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))
        if move.pieceMoved in IMAGES:
            x = (move.startCol + d_col * t) * SQ_SIZE
            y = (move.startRow + d_row * t) * SQ_SIZE
            screen.blit(IMAGES[move.pieceMoved], pg.Rect(x, y, SQ_SIZE, SQ_SIZE))

        pg.display.flip()
        clock.tick(MAX_FPS)

def draw_game_state(screen, gs, validMoves, sq_Selected=()):
    draw_board(screen)
    highlight_squares(screen, gs, validMoves, sq_Selected)
    draw_pieces(screen, gs.board)

def highlight_squares(screen, gs, validMoves, sq_Selected):
    if len(gs.moveLog) > 0:
        last = gs.moveLog[-1]
        for sq in [(last.startRow, last.startCol), (last.endRow, last.endCol)]:
            s = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            s.fill((255, 255, 100, 80))
            screen.blit(s, (sq[1] * SQ_SIZE, sq[0] * SQ_SIZE))

    if sq_Selected != ():
        r, c = sq_Selected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'):
            # Highlight selected square
            s = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            s.fill((0, 150, 255, 100))
            screen.blit(s, (c * SQ_SIZE, r * SQ_SIZE))
            # Highlight valid moves
            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    s2 = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
                    pg.draw.circle(s2, (0, 200, 0, 120), (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 6)
                    screen.blit(s2, (move.endCol * SQ_SIZE, move.endRow * SQ_SIZE))

def draw_board(screen):
    colors = [pg.Color("white"), pg.Color("gray")]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[((r + c) % 2)]
            pg.draw.rect(screen, color, pg.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_pieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], pg.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_end_game_text(screen, text):
    font = pg.font.SysFont("Helvetica", 32, True, False)
    text_object = font.render(text, 0, pg.Color('Black'))
    text_location = pg.Rect(0, 0, WIDTH, HEIGHT).move(WIDTH // 2 - text_object.get_width() // 2, HEIGHT // 2 - text_object.get_height() // 2)
    # Draw transparent overlay
    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    overlay.fill(pg.Color("white"))
    screen.blit(overlay, (0, 0))
    # Box
    box_rect = pg.Rect(text_location.left - 20, text_location.top - 10, text_object.get_width() + 40, text_object.get_height() + 20)
    pg.draw.rect(screen, pg.Color("darkgray"), box_rect, 0, 10)
    pg.draw.rect(screen, pg.Color("black"), box_rect, 2, 10)
    screen.blit(text_object, text_location)

if __name__ == "__main__":
    main()
