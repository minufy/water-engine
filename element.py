from dataclasses import dataclass, field
from typing import Any


@dataclass
class Component:
    type_name: str


@dataclass
class TransformComponent(Component):
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class MeshRendererComponent(Component):
    mesh_id: str = ""
    material_id: str = ""


@dataclass
class ScriptComponent(Component):
    script_name: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class Element:
    name: str
    components: list[Component] = field(default_factory=list)

    def add_component(self, component: Component) -> None:
        self.components.append(component)

    def remove_component(self, component: Component) -> None:
        self.components.remove(component)
