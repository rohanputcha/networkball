import pygame
from client import Client
import threading
import time

pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
FPS = 60
BALL_RADIUS = 15
SPEED = (SCREEN_WIDTH // 100)

class Ball:
    def __init__(self, x=SCREEN_WIDTH//2, y=SCREEN_HEIGHT//2, color=(255, 0, 0)):
        self.x = x
        self.y = y
        self.color = color
        self.dx = 0
        self.dy = 0

    def draw(self):
        pygame.draw.circle(display, self.color, (self.x, self.y), BALL_RADIUS)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        if self.x < BALL_RADIUS:
            self.x = BALL_RADIUS
        if self.x > SCREEN_WIDTH - BALL_RADIUS:
            self.x = SCREEN_WIDTH - BALL_RADIUS
        if self.y < BALL_RADIUS:
            self.y = BALL_RADIUS
        if self.y > SCREEN_HEIGHT - BALL_RADIUS:
            self.y = SCREEN_HEIGHT - BALL_RADIUS


def game(manager_host='localhost', manager_port=5000, host='localhost', port=5001):
    ball = Ball()
    keys_pressed = {}
    client = Client(host, port, manager_host, manager_port, (ball.x, ball.y))
    client_thread = threading.Thread(target=client.run)
    client_thread.start()
    balls = {} # host, port: ball
    player_time_updated = {} # host, port: time
    signals = {"shutdown": False}
    player_timeout_check = threading.Thread(target=player_timeout, args=(player_time_updated, balls, signals))
    player_timeout_check.start()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                signals["shutdown"] = True
                pygame.quit()
                client.shutdown()
                client_thread.join()
                player_timeout_check.join()
                return
            if event.type == pygame.KEYDOWN:
                keys_pressed[event.key] = True
            if event.type == pygame.KEYUP:
                keys_pressed[event.key] = False
        player_locations = client.get_player_locations()
        for player in player_locations:
            if player == (host, port):
                continue
            if player not in balls:
                balls[player] = Ball(player_locations[player][0], player_locations[player][1], (0, 0, 255))
                player_time_updated[player] = time.time()
            else:
                balls[player].x = player_locations[player][0]
                balls[player].y = player_locations[player][1]
                player_time_updated[player] = time.time()
        
        # Update ball movement based on pressed keys
        ball.dx = (keys_pressed.get(pygame.K_d, 0) - keys_pressed.get(pygame.K_a, 0)) * SPEED
        ball.dy = (keys_pressed.get(pygame.K_s, 0) - keys_pressed.get(pygame.K_w, 0)) * SPEED
        
        display.fill((190, 255, 255))
        ball.update()
        ball.draw()
        for player in balls:
            balls[player].draw()
        client.set_location((ball.x, ball.y))
        pygame.display.update()
        clock.tick(FPS)

def player_timeout(player_time_updated, balls, signals):
    while not signals["shutdown"]:
        for player in player_time_updated.copy():
            if time.time() - player_time_updated[player] > 5:
                del player_time_updated[player]
                del balls[player]
        time.sleep(1)