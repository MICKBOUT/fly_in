import math
from typing import Callable, Iterable, TypedDict

import pygame

from models import NodeData


class ConnectionDisplayData(TypedDict):
    left: str
    right: str


class Drone(pygame.sprite.Sprite):
    DRONE_PNG_PATH = "assets/drone.png"
    IMG_SIZE = 512
    TARGET_SIZE = 32
    BASE_RESCALE = TARGET_SIZE / IMG_SIZE
    DRONE_SPEED = 360  # en pixel par seconde

    def __init__(self, start_pos: str, path: list[tuple[str, int]],
                 drone_png: pygame.Surface,
                 waypoint_to_pos: Callable[[str], tuple[int, int]]) -> None:
        super().__init__()

        self.waypoint_to_pos = waypoint_to_pos
        start_x, start_y = self.waypoint_to_pos(start_pos)
        self.pos: tuple[float, float] = (float(start_x), float(start_y))
        self.target_pos: tuple[float, float] = self.pos

        self.path = {turn: waypoint for waypoint, turn in path}
        self.path[0] = start_pos
        for i in path:
            print(i)

        self.loaded_img = drone_png
        self.image = pygame.transform.scale_by(
            self.loaded_img, self.BASE_RESCALE)
        self.rect = self.image.get_rect(center=(0, 0))

    def update(self, zoom: float, turn: int, dt: float) -> None:
        if turn in self.path:
            target_str = self.path[turn]
            target_x, target_y = self.waypoint_to_pos(target_str)
            self.target_pos = (float(target_x), float(target_y))
        elif turn - 1 in self.path and turn + 1 in self.path:
            target_a_x, target_a_y = self.waypoint_to_pos(self.path[turn - 1])
            target_b_x, target_b_y = self.waypoint_to_pos(self.path[turn + 1])
            self.target_pos = (
                (target_a_x + target_b_x) / 2, (target_a_y + target_b_y) / 2
            )
        movement = dt * self.DRONE_SPEED

        if self.pos != self.target_pos:
            x, y = self.pos
            tx, ty = self.target_pos
            dx = tx - x
            dy = ty - y
            distance = math.hypot(dx, dy)

            if distance <= movement:
                self.pos = self.target_pos
            elif distance > 0:
                ratio = movement / distance
                self.pos = (x + (dx * ratio), y + (dy * ratio))

        self.image = pygame.transform.scale_by(
            self.loaded_img, self.BASE_RESCALE * zoom
        )
        self.rect = self.image.get_rect(center=self.rect.center)


class Circle(NodeData):
    RADIUS = 25

    def __init__(
            self, name: str, x: int, y: int, zone: str,
            color: str | None, max_drones: int) -> None:
        super().__init__(name, x * 100, y * 100, zone, color, max_drones)

        self.true_x, self.true_y = x, y
        self.display_color: str = "white"
        # if the color is not valid, the the color to white
        if color is None:
            return
        try:
            # if color not in {"rainbow"}: skip next line (allow custom color)
            pygame.Color(color)
            self.display_color = color
        except ValueError:
            pass


