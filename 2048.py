import curses
from curses import wrapper
import random
import time
import os
import sys

BOARD_SIZE = 4
HIGHSCORE_FILE = "2048_highscore.txt"

# ------------------------- GAME LOGIC -------------------------

def init_board():
    board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    add_random_tile(board)
    add_random_tile(board)
    return board


def add_random_tile(board):
    empty = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if board[r][c] == 0]
    if not empty:
        return
    r, c = random.choice(empty)
    board[r][c] = 2 if random.random() < 0.9 else 4


def compress(row):
    new = [x for x in row if x != 0]
    new += [0] * (BOARD_SIZE - len(new))
    return new


def merge(row, score):
    for i in range(BOARD_SIZE - 1):
        if row[i] != 0 and row[i] == row[i + 1]:
            row[i] *= 2
            score += row[i]
            row[i + 1] = 0
    return row, score


def move_left(board, score):
    moved = False
    new_board = []
    for row in board:
        c = compress(row)
        m, score = merge(c, score)
        f = compress(m)
        if f != row:
            moved = True
        new_board.append(f)
    return new_board, moved, score


def move_right(board, score):
    rev = [r[::-1] for r in board]
    new_rev, moved, score = move_left(rev, score)
    new_board = [r[::-1] for r in new_rev]
    return new_board, moved, score


def move_up(board, score):
    trans = list(map(list, zip(*board)))
    new_trans, moved, score = move_left(trans, score)
    new_board = list(map(list, zip(*new_trans)))
    return new_board, moved, score


def move_down(board, score):
    trans = list(map(list, zip(*board)))
    new_trans, moved, score = move_right(trans, score)
    new_board = list(map(list, zip(*new_trans)))
    return new_board, moved, score


def is_game_over(board):
    # if any empty cell -> not over
    for row in board:
        if 0 in row:
            return False
    # horizontal
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):
            if board[r][c] == board[r][c + 1]:
                return False
    # vertical
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE):
            if board[r][c] == board[r + 1][c]:
                return False
    return True

# ------------------------- HIGHSCORE -------------------------

def load_highscore():
    try:
        if os.path.exists(HIGHSCORE_FILE):
            with open(HIGHSCORE_FILE, 'r') as f:
                return int(f.read().strip() or 0)
    except Exception:
        pass
    return 0


def save_highscore(value):
    try:
        with open(HIGHSCORE_FILE, 'w') as f:
            f.write(str(int(value)))
    except Exception:
        pass

# ------------------------- CURSES UI helpers -------------------------

def init_colors():
    # set up a few color pairs; if terminal doesn't support colors, calls fail silently
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)   # tile background light
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_BLUE)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)
    except Exception:
        pass


def draw_background(stdscr):
    # intentionally do nothing — user requested no background color
    stdscr.erase()


