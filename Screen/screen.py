import pygame

################################################################
# Class Screen: Class to initalize and hold the pygame display object
#
#################################################################

class Screen:
    def __init__ (self, screen_width, screen_height, game_title):
        self.screen = pygame.display.set_mode((int(screen_width), int(screen_height)), pygame.RESIZABLE)
        pygame.display.set_caption(game_title)
        self.clock = pygame.time.Clock()
