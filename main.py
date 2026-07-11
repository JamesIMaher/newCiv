import pygame
import sys
import grid 
from Screen.screen import Screen

pygame.init()

SCREEN_WIDTH = pygame.display.Info().current_w / 2
SCREEN_HEIGHT = pygame.display.Info().current_h - 80
GAME_TITLE = "New Civilization"
GRID_SIZE = (70, 50)
FPS = 60

def main():
    #Initialize the pygame display
    game_screen = Screen(SCREEN_WIDTH, SCREEN_HEIGHT, GAME_TITLE)
    game_grid = grid.Grid(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE)
    game_grid.draw_grid_terrain(game_screen)

if __name__ == "__main__":
    main()
