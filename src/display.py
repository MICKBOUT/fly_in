import pygame

pygame.init()

pygame.display.set_caption("FLY IN !!!")
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF, vsync=1)
clock = pygame.time.Clock()

screen_size = screen.get_size()
screen_width, screen_height = screen_size

# pixels per second (was 960/60 per frame, now 960 per second)
speed = 960

line_x_axe = pygame.Rect(-5000, -5, 10000, 10)
line_y_axe = pygame.Rect(-5, -5000, 10, 10000)

blue_rect = pygame.Rect((0, 0), (200, 80))
red_rect = pygame.Rect((500, 400), (200, 80))

running = True
offset = [-(screen_width / 2), -(screen_height / 2)]

def draw_rect_offset(rect, color, offset: tuple[int, int]):
    pygame.draw.rect(screen, color, ((rect.left - offset[0], rect.top - offset[1]), rect.size))

while running:
    dt = clock.tick() / 1000  # seconds since last frame, uncapped

    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    key_dict = pygame.key.get_pressed()
    if key_dict[pygame.K_d]:
        offset[0] += speed * dt
    if key_dict[pygame.K_a]:
        offset[0] -= speed * dt
    if key_dict[pygame.K_s]:
        offset[1] += speed * dt
    if key_dict[pygame.K_w]:
        offset[1] -= speed * dt

    draw_rect_offset(line_x_axe, "white", offset)
    draw_rect_offset(line_y_axe, "white", offset)
    draw_rect_offset(blue_rect, "blue", offset)
    draw_rect_offset(red_rect, "red", offset)
    pygame.display.flip()