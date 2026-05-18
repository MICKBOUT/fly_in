"""Pygame rendering and animation for the Fly-In simulation."""

import math
from typing import Callable, Iterable, TypedDict

import pygame

from models import NodeData


class ConnectionDisplayData(TypedDict):
    """Minimal connection data required by the display."""

    left: str
    right: str
    max_link_capacity: int


class Drone(pygame.sprite.Sprite):
    """Sprite used to animate one routed drone."""

    DRONE_PNG_PATH = "assets/drone.png"
    IMG_SIZE = 512
    TARGET_SIZE = 32
    BASE_RESCALE = TARGET_SIZE / IMG_SIZE
    DRONE_SPEED = 720  # en pixel par seconde

    def __init__(self, start_pos: str, path: list[tuple[str, int]],
                 drone_png: pygame.Surface,
                 waypoint_to_pos: Callable[[str], tuple[int, int]]) -> None:
        """Create one drone sprite from a routed path."""
        super().__init__()

        self.waypoint_to_pos = waypoint_to_pos
        start_x, start_y = self.waypoint_to_pos(start_pos)
        self.pos: tuple[float, float] = (float(start_x), float(start_y))
        self.target_pos: tuple[float, float] = self.pos

        self.path = {turn: waypoint for waypoint, turn in path}
        self.path[0] = start_pos

        self.loaded_img = drone_png
        self.image = pygame.transform.scale_by(
            self.loaded_img, self.BASE_RESCALE)
        self.rect = self.image.get_rect(center=(0, 0))

    def update(self, zoom: float, turn: int, dt: float) -> None:
        """Advance the drone toward its target for the current turn."""
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

    def is_at_target(self) -> bool:
        """Return whether the drone reached its current target."""
        return self.pos == self.target_pos


class Circle(NodeData):
    """Display-specific hub data with precomputed render settings."""

    RADIUS = 25

    def __init__(
            self, name: str, x: int, y: int, zone: str,
            color: str | None, max_drones: int) -> None:
        """Build a drawable hub from graph node data."""
        super().__init__(name, x * 100, y * 100, zone, color, max_drones)

        self.true_x, self.true_y = x, y
        self.is_rainbow = color == "rainbow"
        self.display_color: str = "white"
        # If the color is invalid, fall back to white.
        if color is None or self.is_rainbow:
            return
        try:
            pygame.Color(color)
            self.display_color = color
        except ValueError:
            pass


