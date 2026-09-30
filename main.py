import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # keep the console quiet

import pygame
from Screen.screen import Screen

pygame.init()

info = pygame.display.Info()
SCREEN_WIDTH = max(1100, min(1600, info.current_w - 80))
SCREEN_HEIGHT = max(700, min(1000, info.current_h - 100))


def main():
    # Imported after pygame.init() so fonts are available.
    from ui.app import App, GAME_TITLE
    from ui.globe import make_icon
    pygame.display.set_icon(make_icon())
    game_screen = Screen(SCREEN_WIDTH, SCREEN_HEIGHT, GAME_TITLE)
    App(game_screen).run()
    pygame.quit()


if __name__ == "__main__":
    main()
