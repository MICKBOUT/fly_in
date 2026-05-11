import pygame

pygame.init()

pygame.display.set_caption("FLY IN !!!")
font = pygame.font.SysFont("Arial", 48)
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF, vsync=1)
clock = pygame.time.Clock()

screen_size = screen.get_size()
screen_width, screen_height = screen_size
offset = [-(screen_width / 2), -(screen_height / 2)]

# pixels per second (was 960/60 per frame, now 960 per second)
speed = 960

def draw_rect_offset(rect, color, offset: tuple[int, int]):
    pygame.draw.rect(screen, color, ((rect.left - offset[0], rect.top - offset[1]), rect.size))

line_x_axe = pygame.Rect(-500000, -5, 1000000, 10)
line_y_axe = pygame.Rect(-5, -500000, 10, 1000000)



import random
rect_lst = [pygame.Rect((random.randint(-5000, 5000), random.randint(-5000, 5000)), (random.randint(10, 500), random.randint(10, 500))) for _ in range(250)]
blue_rect = pygame.Rect((0, 0), (200, 80))
red_rect = pygame.Rect((500, 400), (200, 80))

running = True
while running:
    ticking = clock.tick()
    fps_str = str(int(clock.get_fps()))
    dt = ticking / 1000  # seconds since last frame, uncapped

    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r:
                rect_lst = [pygame.Rect((random.randint(-5000, 5000), random.randint(-5000, 5000)), (random.randint(10, 500), random.randint(10, 500))) for _ in range(250)]

    key_dict = pygame.key.get_pressed()
    if key_dict[pygame.K_d]:
        offset[0] += speed * dt
    if key_dict[pygame.K_a]:
        offset[0] -= speed * dt
    if key_dict[pygame.K_s]:
        offset[1] += speed * dt
    if key_dict[pygame.K_w]:
        offset[1] -= speed * dt


    for ell in rect_lst:
        draw_rect_offset(ell, "Blue", offset)
    draw_rect_offset(line_x_axe, "white", offset)
    draw_rect_offset(line_y_axe, "white", offset)
    # draw_rect_offset(blue_rect, "blue", offset)
    # draw_rect_offset(red_rect, "red", offset)

    surface = font.render(fps_str, True, "maroon")
    screen.blit(surface, (0, 0))
    pygame.display.flip()

pygame.quit()