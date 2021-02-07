import os
import json
import pygame
from io import BytesIO
import requests
import time
from .board import Board
from .gui import SelectionGroup, Input, Button, Label, InputDialogue
from .leaderboard import Leaderboard
from .boardaxis import BoardAxis
from .danmuji import Danmuji

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')


def load_image(name, size=None):
    """Load image and optionally resize it."""
    path = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(path)
    except pygame.error as error:
        print('Cannot load image: ', path)
        raise SystemError(error)

    if size is not None:
        if isinstance(size, int):
            size = (size, size)
        image = pygame.transform.scale(image, size)

    return image


def load_random_image():
    """Load a random image from http://www.dmoe.cc/random.php
    http://api.mtyqx.cn/api/random.php
    https://img.asmdh.com/img.php
    """
    try:
        link = 'https://img.asmdh.com/img.php'
        time0 = time.time()
        print('getting image from', link)
        image = pygame.image.load(BytesIO(requests.get(link).content))
        print('done in ', time.time() - time0, 's')
        return image
    except:
        image = load_image('bg.png')
        return image


def load_font(name, size):
    path = os.path.join(ASSETS_DIR, name)
    try:
        font = pygame.font.Font(path, size)
    except pygame.error as error:
        print('Cannot load font: ', path)
        raise SystemError(error)
    return font


