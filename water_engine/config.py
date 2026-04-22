from __future__ import annotations

from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent.parent
SCREEN_SIZE = (1280, 720)
PANEL_BG = pygame.Color("#282828")
WINDOW_BG = pygame.Color("#1d2021")
CANVAS_BG = pygame.Color("#32302f")
MOVE_STEP = 8
ROTATE_STEP = 5
SCALE_STEP = 0.1

UI_BG = pygame.Color("#282828")
UI_PANEL = pygame.Color("#32302f")
UI_PANEL_ALT = pygame.Color("#3c3836")
UI_TEXT = pygame.Color("#ebdbb2")
UI_MUTED = pygame.Color("#a89984")
UI_ACCENT = pygame.Color("#83a598")
UI_WARNING = pygame.Color("#fabd2f")
UI_SUCCESS = pygame.Color("#b8bb26")
UI_DANGER = pygame.Color("#fb4934")


def color_to_hex(color: pygame.Color) -> str:
    return f"#{color.r:02x}{color.g:02x}{color.b:02x}"
