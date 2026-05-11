import random
from typing import Mapping, TypedDict

import pygame


class HubDisplayData(TypedDict):
    x: int
    y: int
    color: str | None


class Circle:
    def __init__(
            self, x: int, y: int, radius: int, color: str = "white") -> None:
        self.x = x
        self.y = y
        self.radius = radius
        self.color = "red"
        try:
            pygame.Color(color)
            self.color = color
        except ValueError:
            pass


class Display:
    ZOOM_STEP = 1.25
    MIN_ZOOM = 0.5
    MAX_ZOOM = 20
    SPEED = 960

    def __init__(
            self, hub_dict: Mapping[str, HubDisplayData]) -> None:
        pygame.init()
        pygame.display.set_caption("FLY IN !!!")
        self.font = pygame.font.SysFont("Arial", 48)
        self.screen = pygame.display.set_mode((0, 0), 0, vsync=1)
        self.clock = pygame.time.Clock()

        self.screen_size = self.screen.get_size()
        self.screen_width, self.screen_height = self.screen_size

        # pixels per second (was 960/60 per frame, now 960 per second)
        self.zoom = 1.0

        self.rnd_sample_size = 250
        self.rect_lst = self.gen_rect(self.rnd_sample_size)

        self.hubs: list[Circle] = []

        sum_circle_x = 0
        sum_circle_y = 0
        for value in hub_dict.values():
            color = value["color"] or "white"
            self.hubs.append(Circle(
                value["x"] * 100,
                value["y"] * 100,
                25,
                color
            ))
            sum_circle_x += value["x"]
            sum_circle_y += value["y"]
        self.offset = [
            -(self.screen_width / 2) + (sum_circle_x * 100 / len(self.hubs)),
            -(self.screen_height / 2) + (sum_circle_y * 100 / len(self.hubs))
        ]

    @staticmethod
    def gen_rect(nb: int) -> list[pygame.Rect]:
        return [pygame.Rect(
            (random.randint(-5000, 5000), random.randint(-5000, 5000)),
            (random.randint(10, 500), random.randint(10, 500)))
            for _ in range(nb)
        ]

    # def draw_rect_offset(self, rect: pygame.Rect, color: str) -> None:
    #     pygame.draw.rect(self.screen, color, ((
    #             (rect.left - self.offset[0]) * self.zoom,
    #             (rect.top - self.offset[1]) * self.zoom),
    #         (rect.w * self.zoom, rect.h * self.zoom)),
    #     )

    def draw_circle_offset(self, circle: Circle) -> None:
        pygame.draw.circle(
            self.screen, circle.color,
            (
                (circle.x - self.offset[0]) * self.zoom,
                (circle.y - self.offset[1]) * self.zoom
            ),
            circle.radius * self.zoom
        )
        pygame.draw.circle(
            self.screen, "white",
            (
                (circle.x - self.offset[0]) * self.zoom,
                (circle.y - self.offset[1]) * self.zoom
            ),
            circle.radius * self.zoom,
            int(5 * self.zoom),
        )

    def screen_to_world(self, pos: tuple[int, int]) -> tuple[float, float]:
        x, y = pos
        return (
            self.offset[0] + (x / self.zoom),
            self.offset[1] + (y / self.zoom)
        )

    def zoom_at(self, screen_pos: tuple[int, int], factor: float) -> None:
        world_x, world_y = self.screen_to_world(screen_pos)
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom:
            return

        self.zoom = new_zoom
        self.offset[0] = world_x - (screen_pos[0] / self.zoom)
        self.offset[1] = world_y - (screen_pos[1] / self.zoom)

    def main(self) -> None:
        running = True
        dragging = False
        while running:
            ticking = self.clock.tick()
            fps_str = str(int(self.clock.get_fps()))
            dt = ticking / 1000  # seconds since last frame, uncapped

            self.screen.fill((64, 64, 64))

            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        running = False
                    case pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        if event.key == pygame.K_r:
                            self.rect_lst = self.gen_rect(self.rnd_sample_size)

                    case pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            dragging = True
                            last_mouse_pos = event.pos

                    case pygame.MOUSEBUTTONUP:
                        if event.button == 1:
                            dragging = False

                    case pygame.MOUSEMOTION:
                        if dragging:
                            mx, my = event.pos
                            lx, ly = last_mouse_pos

                            self.offset[0] -= (mx - lx) / self.zoom
                            self.offset[1] -= (my - ly) / self.zoom

                            last_mouse_pos = event.pos

                    case pygame.MOUSEWHEEL:
                        mx, my = pygame.mouse.get_pos()
                        if event.y > 0:
                            self.zoom_at((mx, my), self.ZOOM_STEP)

                        elif event.y < 0:
                            self.zoom_at((mx, my), 1 / self.ZOOM_STEP)

            key_dict = pygame.key.get_pressed()
            if key_dict[pygame.K_d]:
                self.offset[0] += self.SPEED * dt
            if key_dict[pygame.K_a]:
                self.offset[0] -= self.SPEED * dt
            if key_dict[pygame.K_s]:
                self.offset[1] += self.SPEED * dt
            if key_dict[pygame.K_w]:
                self.offset[1] -= self.SPEED * dt

            for ell in self.hubs:
                self.draw_circle_offset(ell)

            surface = self.font.render(fps_str, True, "maroon")
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()

        pygame.quit()
