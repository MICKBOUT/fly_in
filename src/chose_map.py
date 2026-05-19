"""Map chooser UI used before running the simulation."""

from pathlib import Path

import pygame


MapFolders = dict[str, list[str]]


def get_folder(path: str = "maps") -> MapFolders:
    """Retrieve available map files organized by folder.

    This function scans the specified directory for subdirectories,
    and collects the paths of files within those subdirectories.
    It raises an error if the specified path does not exist or is not a
        directory.

    Args:
        path (str): The path to the directory containing map folders.
                    Defaults to "maps".

    Returns:
        MapFolders: A dictionary where the keys are folder paths and
                    the values are lists of map file paths.

    Raises:
        FileNotFoundError: If the specified path does not exist.
        NotADirectoryError: If the specified path is not a directory.
        ValueError: If no map files are found in the specified directory.
    """
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(path)
    if not root.is_dir():
        raise NotADirectoryError(path)

    maps_dict: MapFolders = {}
    for folder in sorted(entry for entry in root.iterdir() if entry.is_dir()):
        files = sorted(
            str(file_path)
            for file_path in folder.iterdir()
            if file_path.is_file()
        )
        if files:
            maps_dict[str(folder)] = files

    if not maps_dict:
        raise ValueError("Folder empty, no map found")
    return maps_dict