class Display:
    """Render the map, hubs, and drone animation in Pygame."""

    ZOOM_STEP = 1.25
    MIN_ZOOM = 0.5
    MAX_ZOOM = 20
    SPEED = 960
    BACKGOUND_COLOR = (91, 123, 122)
    TEXT_ATH_COLOR = (0, 0, 0)
    PERIMETER_COLOR = (161, 124, 107)
    LINK_COLOR = (206, 181, 167)

    def __init__(self, hub_dict: dict[str, NodeData],
                 connections: Iterable[ConnectionDisplayData],
                 paths: list[list[tuple[str, int]]],
                 start_pos: str,
                 nb_turn: int
                 ) -> None:
        """Initialize the display and build all render objects."""
        pygame.init()
        pygame.display.set_caption("FLY IN !!!")

        self.font = pygame.font.SysFont("Arial", 48)
        self.screen = pygame.display.set_mode((0, 0), 0, vsync=1)
        self.clock = pygame.time.Clock()
        self.zoom = 1.0
        self.turn = 0
        self.requested_turn = 0
        self.nb_turn = nb_turn

        drone_png = pygame.image.load(Drone.DRONE_PNG_PATH).convert_alpha()

        self.screen_size = self.screen.get_size()
        self.screen_width, self.screen_height = self.screen_size

        self.connections = {
            (lambda x, y, z: (x, y, z) if x < y else (y, x, z))
            (connection["left"], connection["right"],
             connection['max_link_capacity'])
            for connection in connections
        }

        self.hubs = self.build_hubs(hub_dict)
        sum_circle_x = sum(circle.x for circle in self.hubs.values())
        sum_circle_y = sum(circle.y for circle in self.hubs.values())
        self.offset = [
            -(self.screen_width / 2) + (sum_circle_x / len(self.hubs)),
            -(self.screen_height / 2) + (sum_circle_y / len(self.hubs))
        ]  # * 100 bc the grid is scale by 100px for a better space b/w hub

        self.drones = pygame.sprite.Group(
            *(Drone(start_pos, path, drone_png, self.waypoint_to_pos)
              for path in paths))

    def build_hubs(self, hub_dict: dict[str, NodeData]) -> dict[str, Circle]:
        """Convert graph nodes into display circles."""
        hubs: dict[str, Circle] = {}
        for name, value in hub_dict.items():
            hubs[name] = Circle(
                value.name,
                value.x,
                value.y,
                value.zone,
                value.color,
                value.max_drones,
            )
        return hubs

    def draw_circle_offset(self, circle: Circle, factor: float = 1.0) -> None:
        """Draw one hub using the current camera transform."""
        # colored part of the circle
        pygame.draw.circle(
            self.screen, self.circle_color(circle),
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

    def draw_line_offset(self, start: Circle, end: Circle, size: int) -> None:
        """Draw one connection using the current camera transform."""
        pygame.draw.line(
            self.screen,
            self.LINK_COLOR,
            self.world_to_screen(start.x, start.y),
            self.world_to_screen(end.x, end.y),
            int(2 * self.zoom * size),
        )

    def position_drones(self) -> None:
        """Place drone sprites on screen after their world update."""
        drones_by_pos: dict[tuple[float, float], list[Drone]] = {}
        for drone in self.drones:
            pos_key = (round(drone.pos[0], 3), round(drone.pos[1], 3))
            drones_by_pos.setdefault(pos_key, []).append(drone)

        for pos_key, drones in drones_by_pos.items():
            center_x, center_y = self.world_to_screen(*pos_key)
            if len(drones) == 1:
                drones[0].rect.center = (center_x, center_y)
                continue

            offset_radius = max(12, int(18 * self.zoom))
            for index, drone in enumerate(drones):
                angle = (2 * math.pi * index) / len(drones)
                drone.rect.center = (
                    center_x + int(math.cos(angle) * offset_radius),
                    center_y + int(math.sin(angle) * offset_radius),
                )

    def circle_color(self, circle: Circle) -> str | pygame.Color:
        """Return the current render color of a hub."""
        if not circle.is_rainbow:
            return circle.display_color

        rainbow_color = pygame.Color(0)
        hue = (
            (pygame.time.get_ticks() // 10) +
            int(circle.true_x * 40) +
            int(circle.true_y * 40)
        ) % 360
        rainbow_color.hsva = (hue, 90, 100, 100)
        return rainbow_color

    def waypoint_to_pos(self, waypoint: str) -> tuple[int, int]:
        """Resolve one hub name to its world-space position."""
        circle = self.hubs[waypoint]
        return circle.x, circle.y

    def screen_to_world(self, pos: tuple[int, int]) -> tuple[float, float]:
        """Convert screen coordinates into world coordinates."""
        x, y = pos
        return (
            self.offset[0] + (x / self.zoom),
            self.offset[1] + (y / self.zoom)
        )

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates into screen coordinates."""
        return (
            int((x - self.offset[0]) * self.zoom),
            int((y - self.offset[1]) * self.zoom)
        )

    def zoom_at(self, screen_pos: tuple[int, int], factor: float) -> None:
        """Zoom while keeping one screen position anchored."""
        world_x, world_y = self.screen_to_world(screen_pos)
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom:
            return

        self.zoom = new_zoom
        self.offset[0] = world_x - (screen_pos[0] / self.zoom)
        self.offset[1] = world_y - (screen_pos[1] / self.zoom)

    def render_write(self, text: str) -> tuple[int, int]:
        """Render HUD text and return the next write position."""
        return self.screen.blit(
            self.font.render(
                text, True, self.TEXT_ATH_COLOR), self.write_box).bottomleft

    def display_hub_info(self, circle: Circle) -> None:
        """Render the hovered hub details in the HUD."""
        self.write_box = self.render_write(f"Name: {circle.name}")
        self.write_box = self.render_write(
            f"Position (x, y): ({circle.true_x}, {circle.true_y})")
        self.write_box = self.render_write(f"Zone: {circle.zone}")
        self.write_box = self.render_write(f"Color: {circle.color}")
        self.write_box = self.render_write(
            f"Max drones: {circle.max_drones}")

    def main(self) -> None:
        """Run the main render and input loop."""
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
                            if self.requested_turn < self.nb_turn:
                                self.requested_turn += 1
                        if event.key == pygame.K_LEFT:
                            if self.requested_turn > 0:
                                self.requested_turn -= 1

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

            if all(drone.is_at_target() for drone in self.drones):
                if self.turn < self.requested_turn:
                    self.turn += 1
                elif self.turn > self.requested_turn:
                    self.turn -= 1

            self.drones.update(self.zoom, self.turn, dt)
            self.position_drones()

            # display the background
            self.screen.fill(self.BACKGOUND_COLOR)

            # draw line
            for name_1, name_2, size in self.connections:
                self.draw_line_offset(
                    self.hubs[name_1], self.hubs[name_2], size)

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
                    f"Turn: {self.turn}", True, self.TEXT_ATH_COLOR),
                self.write_box).bottomleft

            # display the hub info at the top left of the screen
            if mouse_over_circle:
                self.display_hub_info(circle)

            pygame.display.flip()
        pygame.quit()
