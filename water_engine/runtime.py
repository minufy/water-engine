from __future__ import annotations

from typing import TYPE_CHECKING

import pygame


if TYPE_CHECKING:
    from .components import Collider
    from .scene import GameObject


class RenderContext:
    def __init__(self) -> None:
        self.surface: pygame.Surface | None = None
        self.camera_offset = pygame.Vector2(0, 0)

    def set_surface(self, surface: pygame.Surface) -> None:
        self.surface = surface

    def set_camera_offset(self, offset: pygame.Vector2) -> None:
        self.camera_offset = offset

    def draw_rect(self, x: float, y: float, w: float, h: float, color: str, width: int = 0) -> None:
        if self.surface is None:
            return
        pygame.draw.rect(
            self.surface,
            pygame.Color(color),
            pygame.Rect(x - self.camera_offset.x, y - self.camera_offset.y, w, h),
            width=width,
        )

    def draw_circle(self, x: float, y: float, radius: float, color: str, width: int = 0) -> None:
        if self.surface is None:
            return
        pygame.draw.circle(
            self.surface,
            pygame.Color(color),
            (int(x - self.camera_offset.x), int(y - self.camera_offset.y)),
            int(radius),
            width=width,
        )

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str,
        width: int = 1,
    ) -> None:
        if self.surface is None:
            return
        pygame.draw.line(
            self.surface,
            pygame.Color(color),
            (x1 - self.camera_offset.x, y1 - self.camera_offset.y),
            (x2 - self.camera_offset.x, y2 - self.camera_offset.y),
            width=width,
        )


class PhysicsAPI:
    def overlaps(self, first: "Collider", second: "Collider") -> bool:
        return first.get_rect().colliderect(second.get_rect())

    def query_overlaps(self, collider: "Collider") -> list["GameObject"]:
        hits: list["GameObject"] = []
        scene = collider.scene
        for game_object in scene.game_objects:
            if game_object is collider.game_object:
                continue
            other = game_object.try_get_component(type(collider))
            if other and self.overlaps(collider, other):
                hits.append(game_object)
        return hits


class InputAPI:
    def __init__(self) -> None:
        self._keys = None

    def refresh(self) -> None:
        self._keys = pygame.key.get_pressed()

    def pressed(self, key_name: str) -> bool:
        if self._keys is None:
            self.refresh()
        key_code = getattr(pygame, f"K_{key_name.lower()}", None)
        if key_code is None:
            return False
        return bool(self._keys[key_code])
