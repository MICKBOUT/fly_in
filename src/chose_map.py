from pathlib import Path

import pygame


MapFolders = dict[str, list[str]]


def get_folder(path: str = "maps") -> MapFolders:
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
        fill_color = self.BORDER_COLOR if is_hovered else self.RECT_COLOR
        border_color = self.RECT_COLOR if is_hovered else self.BORDER_COLOR
        pygame.draw.rect(self.screen, fill_color, rect)
        pygame.draw.rect(self.screen, border_color, rect, self.RECT_BORDER)

    def draw_label(self, label: str, rect: pygame.Rect) -> None:
        render = self.font.render(label, True, self.TEXT_ATH_COLOR)
        text_x = rect.centerx - (render.get_width() // 2)
        text_y = rect.centery - (render.get_height() // 2)
        self.screen.blit(render, (text_x, text_y))

    def open_folder(self, folder_name: str) -> None:
        self.selected_folder = folder_name
        self.file_rects = self.build_button_rects(self.maps_dict[folder_name])

    def close_folder(self) -> None:
        self.selected_folder = None
        self.file_rects = {}

    def handle_folder_click(self, mouse_pos: tuple[int, int]) -> None:
        for folder_name, rect in self.folder_rects.items():
            if rect.collidepoint(mouse_pos):
                self.open_folder(folder_name)
                return

    def handle_file_click(self, mouse_pos: tuple[int, int]) -> str | None:
        if self.back_rect.collidepoint(mouse_pos):
            self.close_folder()
            return None

        for file_name, rect in self.file_rects.items():
            if rect.collidepoint(mouse_pos):
                return file_name
        return None

    def draw_folder_view(self, mouse_pos: tuple[int, int]) -> None:
        for folder_name, rect in self.folder_rects.items():
            self.draw_button(rect.collidepoint(mouse_pos), rect)
            self.draw_label(Path(folder_name).name, rect)

    def draw_file_view(self, mouse_pos: tuple[int, int]) -> None:
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
