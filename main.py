import pygame
import sys

pygame.init()

SCREEN_WIDTH = pygame.display.Info().current_w / 2
SCREEN_HEIGHT = pygame.display.Info().current_h - 80
FPS = 60
BLACK = (0, 0, 0)
BALL_SPEED = [2, 2]

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("newCiv")
clock = pygame.time.Clock()

def main():
    ball = pygame.image.load("intro_ball.gif")
    ballrect = ball.get_rect()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        ballrect = ballrect.move(BALL_SPEED)
        if ballrect.left < 0 or ballrect.right > SCREEN_WIDTH:
            BALL_SPEED[0] = -BALL_SPEED[0]
        if ballrect.top < 0 or ballrect.bottom > SCREEN_HEIGHT:
            BALL_SPEED[1] = -BALL_SPEED[1]

        screen.fill(BLACK)
        screen.blit(ball, ballrect)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