class Display:
    ZOOM_STEP = 1.25
    MIN_ZOOM = 0.5
    MAX_ZOOM = 20
    SPEED = 960
    BACKGOUND_COLOR = (91, 123, 122)
    TEXT_ATH_COLOR = (0, 0, 0)
    PERIMETER_COLOR = (161, 124, 107)
    LINK_COLOR = (206, 181, 167)

    hubs: dict[str, Circle] = {}

    def __init__(self, hub_dict: dict[str, NodeData],
                 connections: Iterable[ConnectionDisplayData],
                 paths: list[list[tuple[str, int]]],
                 start_pos: str,
                 nb_turn: int
                 ) -> None:
        pygame.init()
        pygame.display.set_caption("FLY IN !!!")

        self.font = pygame.font.SysFont("Arial", 48)
        self.screen = pygame.display.set_mode((0, 0), 0, vsync=1)
        self.clock = pygame.time.Clock()
        self.zoom = 1.0
        self.turn = 0
        self.nb_turn = nb_turn

        drone_png = pygame.image.load(Drone.DRONE_PNG_PATH).convert_alpha()

        self.screen_size = self.screen.get_size()
        self.screen_width, self.screen_height = self.screen_size

        self.connections = {
            (lambda x, y: (x, y) if x < y else (y, x))
            (connection["left"], connection["right"])
            for connection in connections
        }

        self.init_hub(hub_dict)
        sum_circle_x = sum(circle.x for circle in self.hubs.values())
        sum_circle_y = sum(circle.y for circle in self.hubs.values())
        self.offset = [
            -(self.screen_width / 2) + (sum_circle_x / len(self.hubs)),
            -(self.screen_height / 2) + (sum_circle_y / len(self.hubs))
        ]  # * 100 bc the grid is scale by 100px for a better space b/w hub

        self.drones = pygame.sprite.Group(
            *(Drone(start_pos, path, drone_png, self.waypoint_to_pos)
              for path in paths))

    @classmethod
    def init_hub(cls, hub_dict: dict[str, NodeData]) -> None:
        cls.hubs = {}
        for name, value in hub_dict.items():
            cls.hubs[name] = Circle(
                value.name,
                value.x,
                value.y,
                value.zone,
                value.color,
                value.max_drones,
            )

    def draw_circle_offset(self, circle: Circle, factor: float = 1.0) -> None:
        # colored part of the circle
        pygame.draw.circle(
            self.screen, circle.display_color,
            self.world_to_screen(circle.x, circle.y),
            circle.RADIUS * self.zoom * factor
        )
        # white part of the circle
        pygame.draw.circle(
            self.screen, (self.PERIMETER_COLOR),
            self.world_to_screen(circle.x, circle.y),
            circle.RADIUS * self.zoom * factor,
            int(5 * self.zoom),
        )

    def draw_line_offset(self, start: Circle, end: Circle) -> None:
        pygame.draw.line(
            self.screen,
            self.LINK_COLOR,
            self.world_to_screen(start.x, start.y),
            self.world_to_screen(end.x, end.y),
            int(5 * self.zoom),
        )

    def move_drone_target(self, drone: Drone) -> None:
        drone.rect.center = (self.world_to_screen(*drone.pos))

    def waypoint_to_pos(self, waypoint: str) -> tuple[int, int]:
        circle = self.hubs[waypoint]
        return circle.x, circle.y

    def screen_to_world(self, pos: tuple[int, int]) -> tuple[float, float]:
        x, y = pos
        return (
            self.offset[0] + (x / self.zoom),
            self.offset[1] + (y / self.zoom)
        )

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return (
            int((x - self.offset[0]) * self.zoom),
            int((y - self.offset[1]) * self.zoom)
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
            self.font.render(
                text, True, self.TEXT_ATH_COLOR), self.write_box).bottomleft

    def display_hub_info(self, circle: Circle) -> None:
        self.write_box = self.render_write(f"Name: {circle.name}")
        self.write_box = self.render_write(
            f"Position (x, y): ({circle.true_x}, {circle.true_y})")
        self.write_box = self.render_write(f"Zone: {circle.zone}")
        self.write_box = self.render_write(f"Color: {circle.color}")
        self.write_box = self.render_write(
            f"Max drones: {circle.max_drones}")

    def main(self) -> None:
        running = True
        dragging = False
        mx, my = pygame.mouse.get_pos()
        while running:
            mouse_over_circle = None
            self.write_box = (0, 0)
            ticking = self.clock.tick()
            fps_str = str(int(self.clock.get_fps()))
            dt = ticking / 1000  # seconds since last frame, uncapped

            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        running = False
                    case pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        if (
                            event.key == pygame.K_SPACE or
                            event.key == pygame.K_RIGHT
                        ):
                            if self.turn < self.nb_turn:
                                self.turn += 1
                        if event.key == pygame.K_LEFT:
                            if self.turn > 0:
                                self.turn -= 1

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

            self.drones.update(self.zoom, self.turn, dt)
            for drone in self.drones:
                self.move_drone_target(drone)

            # display the background
            self.screen.fill(self.BACKGOUND_COLOR)

            # draw line
            for name_1, name_2 in self.connections:
                self.draw_line_offset(self.hubs[name_1], self.hubs[name_2])

            # draw hubs
            for ell in self.hubs.values():
                self.draw_circle_offset(ell)

            # draw big hub
            for circle in self.hubs.values():
                if (
                    ((circle.x - self.offset[0])*self.zoom - mx)**2 +
                    ((circle.y - self.offset[1])*self.zoom - my)**2 <
                    (circle.RADIUS * self.zoom)**2
                ):
                    mouse_over_circle = circle
                    self.draw_circle_offset(circle, factor=1.5)
                    break

            # draw drone
            self.drones.draw(self.screen)

            # display fps count
            self.write_box = self.screen.blit(self.font.render(
              fps_str, True, self.TEXT_ATH_COLOR), self.write_box).bottomleft
            # display turn
            self.write_box = self.screen.blit(self.font.render(
                    f"Trun: {self.turn}", True, self.TEXT_ATH_COLOR),
                self.write_box).bottomleft

            # display the hub info at the top left of the screen
            if mouse_over_circle:
                self.display_hub_info(circle)

            pygame.display.flip()
        pygame.quit()

# Coordinate
