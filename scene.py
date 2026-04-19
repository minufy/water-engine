from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scene:
    elements: list[Any] = field(default_factory=list)

    def add_element(self, element: Any) -> None:
        self.elements.append(element)

    def remove_element(self, element: Any) -> None:
        self.elements.remove(element)

    def clear(self) -> None:
        self.elements.clear()
