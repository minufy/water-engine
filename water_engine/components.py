from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pygame

from .config import ROOT, color_to_hex


if TYPE_CHECKING:
    from .engine import Engine
    from .scene import GameObject, Scene


class Component:
    type_name = "Component"

    def __init__(self) -> None:
        self.game_object: GameObject | None = None
        self.enabled = True

    @property
    def scene(self) -> "Scene":
        if not self.game_object:
            raise RuntimeError("Component is not attached to a GameObject.")
        return self.game_object.scene

    def start(self) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass

    def on_gui(self) -> None:
        pass

    def clone_for(self, engine: "Engine") -> "Component":
        raise NotImplementedError


@dataclass
class Transform(Component):
    position: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    scale: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 1))
    rotation: float = 0.0
    type_name: str = "Transform"

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        rotation: float = 0.0,
    ) -> None:
        super().__init__()
        self.position = pygame.Vector2(x, y)
        self.scale = pygame.Vector2(scale_x, scale_y)
        self.rotation = rotation

    def clone_for(self, engine: "Engine") -> "Transform":
        return Transform(self.position.x, self.position.y, self.scale.x, self.scale.y, self.rotation)


class Sprite(Component):
    type_name = "Sprite"

    def __init__(
        self,
        size: tuple[int, int] = (64, 64),
        color: str = "#38bdf8",
        image_path: str | None = None,
    ) -> None:
        super().__init__()
        self.size = size
        self.color = pygame.Color(color)
        self.image_path = image_path
        self._image: pygame.Surface | None = None

    def start(self) -> None:
        if self.image_path:
            path = ROOT / self.image_path
            if path.exists():
                self._image = pygame.image.load(path.as_posix()).convert_alpha()

    def draw(self, surface: pygame.Surface) -> None:
        transform = self.game_object.get_component(Transform)
        camera_offset = self.scene.engine.editor.camera_offset
        draw_width = max(1, int(self.size[0] * abs(transform.scale.x)))
        draw_height = max(1, int(self.size[1] * abs(transform.scale.y)))

        sprite_surface = pygame.Surface((self.size[0], self.size[1]), pygame.SRCALPHA)
        if self._image:
            scaled_image = pygame.transform.smoothscale(self._image, (self.size[0], self.size[1]))
            sprite_surface.blit(scaled_image, (0, 0))
        else:
            pygame.draw.rect(
                sprite_surface,
                self.color,
                pygame.Rect(0, 0, self.size[0], self.size[1]),
                border_radius=10,
            )

        scaled_surface = pygame.transform.smoothscale(sprite_surface, (draw_width, draw_height))
        if transform.scale.x < 0 or transform.scale.y < 0:
            scaled_surface = pygame.transform.flip(scaled_surface, transform.scale.x < 0, transform.scale.y < 0)
        rotated_surface = pygame.transform.rotate(scaled_surface, transform.rotation)
        center = (
            int(transform.position.x - camera_offset.x + draw_width / 2),
            int(transform.position.y - camera_offset.y + draw_height / 2),
        )
        rect = rotated_surface.get_rect(center=center)
        surface.blit(rotated_surface, rect)

    def clone_for(self, engine: "Engine") -> "Sprite":
        return Sprite(size=self.size, color=color_to_hex(self.color), image_path=self.image_path)


class Collider(Component):
    type_name = "Collider"

    def __init__(
        self,
        width: int = 64,
        height: int = 64,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        is_trigger: bool = False,
        visible: bool = True,
    ) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.offset = pygame.Vector2(offset_x, offset_y)
        self.is_trigger = is_trigger
        self.visible = visible

    def get_rect(self) -> pygame.Rect:
        transform = self.game_object.get_component(Transform)
        scaled_width = max(1, int(self.width * abs(transform.scale.x)))
        scaled_height = max(1, int(self.height * abs(transform.scale.y)))
        return pygame.Rect(
            int(transform.position.x + self.offset.x),
            int(transform.position.y + self.offset.y),
            scaled_width,
            scaled_height,
        )

    def draw(self, surface: pygame.Surface) -> None:
        if self.visible:
            camera_offset = self.scene.engine.editor.camera_offset
            rect = self.get_rect().move(-camera_offset.x, -camera_offset.y)
            pygame.draw.rect(surface, pygame.Color("#f97316"), rect, width=2)

    def clone_for(self, engine: "Engine") -> "Collider":
        return Collider(
            width=self.width,
            height=self.height,
            offset_x=self.offset.x,
            offset_y=self.offset.y,
            is_trigger=self.is_trigger,
            visible=self.visible,
        )


class LuaVectorProxy:
    def __init__(self, vector: pygame.Vector2) -> None:
        object.__setattr__(self, "_vector", vector)

    @property
    def x(self) -> float:
        return float(self._vector.x)

    @x.setter
    def x(self, value: float) -> None:
        self._vector.x = float(value)

    @property
    def y(self) -> float:
        return float(self._vector.y)

    @y.setter
    def y(self, value: float) -> None:
        self._vector.y = float(value)

    def __getitem__(self, key: str) -> float:
        if key == "x":
            return self.x
        if key == "y":
            return self.y
        raise KeyError(key)

    def __setitem__(self, key: str, value: float) -> None:
        if key == "x":
            self.x = value
            return
        if key == "y":
            self.y = value
            return
        raise KeyError(key)


class LuaTransformProxy:
    def __init__(self, transform: Transform) -> None:
        object.__setattr__(self, "_transform", transform)
        object.__setattr__(self, "position", LuaVectorProxy(transform.position))
        object.__setattr__(self, "scale", LuaVectorProxy(transform.scale))

    @property
    def rotation(self) -> float:
        return float(self._transform.rotation)

    @rotation.setter
    def rotation(self, value: float) -> None:
        self._transform.rotation = float(value)

    def __getitem__(self, key: str) -> Any:
        if key == "position":
            return self.position
        if key == "scale":
            return self.scale
        if key == "rotation":
            return self.rotation
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "rotation":
            self.rotation = value
            return
        raise KeyError(key)


class LuaScript(Component):
    type_name = "LuaScript"

    def __init__(self, engine: "Engine", script_path: str) -> None:
        super().__init__()
        self.engine = engine
        self.script_path = ROOT / script_path
        self.script_relative_path = script_path
        self.lua_table: Any = None

    def start(self) -> None:
        if not self.script_path.exists():
            raise FileNotFoundError(f"Lua script not found: {self.script_path}")

        source = self.script_path.read_text(encoding="utf-8")
        factory = self.engine.lua.execute(source)
        if not callable(factory):
            raise TypeError(f"Lua script must return a function: {self.script_path}")

        self.lua_table = factory()
        self._inject_context()
        self._call("start")

    def update(self, dt: float) -> None:
        self._call("update", dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.engine.render_context.set_surface(surface)
        self._call("draw")

    def on_gui(self) -> None:
        self._call("on_gui")

    def _inject_context(self) -> None:
        if self.lua_table is None:
            return
        transform = self.game_object.get_component(Transform)
        self.lua_table["gameObject"] = self.game_object
        self.lua_table["transform"] = LuaTransformProxy(transform)
        self.lua_table["GetComponent"] = lambda _, component_name: self.game_object.get_component_by_name(component_name)
        self.lua_table["engine"] = self.engine

    def _call(self, name: str, *args: Any) -> Any:
        if self.lua_table is None:
            return None
        func = self.lua_table[name]
        if func is None:
            return None
        return func(self.lua_table, *args)

    def clone_for(self, engine: "Engine") -> "LuaScript":
        return LuaScript(engine, self.script_relative_path)