class Display_Chooser:
    """Display a simple menu to pick one map file.

        BACKGOUND_COLOR (tuple): Background color of the display.
        BORDER_COLOR (tuple): Border color of the buttons.
        RECT_COLOR (tuple): Color of the button rectangles.
        TEXT_ATH_COLOR (tuple): Color of the text in the buttons.
        BUTTON_WIDTH (int): Width of the buttons.
        BUTTON_HEIGHT (int): Height of the buttons.
        BACK_BUTTON_SIZE (int): Size of the back button.
        PADDING (int): Padding between buttons.
        RECT_BORDER (int): Width of the button border.
        BACK_ICON_PADDING (int): Padding for the back icon.

        maps_dict (MapFolders): A dictionary containing map folder information.

    Methods:
        build_button_rects(labels: list[str]) -> dict[str, pygame.Rect]:
            Build centered button rectangles for a list of labels.
        draw_button(is_hovered: bool, rect: pygame.Rect) -> None:
            Draw one chooser button with hover feedback.
        draw_label(label: str, rect: pygame.Rect) -> None:
            Draw centered text inside a chooser button.
        open_folder(folder_name: str) -> None:
            Switch the UI to the file list of one folder.
        close_folder() -> None:
            Return from the file view to the folder view.
        handle_folder_click(mouse_pos: tuple[int, int]) -> None:
            Open the clicked folder, if any.
        handle_file_click(mouse_pos: tuple[int, int]) -> str | None:
            Handle clicks in file view and return the chosen map.
        draw_folder_view(mouse_pos: tuple[int, int]) -> None:
            Render the top-level folder selection view.
        draw_file_view(mouse_pos: tuple[int, int]) -> None:
            Render the list of maps inside the selected folder.
        main() -> str | None:
            Run the chooser loop and return the selected map path.
    """

    BACKGOUND_COLOR = (91, 123, 122)
    BORDER_COLOR = (161, 124, 107)
    RECT_COLOR = (206, 181, 167)
    TEXT_ATH_COLOR = (0, 0, 0)

    BUTTON_WIDTH = 720
    BUTTON_HEIGHT = 128
    BACK_BUTTON_SIZE = 128
    PADDING = 32
    RECT_BORDER = 10
    BACK_ICON_PADDING = 32

    def __init__(self, maps_dict: MapFolders) -> None:
        """
        Initialize the chooser window and its cached layout.

        Args:
            maps_dict (MapFolders): A dictionary containing map folder
                information.

        Attributes:
            font (pygame.font.Font): The font used for rendering text.
            screen (pygame.Surface): The display surface for the chooser window
            clock (pygame.time.Clock): The clock used to manage the frame rate.
            screen_width (int): The width of the display screen.
            screen_height (int): The height of the display screen.
            maps_dict (MapFolders): The dictionary of map folders.
            folder_rects (dict): A dictionary of rectangles for each folder
                button.
            file_rects (dict[str, pygame.Rect]): A dictionary mapping file
                names to their rectangles.
            selected_folder (str | None): The currently selected folder, or
                None if none is selected.
            back_arrow_img (pygame.Surface): The image for the back arrow
                button.
            back_rect (pygame.Rect): The rectangle defining the back button's
                position and size.
        """
        """Initialize the chooser window and its cached layout."""
        pygame.init()
        pygame.display.set_caption("choose the maps")

        self.font = pygame.font.SysFont("Arial", 48)
        self.screen = pygame.display.set_mode((0, 0), 0, vsync=1)
        self.clock = pygame.time.Clock()

        self.screen_width, self.screen_height = self.screen.get_size()
        self.maps_dict = maps_dict

        self.folder_rects = self.build_button_rects(list(self.maps_dict))
        self.file_rects: dict[str, pygame.Rect] = {}

        self.selected_folder: str | None = None
        self.back_arrow_img = pygame.image.load(
            "assets/back-arrow.png"
        ).convert_alpha()
        self.back_rect = pygame.Rect(
            (
                self.folder_rects[next(iter(self.folder_rects))].left
                - self.BACK_BUTTON_SIZE
                - self.PADDING,
                self.PADDING,
            ),
            (self.BACK_BUTTON_SIZE, self.BACK_BUTTON_SIZE),
        )

    def build_button_rects(self, labels: list[str]) -> dict[str, pygame.Rect]:
        """Build centered button rectangles for a list of labels.

        Creates a dictionary of pygame.Rect objects positioned vertically
        and centered horizontally on the screen. Each rectangle represents
        a button with consistent dimensions and spacing.

        Args:
            labels: A list of string labels for the buttons.

        Returns:
            A dictionary mapping each label to its corresponding pygame.Rect
            object with position and size information.
        """
        rects: dict[str, pygame.Rect] = {}
        top = self.PADDING
        left = (self.screen_width - self.BUTTON_WIDTH) // 2

        for label in labels:
            rects[label] = pygame.Rect(
                (left, top),
                (self.BUTTON_WIDTH, self.BUTTON_HEIGHT),
            )
            top += self.BUTTON_HEIGHT + self.PADDING

        return rects

    def draw_button(self, is_hovered: bool, rect: pygame.Rect) -> None:
        """Draw a chooser button with dynamic hover feedback.

        Renders a button with colors that change based on hover state.
        When hovered, the fill and border colors are swapped to provide
        visual feedback to the user.

        Args:
            is_hovered: Whether the button is currently being hovered over.
            rect: The rectangular area where the button will be drawn.

        Returns:
            None
        """
        fill_color = self.BORDER_COLOR if is_hovered else self.RECT_COLOR
        border_color = self.RECT_COLOR if is_hovered else self.BORDER_COLOR
        pygame.draw.rect(self.screen, fill_color, rect)
        pygame.draw.rect(self.screen, border_color, rect, self.RECT_BORDER)

    def draw_label(self, label: str, rect: pygame.Rect) -> None:
        """Draw centered text inside a chooser button.

        Renders the given label text and blits it to the screen, centered
        within the provided rectangle.

        Args:
            label: The text string to render and display.
            rect: The pygame.Rect object defining the button area where
                the text should be centered.
        """
        render = self.font.render(label, True, self.TEXT_ATH_COLOR)
        text_x = rect.centerx - (render.get_width() // 2)
        text_y = rect.centery - (render.get_height() // 2)
        self.screen.blit(render, (text_x, text_y))

    def open_folder(self, folder_name: str) -> None:
        """Switch the UI to the file list of the specified folder.

        Updates the selected folder and rebuilds the file rectangles for button
        rendering based on the maps dictionary contents.

        Args:
            folder_name: The name of the folder to open and display.
        """
        self.selected_folder = folder_name
        self.file_rects = self.build_button_rects(self.maps_dict[folder_name])

    def close_folder(self) -> None:
        """Return from the file view to the folder view.

        Resets the selected folder and clears the file rectangles cache,
        returning the UI to the folder selection view.

        Returns:
            None
        """
        self.selected_folder = None
        self.file_rects = {}

    def handle_folder_click(self, mouse_pos: tuple[int, int]) -> None:
        """
        Handle a mouse click event on a folder.

        Iterates through all folder rectangles to detect collision with the
            mouse
        position. If a folder is clicked, opens that folder and stops
            processing.

        Args:
            mouse_pos (tuple[int, int]): The (x, y) coordinates of the mouse
                click.

        Returns:
            None
        """
        for folder_name, rect in self.folder_rects.items():
            if rect.collidepoint(mouse_pos):
                self.open_folder(folder_name)
                return

    def handle_file_click(self, mouse_pos: tuple[int, int]) -> str | None:
        """Handle clicks in file view and return the chosen map.

        Checks if the back button or a file button was clicked. If the back
        button is clicked, closes the folder and returns None. If a file is
        clicked, returns the file path.

        Args:
            mouse_pos: The (x, y) coordinates of the mouse click.

        Returns:
            The selected map file path, or None if the back button was clicked
            or no file was clicked.
        """
        if self.back_rect.collidepoint(mouse_pos):
            self.close_folder()
            return None

        for file_name, rect in self.file_rects.items():
            if rect.collidepoint(mouse_pos):
                return file_name
        return None

    def draw_folder_view(self, mouse_pos: tuple[int, int]) -> None:
        """Render the top-level folder selection view.

        Draws all folder buttons in the folder selection view with hover
        feedback. Each button displays the folder name centered within its
        rectangle.

        Args:
            mouse_pos: The (x, y) coordinates of the current mouse position.
        """
        for folder_name, rect in self.folder_rects.items():
            self.draw_button(rect.collidepoint(mouse_pos), rect)
            self.draw_label(Path(folder_name).name, rect)

    def draw_file_view(self, mouse_pos: tuple[int, int]) -> None:
        """Render the list of maps inside the selected folder.

        Draws file buttons for each map file in the current folder view,
        highlighting them based on mouse position. Also renders a back
        button with an arrow icon for navigation.

        Args:
            mouse_pos: A tuple of (x, y) coordinates representing the
                current mouse position in pixels.
        """
        for file_name, rect in self.file_rects.items():
            self.draw_button(rect.collidepoint(mouse_pos), rect)
            self.draw_label(Path(file_name).name, rect)

        self.draw_button(
            self.back_rect.collidepoint(mouse_pos),
            self.back_rect,
        )
        self.screen.blit(
            self.back_arrow_img,
            (
                self.back_rect.left + self.BACK_ICON_PADDING,
                self.back_rect.top + self.BACK_ICON_PADDING,
            ),
        )

    def main(self) -> str | None:
        """Run the chooser loop and return the selected map path.

        Displays the map chooser interface and handles user interactions
        until a map is selected or the window is closed. Returns the path
        of the selected map file, or None if no selection was made.

        Returns:
            str | None: The path of the selected map file, or None if the
                user closed the window without selecting a map.
        """
        running = True
        selected_map: str | None = None

        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        running = False
                    case pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if self.selected_folder is None:
                                running = False
                            else:
                                self.close_folder()
                    case pygame.MOUSEBUTTONDOWN:
                        if event.button != 1:
                            continue
                        if self.selected_folder is None:
                            self.handle_folder_click(event.pos)
                        else:
                            selected_map = self.handle_file_click(event.pos)
                            if selected_map is not None:
                                running = False

            self.screen.fill(self.BACKGOUND_COLOR)
            if self.selected_folder is None:
                self.draw_folder_view(mouse_pos)
            else:
                self.draw_file_view(mouse_pos)

            pygame.display.flip()

        pygame.quit()
        return selected_map
