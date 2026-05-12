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
            self, hub_dict: Mapping[str, HubDisplayData], connections) -> None:
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

        self.hubs: dict[str, Circle] = {}

        self.connections = {
            (lambda x, y: (x, y) if x < y else (y, x))
            (connection["left"], connection["right"])
            for connection in connections
        }

        sum_circle_x = 0
        sum_circle_y = 0
        for value in hub_dict.values():
            color = value["color"] or "white"
            self.hubs[value["name"]] = (Circle(
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

    def draw_circle_offset(self, circle: Circle) -> None:
        # colored part of the circle
        pygame.draw.circle(
            self.screen, circle.color,
            (
                (circle.x - self.offset[0]) * self.zoom,
                (circle.y - self.offset[1]) * self.zoom
            ),
            circle.radius * self.zoom
        )
        # white part of the circle
        pygame.draw.circle(
            self.screen, "white",
            (
                (circle.x - self.offset[0]) * self.zoom,
                (circle.y - self.offset[1]) * self.zoom
            ),
            circle.radius * self.zoom,
            int(5 * self.zoom),
        )

    def draw_line_offset(self, start: Circle, end: Circle) -> None:
        pygame.draw.line(
            self.screen,
            "white", (
                (start.x - self.offset[0]) * self.zoom,
                (start.y - self.offset[1]) * self.zoom), (
                (end.x - self.offset[0]) * self.zoom,
                (end.y - self.offset[1]) * self.zoom),
            5,
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

            # draw line
            for name_1, name_2 in self.connections:
                self.draw_line_offset(self.hubs[name_1], self.hubs[name_2])

            # draw hubs
            for ell in self.hubs.values():
                self.draw_circle_offset(ell)

            surface = self.font.render(fps_str, True, "maroon")
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()

        pygame.quit()
