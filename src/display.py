from typing import Iterable, TypedDict

import pygame

from models import NodeData


class ConnectionDisplayData(TypedDict):
    left: str
    right: str


class Circle(NodeData):
    radius = 25

    def __init__(
            self, name: str, x: int, y: int, zone: str,
            color: str | None, max_drones: float) -> None:
        super().__init__(name, x * 100, y * 100, zone, color, max_drones)

        self.display_color: str = "white"
        # if the color is not valid, the the color to white
        if color is None:
            return
        try:
            pygame.Color(color)
            self.display_color = color
        except (ValueError, TypeError):
            self.display_color = "white"


class Display:
    ZOOM_STEP = 1.25
    MIN_ZOOM = 0.5
    MAX_ZOOM = 20
    SPEED = 960

    def __init__(self, hub_dict: dict[str, NodeData],
                 connections: Iterable[ConnectionDisplayData]) -> None:
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
        for name, value in hub_dict.items():
            self.hubs[name] = Circle(
                value.name,
                value.x,
                value.y,
                value.zone,
                value.color,
                float(value.max_drones),
            )
            sum_circle_x += value.x
            sum_circle_y += value.y
        self.offset = [
            -(self.screen_width / 2) + (sum_circle_x * 100 / len(self.hubs)),
            -(self.screen_height / 2) + (sum_circle_y * 100 / len(self.hubs))
        ]

    def draw_circle_offset(self, circle: Circle) -> None:
        # colored part of the circle
        pygame.draw.circle(
            self.screen, circle.display_color,
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

    def render_write(self, text: str) -> tuple[int, int]:
        """rebder + write text on screen, return bottomleft of writed text
        """
        return self.screen.blit(
            self.font.render(text, True, "Black"), self.write_box).bottomleft

    def display_hub_info(self, circle: Circle) -> None:
        self.write_box = self.render_write(f"Name: {circle.name}")
        self.write_box = self.render_write(
            f"Position (x, y): ({circle.x // 100}, {circle.x // 100})")
        self.write_box = self.render_write(f"Zone: {circle.zone}")
        self.write_box = self.render_write(f"Color: {circle.color}")
        self.write_box = self.render_write(f"Max drones: {circle.max_drones}")

    def main(self) -> None:
        running = True
        dragging = False
        mx, my = pygame.mouse.get_pos()
        while running:
            self.write_box = (0, 0)
            ticking = self.clock.tick()
            fps_str = str(int(self.clock.get_fps()))
            dt = ticking / 1000  # seconds since last frame, uncapped
            self.screen.fill((64, 64, 96))

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
                        mx, my = event.pos
                        if dragging:
                            lx, ly = last_mouse_pos

                            self.offset[0] -= (mx - lx) / self.zoom
                            self.offset[1] -= (my - ly) / self.zoom

                            last_mouse_pos = event.pos

                    case pygame.MOUSEWHEEL:
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

            # display the fps count
            surface = self.font.render(fps_str, True, "maroon")
            self.write_box = self.screen.blit(
                surface, self.write_box).bottomleft

            # display the hub info at the top left of the screen
            for hub in self.hubs.values():
                if (
                    ((hub.x - self.offset[0])*self.zoom - mx)**2 +
                    ((hub.y - self.offset[1])*self.zoom - my)**2 <
                    (hub.radius * self.zoom)**2
                ):
                    self.display_hub_info(hub)

            # draw line
            for name_1, name_2 in self.connections:
                self.draw_line_offset(self.hubs[name_1], self.hubs[name_2])

            # draw hubs
            for ell in self.hubs.values():
                self.draw_circle_offset(ell)

            pygame.display.flip()
        pygame.quit()

# Coordinate
