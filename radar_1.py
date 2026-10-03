import pygame
import math 
import random

pygame.init()

WIDTH, HEIGHT = 800, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Radar Scanner")

clock = pygame.time.Clock()

CENTER = (WIDTH // 2, HEIGHT // 2)
RADIUS = 320

GREEN = (0, 255, 70)
DARK_GREEN = (0, 60, 0)
BLACK = (0, 0, 0)

enemies = []

for _ in range(5):
    angle = random.uniform(0, 360)
    dist = random.uniform(70, RADIUS - 20)

    x = CENTER[0] + math.cos(math.radians(angle)) * dist
    y = CENTER[1] + math.sin(math.radians(angle)) * dist

    enemies.append((x, y))

enemy_memory = [0] * len(enemies)
radar_angle = 0
running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)

    
    for r in range(80, RADIUS + 1, 80):
        pygame.draw.circle(screen, DARK_GREEN, CENTER, r, 1)

    
    pygame.draw.line(screen, DARK_GREEN, (CENTER[0], 0), (CENTER[0], HEIGHT))
    pygame.draw.line(screen, DARK_GREEN, (0, CENTER[1]), (WIDTH, CENTER[1]))

    # 3. OPTIMIZED: Create ONE sweep surface per frame instead of 45
    sweep = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for i in range(45):
        a = radar_angle - i * 1.5
        
        # 4. FIXED: Syntax error in max(). Was max(0, 180, -i*4) which always returned 180
        alpha = max(0, 180 - i * 4)

        P1 = CENTER
        # 5. FIXED: Use consistent +math.sin for both P2 and p3 so the polygon doesn't tear
        P2 = (
            CENTER[0] + math.cos(math.radians(a)) * RADIUS,
            CENTER[1] + math.sin(math.radians(a)) * RADIUS,
        )
        p3 = (
            CENTER[0] + math.cos(math.radians(a - 1.5)) * RADIUS,
            CENTER[1] + math.sin(math.radians(a - 1.5)) * RADIUS,
        )

        pygame.draw.polygon(sweep, (0, 255, 70, alpha), [P1, P2, p3])
        
    
    screen.blit(sweep, (0, 0))

    pygame.draw.circle(screen, GREEN, CENTER, RADIUS, 2)
    
    for i, (x, y) in enumerate(enemies):
        enemy_angle = math.degrees(math.atan2(y - CENTER[1], x - CENTER[0]))

        
        diff = (radar_angle - enemy_angle) % 360

        if diff < 2 or diff > 358:
            enemy_memory[i] = 60 # Set to 60 frames (1 full second of visibility)

        if enemy_memory[i] > 0:
            enemy_memory[i] -= 1

            glow = pygame.Surface((40, 40), pygame.SRCALPHA)

            pygame.draw.circle(glow, (0, 255, 70, 70), (20, 20), 14)    
            screen.blit(glow, (x - 20, y - 20))

            if enemy_memory[i] % 10 > 4: 
                pygame.draw.circle(screen, (200, 255, 200), (int(x), int(y)), 6)


    radar_angle = (radar_angle + 1) % 360

    pygame.display.flip()
    clock.tick(60)

pygame.quit()