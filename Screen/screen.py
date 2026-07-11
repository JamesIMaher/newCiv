import pygame

################################################################
# Class Screen: Class to initalize and hold the pygame display object
#
#################################################################

class Screen:
    def __init__ (self, screen_width, screen_height, game_title):
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("New Civilization")
        self.clock = pygame.time.Clock()