class Timer:
    """Execute event on timer.

    Parameters
    ----------
    on_time_event L callable
        Call this event on timer.
    """

    def __init__(self, on_time_event, countdown_label=None, show_label_interval=None):
        self.on_time_event = on_time_event
        self.start_time = None
        self.interval = None
        self.running = False
        self.countdown_label = countdown_label
        self.show_label_interval = show_label_interval

    def start(self, interval):
        """Start timer now and trigger event after `interval`."""
        self.running = True
        self.interval = interval
        self.start_time = pygame.time.get_ticks()

    def stop(self):
        """Stop timer before interval"""
        self.running = False

    def check(self):
        """Check whether event occurred.

        Must be called continuously in the main loop."""
        if self.running is False:
            return

        countdown = self.start_time + self.interval - pygame.time.get_ticks()
        if self.countdown_label is not None:
            if countdown > 0 and (self.show_label_interval is None or countdown <= self.show_label_interval):
                text = str(countdown//1000)
            else:
                text = ""
            self.countdown_label.set_text(text)

        if countdown <= 0:
            self.running = False
            self.on_time_event()


def create_count_tiles(tile_size, font_name):
    """Create tiles for mine counts.

    Additionally an empty tile without a digit is returned for 0

    Parameters
    ----------
    tile_size
        Size of tiles.
    font_name : string
        Font name to be found in resources directory. The size will be 0.9
        of `tile_size`.

    Returns
    -------
    tiles : list of pygame.Surface
        List of tiles containing 9 elements.
    """
    colors = [
        None,
        'Blue',
        'Dark Green',
        'Red',
        'Navy',
        'Brown',
        'Light Sea Green',
        'Black',
        'Dim Gray'
    ]

    font_size = int(tile_size * 0.9)
    font = load_font(font_name, font_size)

    empty_tile = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    center = empty_tile.get_rect().center

    tiles = [empty_tile.copy()]

    for count in range(1, 9):
        glyph = font.render(str(count), True, pygame.Color(colors[count]))
        width = glyph.get_rect().width

        glyph_center = (center[0] + int(0.15 * width), center[1])
        rect = glyph.get_rect(center=glyph_center)
        tile = empty_tile.copy()
        tile.blit(glyph, rect.topleft)
        tiles.append(tile)

    return tiles


def is_key_suitable_for_name(key_name):
    """Check if a key is suitable for name input."""
    return len(key_name) == 1 and key_name.isalnum() or key_name in ['-', '_']


def is_digit(key_name):
    """Check if a key is a digit."""
    return len(key_name) == 1 and key_name.isnumeric()


class Game:
    """Main game class."""
    BOARD_SIZE = 550
    GUI_WIDTH = 500
    MARGIN = 50
    # BG_COLOR = pygame.Color('Light Slate Gray')
    # FIELD_BG_COLOR = pygame.Color('#d7dcdc')
    # FIELD_LINES_COLOR = pygame.Color('#738383')
    # GUI_FONT_COLOR = pygame.Color('Light Yellow')
    # GUI_FONT_SIZE = 13
    BG_COLOR = pygame.Color('#fdf0f4')
    FIELD_BG_COLOR = pygame.Color('#ffffff')
    FIELD_LINES_COLOR = pygame.Color('#ffffff')
    GUI_FONT_COLOR = pygame.Color('#000000')
    HUD_FONT_COLOR = pygame.Color('#646de6')
    GUI_FONT_SIZE = 20
    HUD_FONT_SIZE = 30
    DIGITS = {chr(c) for c in range(ord('0'), ord('9') + 1)}
    MAX_BOARD_DIMENSION = 50
    MIN_BOARD_DIMENSION_DISPLAY = 10
    MAX_NAME_LENGTH = 8
    DELAY_BEFORE_NAME_INPUT_MS = 1000
    DELAY_BEFORE_RESTART_MS = 10000
    PLAYER_INPUT_INTERVAL_MS = 60000

    def __init__(self, state_file_path):
        self.player = "all"
        self.dmj = Danmuji("299992")
        self.dmj.run()

        try:
            with open(state_file_path) as state_file:
                state = json.load(state_file)
        except (IOError, json.JSONDecodeError):
            state = {}

        display_info = pygame.display.Info()
        self.max_cols = 16
        self.max_rows = 16

        if "leaderboard" in state:
            leaderboard_data = state['leaderboard']
        else:
            leaderboard_data = {'EASY': [], 'NORMAL': []}

        self.n_rows = state.get('n_rows', 10)
        self.n_cols = state.get('n_cols', 10)
        self.n_mines = state.get('n_mines', 10)
        self.difficulty = state.get('difficulty', 'EASY')

        tile_size = self.BOARD_SIZE // min(self.n_rows, self.n_cols)

        mine_count_images = create_count_tiles(tile_size,
                                               "kenvector_future.ttf")
        tile_image = load_image('tile.png', tile_size)
        mine_image = load_image('mine.png', tile_size)
        flag_image = load_image('flag.png', tile_size)
        bg_image = load_random_image()
        # gui_font = load_font("Akrobat-Bold.otf", self.GUI_FONT_SIZE)
        gui_font = load_font("STHeiti-Thin-1.ttc", self.GUI_FONT_SIZE)
        hud_font = load_font("STHeiti-Medium-4.ttc", self.HUD_FONT_SIZE)
        self.board = Board(
            self.n_rows, self.n_cols, self.n_mines,
            self.FIELD_BG_COLOR, self.FIELD_LINES_COLOR, tile_size,
            tile_image, mine_count_images, flag_image, mine_image, bg_image,
            on_status_change_callback=self.on_status_change)

        self.board_axis = BoardAxis(self.board, gui_font, self.GUI_FONT_COLOR)

        """ screen """
        self.screen = None
        self.screen_rect = None
        self.screen_image = None
        self.gui_rect = None
        self.init_screen()

        """ gui """
        self.difficulty_hint = Label(gui_font, self.GUI_FONT_COLOR, "当前难度：" + self.difficulty)

        self.leaderboard = Leaderboard(gui_font, self.GUI_FONT_COLOR,
                                       10, self.GUI_WIDTH,
                                       data=leaderboard_data)

        self.victory_time = Label(gui_font, self.GUI_FONT_COLOR, "")
        self.leaderboard_announcement = Label(
            gui_font, self.GUI_FONT_COLOR,
            "YOU MADE IT TO THE LEADERBOARD!")

        self.timer = Input(hud_font, self.HUD_FONT_COLOR,
                           '', self.board.time)
        self.current_mines = Input(hud_font, self.HUD_FONT_COLOR,
                                   '', self.board.n_mines)
        self.player_display = Label(hud_font, self.HUD_FONT_COLOR, "")

        self.status = Label(hud_font, self.HUD_FONT_COLOR, "READY TO GO!")
        self.countdown = Label(hud_font, self.HUD_FONT_COLOR, "")

        self.gameover_restart_timer = Timer(self.reset_game, self.countdown)
        self.player_input_timer = Timer(self.reset_player, self.countdown, 30000)

        self.place_gui()
        self.keep_running = None
        self.mode = "game"

    def init_screen(self):
        """Initialize screen and compute rectangles for different regions."""
        self.screen_image = load_image('screen.png')
        self.screen_rect = self.screen_image.get_rect()
        self.screen = pygame.display.set_mode((self.screen_rect.width, self.screen_rect.height))

        self.board.rect = pygame.Rect(704,
                                      116,
                                      self.BOARD_SIZE,
                                      self.BOARD_SIZE)

        self.board_axis.set(self.board)

        self.gui_rect = pygame.Rect(50,
                                    50,
                                    self.GUI_WIDTH,
                                    400)

    def place_gui(self):
        """Place GUI element according to the current settings."""
        self.difficulty_hint.rect.left = self.gui_rect.left
        self.difficulty_hint.rect.top = self.gui_rect.top

        self.leaderboard.rect.centerx = self.gui_rect.centerx
        self.leaderboard.rect.top = self.difficulty_hint.rect.bottom

        self.leaderboard_announcement.rect.top = (
                self.victory_time.rect.bottom
                + 0.4 * self.victory_time.rect.height)
        self.leaderboard_announcement.rect.centerx = self.screen_rect.centerx

        self.timer.rect.center = (800, 70)
        self.current_mines.rect.center = (940, 70)
        self.player_display.rect.left = 1080
        self.player_display.rect.centery = 70
        self.status.rect.center = self.board.rect.center
        self.countdown.rect.center = (730, 150)

    def set_difficulty(self, difficulty):
        """Adjust game parameters given difficulty.

        Custom difficulty is not handled in this function.
        """
        self.difficulty = difficulty

        if difficulty == "EASY":
            self.n_rows = 10
            self.n_cols = 10
            self.n_mines = 10
        elif difficulty == "NORMAL":
            self.n_rows = 16
            self.n_cols = 16
            self.n_mines = 40

        self.difficulty_hint.set_text("当前难度："+difficulty)

    def reset_game(self):
        """Reset the game."""
        print('reset')
        bg_image = load_random_image()
        tile_size = self.BOARD_SIZE // min(self.n_rows, self.n_cols)
        self.board.reset(n_rows=self.n_rows,
                         n_cols=self.n_cols,
                         n_mines=self.n_mines,
                         bg_image=bg_image,
                         tile_size=tile_size)   # game status is changed here
        self.board_axis.set(self.board)

    def reset_player(self):
        self.player = 'all'
        self.player_input_timer.stop()

    def on_status_change(self, new_status):
        """Handle game status change."""
        if new_status == 'game_over':
            self.status.set_text("GAME OVER!")
            self.gameover_restart_timer.start(self.DELAY_BEFORE_RESTART_MS)
            self.reset_player()
        elif new_status == 'victory':
            self.status.set_text("VICTORY!")
            if self.player != 'all' and self.leaderboard.needs_update(self.difficulty,
                                                                      self.board.time):
                self.leaderboard.update(self.difficulty, self.player, self.board.time)
            self.gameover_restart_timer.start(self.DELAY_BEFORE_RESTART_MS)
            self.reset_player()
        elif new_status == 'before_start':
            self.status.set_text("READY TO GO!")
        else:
            self.status.set_text("")

    def on_difficulty_change(self, difficulty):
        """Handle difficulty change."""
        self.set_difficulty(difficulty)

        self.init_screen()
        self.place_gui()
        self.reset_game()

    def set_game_parameter(self, parameter, max_value, value):
        """Set either n_rows, n_cols, n_mines."""
        if not value:
            value = 1

        value = int(value)
        value = min(max(1, value), max_value)
        setattr(self, parameter, value)
        self.n_mines = min(self.n_mines, self.n_rows * self.n_cols - 1)
        self.init_screen()
        self.place_gui()
        self.reset_game()
        return value

    def draw_all(self):
        """Draw all elements."""
        self.screen.blit(self.screen_image, self.screen_image.get_rect())

        if self.mode == "name_input":
            self.victory_time.draw(self.screen)
            self.leaderboard_announcement.draw(self.screen)
            pygame.display.flip()
            return

        self.board.draw(self.screen)
        self.board_axis.draw(self.screen)

        # self.difficulty_selector.draw(self.screen)
        self.difficulty_hint.draw(self.screen)
        self.leaderboard.draw(self.screen)

        self.timer.draw(self.screen)
        self.current_mines.draw(self.screen)
        self.player_display.draw(self.screen)
        self.status.draw(self.screen)

        self.countdown.draw(self.screen)

        pygame.display.flip()

    def process_events(self):
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.keep_running = False
                break

            if self.mode == "leaderboard":
                if event.type == pygame.MOUSEBUTTONUP:
                    self.mode = "game"
                break
            elif self.mode == "name_input":
                pass
                break

            if event.type == pygame.MOUSEBUTTONUP:
                self.board.on_mouse_up(event.button)

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.board.on_mouse_down(event.button)

    def process_danmu_list(self):
        danmu_list = self.dmj.get_danmu_list()
        for danmu in danmu_list:
            print(danmu)
            if self.player == 'all' or self.player == danmu[0]:
                if danmu[1] == 'gift':
                    print(self.board.game_status)
                    if self.player == 'all':
                        self.player = danmu[0]
                        self.player_input_timer.start(self.PLAYER_INPUT_INTERVAL_MS)
                elif danmu[1] == 'difficulty':
                    if self.board.game_status != "running":
                        self.on_difficulty_change(danmu[2])
                else:
                    if self.player != 'all':
                        self.player_input_timer.start(self.PLAYER_INPUT_INTERVAL_MS)
                    i, j = self.board.n_rows - danmu[2][1] - 1, danmu[2][0]
                    if danmu[1] == 'open':
                        self.board.open_tile(i, j)
                    elif danmu[1] == 'check':
                        self.board.check_tile_if_unchecked(i, j)
                    elif danmu[1] == 'uncheck':
                        self.board.uncheck_tile_if_checked(i, j)

    def start_main_loop(self):
        """Start main game loop."""
        clock = pygame.time.Clock()
        self.keep_running = True
        while self.keep_running:
            clock.tick(30)
            self.timer.set_value(self.board.time)
            self.current_mines.set_value(self.board.n_mines_left)
            player_text = self.player
            if len(player_text) > 8:
                player_text = player_text[:8] + "..."
            self.player_display.set_text(player_text)
            self.process_events()
            self.process_danmu_list()
            self.player_input_timer.check()
            self.gameover_restart_timer.check()

            self.place_gui()
            self.draw_all()

    def save_state(self, state_file_path):
        """Save game state on disk."""
        state = {
            "difficulty": self.difficulty,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "n_mines": self.n_mines,
            "leaderboard": self.leaderboard.data
        }
        with open(state_file_path, "w") as state_file:
            json.dump(state, state_file)


def run(state_file_path):
    pygame.init()
    pygame.display.set_caption('Minesweeper')
    pygame.mouse.set_visible(True)
    game = Game(state_file_path)
    game.start_main_loop()
    game.save_state(state_file_path)
