import pygame
import math

pygame.init()

WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Four Rings Animation")

clock = pygame.time.Clock()

BLACK = (10, 10, 10)
SILVER = (220, 220, 220)
GLOW = (120, 120, 140)

rings = [
    (340, 250),
    (430, 250),
    (520, 250),
    (610, 250)
]

radius = 70
line_width = 6
progress = [0, 0, 0, 0]
current_ring = 0

title_font = pygame.font.SysFont("Arial", 24)
logo_font = pygame.font.SysFont("Arial", 54, bold=True)

def draw_arc(surface, color, centre,radius,angle,width):
    points = []

    for a in range(angle + 1):
        r = math.radians(a)
        x = centre[0] + math.cos(r) * radius
        y = centre[1] + math.sin(r) * radius
        points.append((x, y))


    if len(points) > 1:
        pygame.draw.lines(surface, color, False, points, width)

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)        
    title = title_font.render("FOUR RINGS", True, (220, 220, 220))
    screen.blit(title, (20, 20))

    for i in range(4):

        if i < current_ring:
            draw_arc(screen, GLOW, rings[i], radius + 3, 360, 10)
            draw_arc(screen, SILVER,rings[i], radius, 360, line_width)

        elif i == current_ring:

            draw_arc(screen, GLOW, rings[i], radius + 3, progress[i], 10)
            draw_arc(screen, SILVER, rings[i], radius, progress[i], line_width)

            progress[i] += 4

            
            if  progress[i] >= 360:
                progress[i] = 360
                current_ring += 1

    if current_ring >= 4:
        text = logo_font.render("AUDI", True, SILVER)
        rect = text.get_rect(center=(475, 400))
        screen.blit(text, rect)


    pygame.display.flip()
    clock.tick(60)

pygame.quit()