def draw_box_tile(stdscr, top, left, width, height, val, color_pair_id=None):
    # Draw a confined box; tile color fills only the interior
    try:
        # box border
        horiz = '─' * (width - 2)
        stdscr.addstr(top, left, '┌' + horiz + '┐')
        for row in range(1, height - 1):
            stdscr.addstr(top + row, left, '│' + ' ' * (width - 2) + '│')
        stdscr.addstr(top + height - 1, left, '└' + horiz + '┘')

        # fill interior with color if available (confined)
        if color_pair_id:
            for row in range(1, height - 1):
                try:
                    stdscr.addstr(top + row, left + 1, ' ' * (width - 2), curses.color_pair(color_pair_id))
                except Exception:
                    pass

        # draw centered number (bigger font by spacing)
        num = '' if val == 0 else str(val)
        if num:
            mid_row = top + (height // 2)
            content = num.center(width - 2)
            try:
                stdscr.addstr(mid_row, left + 1, content, curses.A_BOLD)
            except Exception:
                pass
    except Exception:
        # fallback simple representation
        try:
            stdscr.addstr(top, left, '[' + (str(val) if val else '.') + ']')
        except Exception:
            pass


def choose_color_id_for_value(val):
    if not val:
        return 1
    length = val.bit_length()
    # map bit_length to pair 2..6
    return 2 + ((length - 1) % 5)

# ------------------------- SIMPLE MENU -------------------------

def menu_screen(stdscr):
    curses.curs_set(0)
    h, w = stdscr.getmaxyx()
    title = "2048"
    subtitle = "Soft Boxes Edition"
    options = ["Start Game", "Quit"]
    selected = 0

    how_to_play = [
        "+-----------------------------+",
        "|          HOW TO PLAY        |",
        "|  Use ↑ ↓ ← → to move        |",
        "|  Combine same tiles         |",
        "|  Press R to restart         |",
        "|  Press Q to quit            |",
        "|  Press ENTER to start       |",
        "+-----------------------------+",
    ]

    while True:
        stdscr.erase()
        try:
            # Title
            stdscr.addstr(2, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.A_UNDERLINE)
            stdscr.addstr(4, max(0, (w - len(subtitle)) // 2), subtitle)

            # HOW TO PLAY box centered
            start_y = 6
            for i, line in enumerate(how_to_play):
                stdscr.addstr(start_y + i, max(0, (w - len(line)) // 2), line)

            # Options (Start / Quit)
            offset = start_y + len(how_to_play) + 2
            for i, opt in enumerate(options):
                y = offset + i * 3
                x = max(0, (w - 20) // 2)
                box_w = 20
                box_h = 3

                # draw border
                draw_box_tile(stdscr, y, x, box_w, box_h, 0, color_pair_id=None)

                label_x = x + (box_w - len(opt)) // 2
                if i == selected:
                    stdscr.addstr(y + 1, label_x, opt, curses.A_REVERSE | curses.A_BOLD)
                else:
                    stdscr.addstr(y + 1, label_x, opt)

        except Exception:
            pass

        stdscr.refresh()
        k = stdscr.getch()

        if k in (curses.KEY_UP, ord('w')):
            selected = (selected - 1) % len(options)
        elif k in (curses.KEY_DOWN, ord('s')):
            selected = (selected + 1) % len(options)
        elif k in (10, 13):
            if options[selected] == "Start Game":
                return
            else:
                raise SystemExit
        elif k == ord('q'):
            raise SystemExit

# ------------------------- LOSE SCREEN -------------------------

def lose_screen(stdscr, score, highscore):
    h, w = stdscr.getmaxyx()
    lines = ["== You Lost ==", f"Score: {score}", f"Highscore: {highscore}", "", "Press r to restart, q to quit"]
    while True:
        stdscr.erase()
        for i, ln in enumerate(lines):
            try:
                stdscr.addstr(h // 2 - 2 + i, max(0, (w - len(ln)) // 2), ln)
            except Exception:
                pass
        stdscr.refresh()
        k = stdscr.getch()
        if k == ord('r'):
            return 'restart'
        if k == ord('q'):
            return 'quit'

# ------------------------- MAIN GAME LOOP (curses) -------------------------

def curses_main(stdscr):
    init_colors()
    menu_screen(stdscr)
    highscore = load_highscore()

    while True:
        board = init_board()
        score = 0
        while True:
            draw_background(stdscr)
            h, w = stdscr.getmaxyx()
            tile_w = 9
            tile_h = 5
            board_w = BOARD_SIZE * tile_w
            board_h = BOARD_SIZE * tile_h
            start_y = max(3, (h - board_h) // 2)
            start_x = max(3, (w - board_w) // 2)

            # draw tiles
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    val = board[r][c]
                    top = start_y + r * tile_h
                    left = start_x + c * tile_w
                    color_id = choose_color_id_for_value(val)
                    draw_box_tile(stdscr, top, left, tile_w, tile_h, val, color_pair_id=color_id)

            # draw score
            try:
                stdscr.addstr(start_y - 3, start_x, f"Score: {score}   Highscore: {highscore}")
            except Exception:
                pass

            stdscr.refresh()
            k = stdscr.getch()
            moved = False
            if k == curses.KEY_LEFT:
                board, moved, score = move_left(board, score)
            elif k == curses.KEY_RIGHT:
                board, moved, score = move_right(board, score)
            elif k == curses.KEY_UP:
                board, moved, score = move_up(board, score)
            elif k == curses.KEY_DOWN:
                board, moved, score = move_down(board, score)
            elif k == ord('q'):
                return
            if moved:
                add_random_tile(board)
            if is_game_over(board):
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)
                action = lose_screen(stdscr, score, highscore)
                if action == 'restart':
                    break
                else:
                    return

# ------------------------- TESTS -------------------------

def run_tests():
    b = [[2, 2, 0, 0], [0] * 4, [0] * 4, [0] * 4]
    nb, m, s = move_left(b, 0)
    assert nb[0][0] == 4 and s == 4
    b = [[2, 0, 0, 0], [0] * 4, [0] * 4, [0] * 4]
    nb, m, s = move_left(b, 0)
    assert m is False
    b = [[2, 0, 0, 0], [0] * 4, [0] * 4, [0] * 4]
    nb, m, s = move_right(b, 0)
    assert nb[0][-1] == 2
    b = [[2, 0, 0, 0], [2, 0, 0, 0], [0] * 4, [0] * 4]
    nb, m, s = move_up(b, 0)
    assert nb[0][0] == 4 and s == 4
    b = [[0, 0, 0, 0], [2, 0, 0, 0], [2, 0, 0, 0], [0, 0, 0, 0]]
    nb, m, s = move_down(b, 0)
    assert nb[-1][0] == 4 and m is True and s == 4
    print('All tests passed.')

# ------------------------- ENTRY POINT -------------------------

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_tests()
        sys.exit(0)
    try:
        curses.wrapper(curses_main)
    except Exception as e:
        print('Failed to start curses UI:', e)
        print('Run this script in a proper terminal and (on Windows) install windows-curses.')
