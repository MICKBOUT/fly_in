import math
from typing import Callable, Iterable, TypedDict

import pygame

from models import NodeData


class ConnectionDisplayData(TypedDict):
    """Minimal connection data required by the display.

    Attributes:
        left: Name of the left hub in the connection.
        right: Name of the right hub in the connection.
        max_link_capacity: Maximum number of drones that can use this link.
    """
    left: str
    right: str
    max_link_capacity: int


class Drone(pygame.sprite.Sprite):
    """A sprite representing a delivery drone that follows a predefined path.

    This class manages a drone sprite that moves along waypoints in a delivery
    network. The drone interpolates between waypoints based on the current
    simulation turn and smoothly animates movement toward its target position.

    Attributes:
        DRONE_PNG_PATH (str): Path to the drone sprite image file.
        IMG_SIZE (int): Original size of the drone image in pixels.
        TARGET_SIZE (int): Target display size of the drone in pixels.
        BASE_RESCALE (float): Base scaling factor from original to target size.
        DRONE_SPEED (int): Movement speed of the drone in pixels per second.
        pos (tuple[float, float]): Current position of the drone in world
            coordinates.
        target_pos (tuple[float, float]): Target position the drone is moving
            toward.
        path (dict[int, str]): Mapping of turn numbers to waypoint names.
        loaded_img (pygame.Surface): The loaded drone sprite image.
        image (pygame.Surface): Current scaled drone image for rendering.
        rect (pygame.Rect): Rectangle for sprite positioning and collision
            detection.
        waypoint_to_pos (Callable): Callback function to convert waypoint names
            to coordinates.
    """
    DRONE_PNG_PATH = "assets/drone.png"
    IMG_SIZE = 512
    TARGET_SIZE = 32
    BASE_RESCALE = TARGET_SIZE / IMG_SIZE
    DRONE_SPEED = 720  # en pixel par seconde

    def __init__(
            self,
            start_pos: str,
            path: list[tuple[str, int]],
            drone_png: pygame.Surface,
            waypoint_to_pos: Callable[[str], tuple[int, int]]) -> None:
        """Create one drone sprite from a routed path.

        Args:
            start_pos: Name of the starting hub.
            path: List of (waypoint, turn) tuples for the drone's route.
            drone_png: Loaded drone sprite image.
            waypoint_to_pos: Callback to resolve hub names to coordinates.
        """
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
        self.rect: pygame.Rect = self.image.get_rect(center=(0, 0))

    def update(self, zoom: float, turn: int, dt: float) -> None:
        """Advance the drone toward its target for the current turn.

        Args:
            zoom: Current camera zoom level.
            turn: Current simulation turn.
            dt: Delta time since last update in seconds.
        """
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
        """Return whether the drone reached its current target.

        Returns:
            True if the drone is at its target position.
        """
        return self.pos == self.target_pos


class Circle(NodeData):
    """
    Circle class for displaying hub nodes in a graph visualization.

    A Circle represents a drawable hub node with position, color, and drone
        capacity.
    It extends NodeData to add visual rendering properties and coordinate
        scaling.

    Attributes:
        RADIUS (int): The radius of the circle in pixels (25).
        true_x (int): The original unscaled x coordinate.
        true_y (int): The original unscaled y coordinate.
        is_rainbow (bool): Whether the circle should display with rainbow
            coloring.
        display_color (str): The color to use for rendering the circle.
    """
    RADIUS = 25

    def __init__(
            self, name: str, x: int, y: int, zone: str,
            color: str | None, max_drones: int) -> None:
        """
        Initialize a Circle node for graph visualization.

        Args:
            name (str): The identifier/name of the hub.
            x (int): The x coordinate (scaled by 100 for display).
            y (int): The y coordinate (scaled by 100 for display).
            zone (str): The zone or region the hub belongs to.
            color (str | None): The color to display the hub. Can be a valid
                pygame color, "rainbow" for rainbow coloring, or None for white
            max_drones (int): The maximum number of drones this hub can support

        Returns:
            None
        """
        super().__init__(name, x * 100, y * 100, zone, color, max_drones)

        self.true_x, self.true_y = x, y
        self.is_rainbow = color == "rainbow"
        self.display_color: str = "white"
        if color is None or self.is_rainbow:
            return
        try:
            pygame.Color(color)
            self.display_color = color
        except ValueError:
            pass


