from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .components import Collider, Component, Sprite, Transform


if TYPE_CHECKING:
    from .engine import Engine


class GameObject:
    def __init__(self, name: str, scene: "Scene") -> None:
        self.name = name
        self.scene = scene
        self.components: list[Component] = []
        self.active = True
        self.add_component(Transform())

    def add_component(self, component: Component) -> Component:
        component.game_object = self
        self.components.append(component)
        return component

    def remove_component(self, component: Component) -> None:
        if isinstance(component, Transform):
            raise ValueError("Transform component cannot be removed.")
        self.components.remove(component)

    def get_component(self, component_type: type[Component]) -> Component:
        for component in self.components:
            if isinstance(component, component_type):
                return component
        raise LookupError(f"{self.name} does not have component {component_type.__name__}")

    def get_component_by_name(self, component_name: str) -> Component:
        for component in self.components:
            if component.type_name == component_name or component.__class__.__name__ == component_name:
                return component
        raise LookupError(f"{self.name} does not have component {component_name}")

    def try_get_component(self, component_type: type[Component]) -> Component | None:
        for component in self.components:
            if isinstance(component, component_type):
                return component
        return None

    def get_bounds(self) -> pygame.Rect:
        collider = self.try_get_component(Collider)
        if collider:
            return collider.get_rect()
        sprite = self.try_get_component(Sprite)
        transform = self.get_component(Transform)
        if sprite:
            return pygame.Rect(
                int(transform.position.x),
                int(transform.position.y),
                max(1, int(sprite.size[0] * abs(transform.scale.x))),
                max(1, int(sprite.size[1] * abs(transform.scale.y))),
            )
        return pygame.Rect(int(transform.position.x), int(transform.position.y), 32, 32)

    def start(self) -> None:
        for component in self.components:
            component.start()

    def update(self, dt: float) -> None:
        if not self.active:
            return
        for component in self.components:
            if component.enabled:
                component.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.active:
            return
        for component in self.components:
            if component.enabled:
                component.draw(surface)

    def on_gui(self) -> None:
        if not self.active:
            return
        for component in self.components:
            if component.enabled:
                component.on_gui()

    def clone_for_scene(self, scene: "Scene") -> "GameObject":
        clone = GameObject(self.name, scene)
        clone.active = self.active

        original_transform = self.get_component(Transform)
        clone_transform = clone.get_component(Transform)
        clone_transform.position.update(original_transform.position.x, original_transform.position.y)
        clone_transform.scale.update(original_transform.scale.x, original_transform.scale.y)
        clone_transform.rotation = original_transform.rotation

        for component in self.components:
            if isinstance(component, Transform):
                continue
            clone.add_component(component.clone_for(scene.engine))
        return clone


class Scene:
    def __init__(self, name: str, engine: "Engine") -> None:
        self.name = name
        self.engine = engine
        self.game_objects: list[GameObject] = []
        self.started = False
        self.selected_object: GameObject | None = None
        self.selected_objects: list[GameObject] = []

    def create_object(self, name: str) -> GameObject:
        game_object = GameObject(name, self)
        self.game_objects.append(game_object)
        if self.selected_object is None:
            self.selected_object = game_object
            self.selected_objects = [game_object]
        return game_object

    def add_existing_object(self, game_object: GameObject) -> None:
        self.game_objects.append(game_object)
        game_object.scene = self
        if self.selected_object is None:
            self.selected_object = game_object
            self.selected_objects = [game_object]

    def remove_object(self, game_object: GameObject) -> None:
        self.game_objects.remove(game_object)
        if game_object in self.selected_objects:
            self.selected_objects = [obj for obj in self.selected_objects if obj is not game_object]
        if self.selected_object is game_object:
            self.selected_object = self.game_objects[0] if self.game_objects else None
        if not self.selected_objects and self.selected_object is not None:
            self.selected_objects = [self.selected_object]

    def start(self) -> None:
        if self.started:
            return
        for game_object in self.game_objects:
            game_object.start()
        self.started = True

    def update(self, dt: float) -> None:
        self.start()
        for game_object in self.game_objects:
            game_object.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        for game_object in self.game_objects:
            game_object.draw(surface)

    def on_gui(self) -> None:
        for game_object in self.game_objects:
            game_object.on_gui()

    def clone_for_engine(self, engine: "Engine") -> "Scene":
        cloned_scene = Scene(self.name, engine)
        selection_name = self.selected_object.name if self.selected_object else None
        selection_names = {game_object.name for game_object in self.selected_objects}
        for game_object in self.game_objects:
            clone = game_object.clone_for_scene(cloned_scene)
            cloned_scene.add_existing_object(clone)
            if clone.name == selection_name:
                cloned_scene.selected_object = clone
            if clone.name in selection_names:
                cloned_scene.selected_objects.append(clone)
        if cloned_scene.selected_object and not cloned_scene.selected_objects:
            cloned_scene.selected_objects = [cloned_scene.selected_object]
        return cloned_scene
