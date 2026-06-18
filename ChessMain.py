import os
import ChessEngine
import pygame as pg
from ChessEngine import GameState

WIDTH = 512
HEIGHT = 512

DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 60  # Increased for smooth animation
IMAGES = {}
ANIMATION_FRAMES = 8  # Number of frames to animate a move

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
    load_images()
    running = True
    animate = False  # flag to trigger animation
    sq_Selected = ()  # no square is selected
    playerClicks = []  # two tuples: [(6,4), (4,4)]

    while running:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            elif e.type == pg.MOUSEBUTTONDOWN:
                location = pg.mouse.get_pos()
                col = location[0] // SQ_SIZE
                row = location[1] // SQ_SIZE
                if sq_Selected == (row, col):  # clicked same square twice
                    sq_Selected = ()
                    playerClicks = []
                else:
                    sq_Selected = (row, col)
                    playerClicks.append(sq_Selected)
                if len(playerClicks) == 2:
                    move = ChessEngine.Move(playerClicks[0], playerClicks[1], gs.board)
                    gs.makeMove(move)
                    print(move.getChessNotation())
                    animate = True
                    playerClicks = []
                    sq_Selected = ()

        if animate and len(gs.moveLog) > 0:
            animate_move(gs.moveLog[-1], screen, gs.board, clock)
            animate = False

        draw_game_state(screen, gs, sq_Selected)
        clock.tick(MAX_FPS)
        pg.display.flip()

def animate_move(move, screen, board, clock):
    """Smoothly animates a piece sliding from start to end square."""
    colors = [pg.Color("white"), pg.Color("gray")]
    d_row = move.endRow - move.startRow
    d_col = move.endCol - move.startCol

    for frame in range(ANIMATION_FRAMES + 1):
        t = frame / ANIMATION_FRAMES  # progress 0.0 → 1.0

        # Draw the board and all pieces (without the moving piece at its destination)
        screen.fill(pg.Color("white"))
        draw_board(screen)

        # Highlight the start and end squares
        for sq in [(move.startRow, move.startCol), (move.endRow, move.endCol)]:
            highlight = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            highlight.fill((255, 255, 100, 100))
            screen.blit(highlight, (sq[1] * SQ_SIZE, sq[0] * SQ_SIZE))

        # Draw all pieces except the one being animated
        for r in range(DIMENSION):
            for c in range(DIMENSION):
                piece = board[r][c]
                if piece != "--":
                    # Skip the moved piece at its destination on all but the last frame
                    if frame < ANIMATION_FRAMES and r == move.endRow and c == move.endCol:
                        continue
                    screen.blit(IMAGES[piece], pg.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

        # Draw the animated piece at its interpolated position
        if move.pieceMoved in IMAGES:
            x = (move.startCol + d_col * t) * SQ_SIZE
            y = (move.startRow + d_row * t) * SQ_SIZE
            screen.blit(IMAGES[move.pieceMoved], pg.Rect(x, y, SQ_SIZE, SQ_SIZE))

        pg.display.flip()
        clock.tick(MAX_FPS)

def draw_game_state(screen, gs, sq_Selected=()):
    draw_board(screen)
    highlight_squares(screen, gs, sq_Selected)
    draw_pieces(screen, gs.board)

def highlight_squares(screen, gs, sq_Selected):
    """Highlight selected square and last move."""
    # Highlight last move
    if len(gs.moveLog) > 0:
        last = gs.moveLog[-1]
        for sq in [(last.startRow, last.startCol), (last.endRow, last.endCol)]:
            s = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
            s.fill((255, 255, 100, 80))
            screen.blit(s, (sq[1] * SQ_SIZE, sq[0] * SQ_SIZE))

    # Highlight selected square
    if sq_Selected != ():
        r, c = sq_Selected
        s = pg.Surface((SQ_SIZE, SQ_SIZE), pg.SRCALPHA)
        s.fill((0, 150, 255, 100))
        screen.blit(s, (c * SQ_SIZE, r * SQ_SIZE))

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

if __name__ == "__main__":
    main()