class Display:
    """
    A Pygame-based display manager for rendering a map with hubs, connections,
    and drone animations.

    This class handles all visual rendering including hubs (nodes), connections
    (edges), drone sprites, camera controls, and a heads-up display (HUD) with
    information about hovered hubs. It manages camera zoom and pan operations,
    drone positioning, and user input events.

    Attributes:
        ZOOM_STEP (float): Multiplicative factor for each zoom operation.
        MIN_ZOOM (float): Minimum allowed zoom level.
        MAX_ZOOM (float): Maximum allowed zoom level.
        SPEED (int): Camera pan speed in pixels per second.
        BACKGOUND_COLOR (tuple): RGB color for the background.
        TEXT_ATH_COLOR (tuple): RGB color for text rendering.
        PERIMETER_COLOR (tuple): RGB color for hub borders.
        LINK_COLOR (tuple): RGB color for connection lines.
        font (pygame.font.Font): Font used for rendering text.
        screen (pygame.Surface): The main display surface.
        clock (pygame.time.Clock): Clock for managing frame rate and delta time
        zoom (float): Current zoom level.
        turn (int): Current simulation turn being displayed.
        requested_turn (int): Turn requested by user input.
        nb_turn (int): Total number of simulation turns.
        screen_size (tuple): Current screen dimensions (width, height).
        screen_width (int): Screen width in pixels.
        screen_height (int): Screen height in pixels.
        connections (set): Set of tuples representing connections between hubs.
        hubs (dict): Mapping of hub names to Circle objects.
        offset (list): Camera offset in world space [x, y].
        drones (pygame.sprite.Group): Group of Drone sprites to be rendered.
    """
    ZOOM_STEP = 1.25
    MIN_ZOOM = 0.5
    MAX_ZOOM = 20
    SPEED = 960
    BACKGOUND_COLOR = (91, 123, 122)
    TEXT_ATH_COLOR = (0, 0, 0)
    PERIMETER_COLOR = (161, 124, 107)
    LINK_COLOR = (206, 181, 167)

    def __init__(
      self, hub_dict: dict[str, NodeData],
      connections: Iterable[ConnectionDisplayData],
      paths: list[list[tuple[str, int]]], start_pos: str, nb_turn: int
    ) -> None:
        """Initialize the display and build all render objects.

        Args:
            hub_dict: Dictionary mapping hub names to their NodeData objects.
            connections: Iterable of ConnectionDisplayData objects representing
                network connections between hubs.
            paths: List of paths, where each path is a list of tuples
                containing hub names and turn numbers.
            start_pos: The starting position identifier for drones.
            nb_turn: Total number of turns in the simulation.

        Returns:
            None
        """
        pygame.init()
        pygame.display.set_caption("FLY IN !!!")

        self.font = pygame.font.SysFont("Arial", 48)
        self.screen = pygame.display.set_mode()
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
        """Convert graph nodes into display circles.

        Args:
            hub_dict (dict[str, NodeData]): A dictionary mapping hub names to
            their NodeData objects.

        Returns:
            dict[str, Circle]: A dictionary mapping hub names to their
            corresponding Circle objects.
        """
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
        """Draw a hub using the current camera transform.

        Args:
            circle (Circle): The circle object representing the hub.
            factor (float, optional): Scaling factor for the circle size.

        Returns:
            None
        """
        pygame.draw.circle(
            self.screen, self.circle_color(circle),
            self.world_to_screen(circle.x, circle.y),
            circle.RADIUS * self.zoom * factor
        )
        pygame.draw.circle(
            self.screen, (self.PERIMETER_COLOR),
            self.world_to_screen(circle.x, circle.y),
            circle.RADIUS * self.zoom * factor,
            int(5 * self.zoom),
        )

    def draw_line_offset(self, start: Circle, end: Circle, size: int) -> None:
        """
        Draw a connection line between two circles with camera transformation.

        Args:
            start (Circle): The starting circle of the connection.
            end (Circle): The ending circle of the connection.
            size (int): The thickness of the line to be drawn.

        Returns:
            None
        """
        pygame.draw.line(
            self.screen,
            self.LINK_COLOR,
            self.world_to_screen(start.x, start.y),
            self.world_to_screen(end.x, end.y),
            int(2 * self.zoom * size),
        )

    def position_drones(self) -> None:
        """Position drone sprites on the screen after their world update.

        This method organizes drones that occupy the same position on the
        screen. If multiple drones are at the same location, they are
        arranged in a circular formation around the center point.

        Returns:
            None
        """
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
        """Get the render color of a hub.

        Determines the color used for rendering a hub based on its properties.
        If the hub is set to rainbow mode, it calculates a color that cycles
        through the hues over time.

        Args:
            circle (Circle): The circle object representing the hub.

        Returns:
            str | pygame.Color: The color to use for rendering the hub.
        """
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
        """Resolve a hub name to its world-space position.

        Args:
            waypoint (str): The name of the hub to resolve.

        Returns:
            tuple[int, int]: The (x, y) coordinates of the hub in world space.
        """
        circle = self.hubs[waypoint]
        return circle.x, circle.y

    def screen_to_world(self, pos: tuple[int, int]) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates.

        Args:
            pos (tuple[int, int]): The (x, y) coordinates on the screen.

        Returns:
            tuple[float, float]: The corresponding (x, y) coordinates in world
            space.
        """
        x, y = pos
        return (
            self.offset[0] + (x / self.zoom),
            self.offset[1] + (y / self.zoom)
        )

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates.

        Args:
            x (float): The x coordinate in world space.
            y (float): The y coordinate in world space.

        Returns:
            tuple[int, int]: The corresponding (x, y) coordinates in screen
            space.
        """
        return (
            int((x - self.offset[0]) * self.zoom),
            int((y - self.offset[1]) * self.zoom)
        )

    def zoom_at(self, screen_pos: tuple[int, int], factor: float) -> None:
        """
        Zooms in or out while keeping a specified screen position anchored.

        This method adjusts the zoom level of the display based on a zoom
            factor, ensuring that the specified screen position remains fixed
            in the world space.

        Args:
            screen_pos (tuple[int, int]): The (x, y) coordinates on the screen
                to anchor the zoom.
            factor (float): The zoom factor to apply. A value greater than 1.0
                zooms in, while a value less than 1.0 zooms out.

        Returns:
            None: This method modifies in place and does not return a value.
        """
        world_x, world_y = self.screen_to_world(screen_pos)
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom:
            return

        self.zoom = new_zoom
        self.offset[0] = world_x - (screen_pos[0] / self.zoom)
        self.offset[1] = world_y - (screen_pos[1] / self.zoom)

    def render_write(self, text: str) -> tuple[int, int]:
        """
        Renders HUD text on the screen and returns the position for the next
            write.

        Args:
            text (str): The text to be rendered on the HUD.

        Returns:
            tuple[int, int]: The bottom-left coordinates of the rendered text.
        """
        return self.screen.blit(
            self.font.render(
                text, True, self.TEXT_ATH_COLOR), self.write_box).bottomleft

    def display_hub_info(self, circle: Circle) -> None:
        """Display hub information in the HUD.

        Renders the details of a hovered hub circle in the heads-up display,
        including its name, position, zone, color, and maximum drone capacity.

        Args:
            circle (Circle): The hub circle object containing the information
                to be displayed.

        Returns:
            None
        """
        self.write_box = self.render_write(f"Name: {circle.name}")
        self.write_box = self.render_write(
            f"Position (x, y): ({circle.true_x}, {circle.true_y})")
        self.write_box = self.render_write(f"Zone: {circle.zone}")
        self.write_box = self.render_write(f"Color: {circle.color}")
        self.write_box = self.render_write(
            f"Max drones: {circle.max_drones}")

    def main(self) -> None:
        """Run the main render and input loop.

        Manages the primary game loop including event handling, rendering,
        and updating the display. Handles user input for navigation (mouse
        dragging, keyboard controls), turn progression, and zoom functionality.
        Renders the background, connections, hubs, drones, and UI elements
        (FPS counter and turn indicator).

        The loop continues until the user requests to quit via window close
        or ESC key. Mouse wheel controls zoom level, WASD keys pan the view,
        arrow keys or space navigate between turns, and left mouse button
        enables panning. Hub information is displayed when the mouse hovers
        over a hub.
        """
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
