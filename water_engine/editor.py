from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pygame
import pygame_gui

from .components import Collider, LuaScript, Sprite, Transform
from .config import ROOT, UI_ACCENT, UI_BG, UI_MUTED, UI_PANEL, UI_PANEL_ALT, UI_SUCCESS, UI_TEXT, UI_WARNING
from .config import color_to_hex


if TYPE_CHECKING:
    from .scene import GameObject, Scene


@dataclass
class EditorSnapshot:
    scene: Scene
    camera_offset: pygame.Vector2


@dataclass
class EditorState:
    tool: str = "move"
    is_playing: bool = False
    selected_component_index: int = 0
    play_snapshot: Scene | None = None
    drag_active: bool = False
    drag_origin_mouse: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    drag_origin_position: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    drag_origin_scale: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 1))
    drag_origin_rotation: float = 0.0
    drag_origin_angle: float = 0.0
    drag_center: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    drag_origin_bounds_size: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(1, 1))
    drag_axis: str | None = None
    drag_corner: str | None = None
    drag_anchor: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    camera_offset: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    panning: bool = False
    pan_origin_mouse: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    pan_origin_offset: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    selecting: bool = False
    selection_origin: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    selection_current: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    drag_origin_positions: dict[Any, pygame.Vector2] = field(default_factory=dict)
    undo_stack: list[EditorSnapshot] = field(default_factory=list)
    redo_stack: list[EditorSnapshot] = field(default_factory=list)
    pending_snapshot: EditorSnapshot | None = None
    interaction_changed: bool = False


class EditorUI:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.font_regular = pygame.font.Font((ROOT / "assets/fonts/Galmuri9.ttf").as_posix(), 16)
        self.font_bold = pygame.font.Font((ROOT / "assets/fonts/Galmuri11-Bold.ttf").as_posix(), 18)
        self.manager = pygame_gui.UIManager(engine.window_size, theme_path=self._theme_path())
        self._dirty = True
        self.object_buttons: dict[Any, GameObject] = {}
        self.component_buttons: dict[Any, int] = {}
        self.dynamic_elements: list[Any] = []
        self.object_hitboxes: list[tuple[pygame.Rect, GameObject]] = []
        self.component_hitboxes: list[tuple[pygame.Rect, int]] = []
        self.context_buttons: dict[Any, str] = {}
        self.context_menu: Any = None
        self.context_elements: list[Any] = []
        self.context_hitboxes: list[tuple[pygame.Rect, str]] = []
        self.inspector_fields: dict[str, Any] = {}
        self._build_static_layout()

    def hierarchy_rect(self) -> pygame.Rect:
        _, height = self.engine.window_size
        return pygame.Rect(16, 16, 250, max(280, height - 32))

    def inspector_rect(self) -> pygame.Rect:
        width, height = self.engine.window_size
        return pygame.Rect(max(280, width - 316), 16, 300, max(280, height - 32))

    def canvas_rect(self) -> pygame.Rect:
        width, height = self.engine.window_size
        left_width = 266
        right_width = 316
        x = left_width + 24
        y = 96
        canvas_width = max(320, width - left_width - right_width - 40)
        canvas_height = max(240, height - 112)
        return pygame.Rect(x, y, canvas_width, canvas_height)

    def toolbar_rect(self) -> pygame.Rect:
        canvas = self.canvas_rect()
        return pygame.Rect(canvas.x, 16, canvas.width, 64)

    def _build_static_layout(self) -> None:
        self.hierarchy_panel = pygame_gui.elements.UIPanel(
            relative_rect=self.hierarchy_rect(),
            starting_height=1,
            manager=self.manager,
        )
        self.inspector_panel = pygame_gui.elements.UIPanel(
            relative_rect=self.inspector_rect(),
            starting_height=1,
            manager=self.manager,
        )
        self.toolbar_panel = pygame_gui.elements.UIPanel(
            relative_rect=self.toolbar_rect(),
            starting_height=1,
            manager=self.manager,
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 12, 220, 28),
            text="Hierarchy",
            manager=self.manager,
            container=self.hierarchy_panel,
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 12, 220, 28),
            text="Inspector",
            manager=self.manager,
            container=self.inspector_panel,
        )

        self.play_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(12, 14, 80, 32),
            text="Play",
            manager=self.manager,
            container=self.toolbar_panel,
        )
        self.stop_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(100, 14, 80, 32),
            text="Stop",
            manager=self.manager,
            container=self.toolbar_panel,
        )
        self.mode_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(200, 12, 120, 24),
            text="Mode: Edit",
            manager=self.manager,
            container=self.toolbar_panel,
        )
        self.tool_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(200, 34, 180, 24),
            text="Tool: Move",
            manager=self.manager,
            container=self.toolbar_panel,
        )
        self.help_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(320, 22, max(120, self.toolbar_rect().width - 332), 24),
            text="Drag / Right click",
            manager=self.manager,
            container=self.toolbar_panel,
        )

    def rebuild_manager(self) -> None:
        self.manager = pygame_gui.UIManager(self.engine.window_size, theme_path=self._theme_path())
        self.dynamic_elements = []
        self.object_buttons = {}
        self.component_buttons = {}
        self.object_hitboxes = []
        self.component_hitboxes = []
        self.context_buttons = {}
        self.context_elements = []
        self.context_menu = None
        self.context_hitboxes = []
        self.inspector_fields = {}
        self._build_static_layout()
        self._dirty = True

    def _theme_path(self) -> str:
        template_path = ROOT / "assets/ui/theme.json"
        generated_path = ROOT / "assets/ui/theme.generated.json"
        theme = json.loads(template_path.read_text(encoding="utf-8"))
        defaults_font = theme.setdefault("defaults", {}).setdefault("font", {})
        defaults_font["regular_path"] = (ROOT / "assets/fonts/Galmuri9.ttf").as_posix()
        defaults_font["bold_path"] = (ROOT / "assets/fonts/Galmuri11-Bold.ttf").as_posix()
        button_font = theme.setdefault("button", {}).setdefault("font", {})
        button_font["bold"] = "0"
        button_font["regular_path"] = (ROOT / "assets/fonts/Galmuri9.ttf").as_posix()
        button_font["bold_path"] = (ROOT / "assets/fonts/Galmuri11-Bold.ttf").as_posix()
        generated_path.write_text(json.dumps(theme, ensure_ascii=True, indent=2), encoding="utf-8")
        return generated_path.as_posix()

    def mark_dirty(self) -> None:
        self._dirty = True

    def close_context_menu(self) -> None:
        if self.context_menu is not None:
            self.context_menu.kill()
            self.context_menu = None
        for element in self.context_elements:
            element.kill()
        self.context_elements.clear()
        self.context_buttons.clear()
        self.context_hitboxes.clear()

    def _clear_dynamic(self) -> None:
        for element in self.dynamic_elements:
            element.kill()
        self.dynamic_elements.clear()
        self.object_buttons.clear()
        self.component_buttons.clear()
        self.object_hitboxes.clear()
        self.component_hitboxes.clear()
        self.inspector_fields.clear()

    def rebuild(self, scene: Scene, editor: EditorState) -> None:
        self._clear_dynamic()

        top = 56
        hierarchy_rect = self.hierarchy_rect()
        for game_object in scene.game_objects:
            if game_object is scene.selected_object:
                prefix = ">"
            elif game_object in scene.selected_objects:
                prefix = "+"
            else:
                prefix = " "
            rect = pygame.Rect(12, top, hierarchy_rect.width - 28, 30)
            button = pygame_gui.elements.UIButton(
                relative_rect=rect,
                text=f"{prefix} {game_object.name}",
                manager=self.manager,
                container=self.hierarchy_panel,
            )
            self.dynamic_elements.append(button)
            self.object_buttons[button] = game_object
            self.object_hitboxes.append((rect.move(hierarchy_rect.x, hierarchy_rect.y), game_object))
            top += 34

        self._rebuild_inspector(scene, editor)
        self._dirty = False

    def _rebuild_inspector(self, scene: Scene, editor: EditorState) -> None:
        game_object = scene.selected_object
        if game_object is None:
            return

        transform = game_object.get_component(Transform)
        top = 56
        inspector_rect = self.inspector_rect()
        summary_lines = [
            f"{game_object.name}",
            f"{len(scene.selected_objects)} selected",
        ]
        for text in summary_lines:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(12, top, inspector_rect.width - 24, 22),
                text=text,
                manager=self.manager,
                container=self.inspector_panel,
            )
            self.dynamic_elements.append(label)
            top += 22

        top += 12
        for index, component in enumerate(game_object.components):
            prefix = "> " if index == editor.selected_component_index else ""
            rect = pygame.Rect(12, top, inspector_rect.width - 40, 28)
            button = pygame_gui.elements.UIButton(
                relative_rect=rect,
                text=f"{prefix}{component.type_name}",
                manager=self.manager,
                container=self.inspector_panel,
            )
            self.dynamic_elements.append(button)
            self.component_buttons[button] = index
            self.component_hitboxes.append((rect.move(inspector_rect.x, inspector_rect.y), index))
            top += 34

        top += 8
        top = self._build_transform_editor(top, game_object)

    def _build_transform_editor(self, top: int, game_object: GameObject) -> int:
        transform = game_object.get_component(Transform)
        inspector_width = self.inspector_rect().width

        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, top, inspector_width - 24, 24),
            text="Transform",
            manager=self.manager,
            container=self.inspector_panel,
        )
        self.dynamic_elements.append(title)
        top += 28

        field_specs = [
            ("pos_x", "Pos X", f"{transform.position.x:.2f}"),
            ("pos_y", "Pos Y", f"{transform.position.y:.2f}"),
            ("rotation", "Rotation", f"{transform.rotation:.2f}"),
        ]
        for key, label_text, value in field_specs:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(12, top, 72, 24),
                text=label_text,
                manager=self.manager,
                container=self.inspector_panel,
            )
            entry = pygame_gui.elements.UITextEntryLine(
                relative_rect=pygame.Rect(88, top, inspector_width - 104, 26),
                manager=self.manager,
                container=self.inspector_panel,
            )
            entry.set_text(value)
            self.dynamic_elements.extend([label, entry])
            self.inspector_fields[key] = entry
            top += 32

        slider_specs = [
            ("scale_x", "Scale X", transform.scale.x),
            ("scale_y", "Scale Y", transform.scale.y),
        ]
        for key, label_text, value in slider_specs:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(12, top, 72, 24),
                text=label_text,
                manager=self.manager,
                container=self.inspector_panel,
            )
            slider = pygame_gui.elements.UIHorizontalSlider(
                relative_rect=pygame.Rect(88, top, inspector_width - 140, 24),
                start_value=max(-3.0, min(3.0, value)),
                value_range=(-3.0, 3.0),
                manager=self.manager,
                container=self.inspector_panel,
            )
            value_label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(inspector_width - 48, top, 36, 24),
                text=f"{value:.2f}",
                manager=self.manager,
                container=self.inspector_panel,
            )
            self.dynamic_elements.extend([label, slider, value_label])
            self.inspector_fields[key] = slider
            self.inspector_fields[f"{key}_label"] = value_label
            top += 32

        top += 10
        top = self._build_component_editor(top, game_object)
        return top

    def _build_component_editor(self, top: int, game_object: GameObject) -> int:
        inspector_width = self.inspector_rect().width
        component = game_object.components[max(0, min(self.engine.editor.selected_component_index, len(game_object.components) - 1))]

        title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, top, inspector_width - 24, 24),
            text=f"{component.type_name} Values",
            manager=self.manager,
            container=self.inspector_panel,
        )
        self.dynamic_elements.append(title)
        top += 28

        rows: list[tuple[str, str, str]] = []
        if isinstance(component, Sprite):
            rows = [
                ("sprite_width", "Width", str(component.size[0])),
                ("sprite_height", "Height", str(component.size[1])),
                ("sprite_color", "Color", color_to_hex(component.color)),
                ("sprite_image", "Image", component.image_path or ""),
            ]
        elif isinstance(component, Collider):
            rows = [
                ("collider_width", "Width", str(component.width)),
                ("collider_height", "Height", str(component.height)),
                ("collider_offset_x", "Off X", f"{component.offset.x:.2f}"),
                ("collider_offset_y", "Off Y", f"{component.offset.y:.2f}"),
                ("collider_trigger", "Trigger", str(component.is_trigger).lower()),
                ("collider_visible", "Visible", str(component.visible).lower()),
            ]
        elif isinstance(component, LuaScript):
            rows = [("lua_script", "Script", component.script_relative_path)]

        for key, label_text, value in rows:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(12, top, 72, 24),
                text=label_text,
                manager=self.manager,
                container=self.inspector_panel,
            )
            entry = pygame_gui.elements.UITextEntryLine(
                relative_rect=pygame.Rect(88, top, inspector_width - 104, 26),
                manager=self.manager,
                container=self.inspector_panel,
            )
            entry.set_text(value)
            self.dynamic_elements.extend([label, entry])
            self.inspector_fields[key] = entry
            top += 32

        return top

    def refresh(self, scene: Scene, editor: EditorState) -> None:
        self.mode_label.set_text(f"Mode: {'Play' if editor.is_playing else 'Edit'}")
        self.tool_label.set_text(f"Tool: {editor.tool.title()}")
        if self._dirty:
            self.rebuild(scene, editor)

    def process_event(self, event: pygame.event.Event) -> None:
        self.manager.process_events(event)

    def show_context_menu(self, screen_pos: tuple[int, int], entries: list[tuple[str, str]]) -> None:
        self.close_context_menu()
        if not entries:
            return
        width = 180
        height = 8 + len(entries) * 34
        x, y = screen_pos
        max_x = self.engine.window_size[0] - width - 8
        max_y = self.engine.window_size[1] - height - 8
        panel_rect = pygame.Rect(max(8, min(x, max_x)), max(8, min(y, max_y)), width, height)
        self.context_menu = pygame_gui.elements.UIPanel(
            relative_rect=panel_rect,
            starting_height=30,
            manager=self.manager,
        )
        top = 6
        for label, action in entries:
            button_rect = pygame.Rect(8, top, width - 16, 28)
            button = pygame_gui.elements.UIButton(
                relative_rect=button_rect,
                text=label,
                manager=self.manager,
                container=self.context_menu,
            )
            self.context_elements.append(button)
            self.context_buttons[button] = action
            self.context_hitboxes.append((button_rect.move(panel_rect.x, panel_rect.y), action))
            top += 32

    def object_at(self, screen_pos: tuple[int, int]) -> GameObject | None:
        for rect, game_object in reversed(self.object_hitboxes):
            if rect.collidepoint(screen_pos):
                return game_object
        return None

    def component_at(self, screen_pos: tuple[int, int]) -> int | None:
        for rect, index in self.component_hitboxes:
            if rect.collidepoint(screen_pos):
                return index
        return None

    def handle_button(self, ui_element: Any) -> bool:
        engine = self.engine
        if ui_element == self.play_button:
            engine.enter_play_mode()
            return True
        if ui_element == self.stop_button:
            engine.stop_play_mode()
            return True
        if ui_element in self.object_buttons:
            engine.select_object(self.object_buttons[ui_element])
            return True
        if ui_element in self.component_buttons:
            engine.select_component(self.component_buttons[ui_element])
            return True
        if ui_element in self.context_buttons:
            action = self.context_buttons[ui_element]
            self.close_context_menu()
            engine.handle_context_action(action)
            return True
        return False

    def handle_value_change(self, event: pygame.event.Event) -> bool:
        engine = self.engine
        selected = engine.get_selected_object()
        if selected is None:
            return False
        transform = selected.get_component(Transform)
        component = selected.components[max(0, min(engine.editor.selected_component_index, len(selected.components) - 1))]

        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.inspector_fields.get("scale_x"):
                engine.push_undo_state()
                transform.scale.x = float(event.value)
                label = self.inspector_fields.get("scale_x_label")
                if label:
                    label.set_text(f"{transform.scale.x:.2f}")
                self.mark_dirty()
                return True
            if event.ui_element == self.inspector_fields.get("scale_y"):
                engine.push_undo_state()
                transform.scale.y = float(event.value)
                label = self.inspector_fields.get("scale_y_label")
                if label:
                    label.set_text(f"{transform.scale.y:.2f}")
                self.mark_dirty()
                return True

        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            updates = {
                "pos_x": ("position_x", self.inspector_fields.get("pos_x")),
                "pos_y": ("position_y", self.inspector_fields.get("pos_y")),
                "rotation": ("rotation", self.inspector_fields.get("rotation")),
            }
            for key, (_, field) in updates.items():
                if event.ui_element == field:
                    try:
                        value = float(field.get_text())
                    except ValueError:
                        return True
                    if key == "pos_x":
                        if value == transform.position.x:
                            return True
                        engine.push_undo_state()
                        transform.position.x = value
                    elif key == "pos_y":
                        if value == transform.position.y:
                            return True
                        engine.push_undo_state()
                        transform.position.y = value
                    elif key == "rotation":
                        if value == transform.rotation:
                            return True
                        engine.push_undo_state()
                        transform.rotation = value
                    self.mark_dirty()
                    return True
            return self._handle_component_value_change(engine, component, event)
        return False

    def _handle_component_value_change(self, engine: Any, component: Any, event: pygame.event.Event) -> bool:
        if event.type != pygame_gui.UI_TEXT_ENTRY_FINISHED:
            return False
        for key, field in self.inspector_fields.items():
            if not hasattr(field, "get_text") or event.ui_element != field:
                continue
            text = field.get_text()
            try:
                if isinstance(component, Sprite):
                    if key == "sprite_width":
                        value = max(1, int(float(text)))
                        if value == component.size[0]:
                            return True
                        engine.push_undo_state()
                        component.size = (value, component.size[1])
                    elif key == "sprite_height":
                        value = max(1, int(float(text)))
                        if value == component.size[1]:
                            return True
                        engine.push_undo_state()
                        component.size = (component.size[0], value)
                    elif key == "sprite_color":
                        color = pygame.Color(text)
                        if color == component.color:
                            return True
                        engine.push_undo_state()
                        component.color = color
                    elif key == "sprite_image":
                        image_path = text or None
                        if image_path == component.image_path:
                            return True
                        engine.push_undo_state()
                        component.image_path = image_path
                        component._image = None
                        component.start()
                elif isinstance(component, Collider):
                    if key == "collider_width":
                        value = max(1, int(float(text)))
                        if value == component.width:
                            return True
                        engine.push_undo_state()
                        component.width = value
                    elif key == "collider_height":
                        value = max(1, int(float(text)))
                        if value == component.height:
                            return True
                        engine.push_undo_state()
                        component.height = value
                    elif key == "collider_offset_x":
                        value = float(text)
                        if value == component.offset.x:
                            return True
                        engine.push_undo_state()
                        component.offset.x = value
                    elif key == "collider_offset_y":
                        value = float(text)
                        if value == component.offset.y:
                            return True
                        engine.push_undo_state()
                        component.offset.y = value
                    elif key == "collider_trigger":
                        value = text.strip().lower() in ("1", "true", "yes", "on")
                        if value == component.is_trigger:
                            return True
                        engine.push_undo_state()
                        component.is_trigger = value
                    elif key == "collider_visible":
                        value = text.strip().lower() in ("1", "true", "yes", "on")
                        if value == component.visible:
                            return True
                        engine.push_undo_state()
                        component.visible = value
                elif isinstance(component, LuaScript) and key == "lua_script":
                    if text == component.script_relative_path:
                        return True
                    engine.push_undo_state()
                    component.script_relative_path = text
                    component.script_path = ROOT / text
                    component.lua_table = None
                    if component.script_path.exists():
                        component.start()
            except (ValueError, TypeError, FileNotFoundError):
                return True
            self.mark_dirty()
            return True
        return False

    def context_action_at(self, screen_pos: tuple[int, int]) -> str | None:
        for rect, action in self.context_hitboxes:
            if rect.collidepoint(screen_pos):
                return action
        return None

    def update(self, dt: float) -> None:
        self.manager.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.manager.draw_ui(surface)

    def draw_chrome(self, surface: pygame.Surface, scene: Scene, editor: EditorState) -> None:
        hierarchy = self.hierarchy_rect()
        inspector = self.inspector_rect()
        toolbar = self.toolbar_rect()
        canvas = self.canvas_rect()

        pygame.draw.rect(surface, UI_PANEL, hierarchy, border_radius=14)
        pygame.draw.rect(surface, UI_PANEL, inspector, border_radius=14)
        pygame.draw.rect(surface, UI_PANEL_ALT, toolbar, border_radius=14)
        pygame.draw.rect(surface, UI_PANEL_ALT, canvas.inflate(16, 16), border_radius=16)

        self._draw_text(surface, "Hierarchy", self.font_regular, UI_TEXT, (hierarchy.x + 14, hierarchy.y + 12))
        self._draw_text(surface, "Inspector", self.font_regular, UI_TEXT, (inspector.x + 14, inspector.y + 12))
        self._draw_text(
            surface,
            f"{scene.name}  |  {len(scene.selected_objects)} selected",
            self.font_regular,
            UI_MUTED,
            (hierarchy.x + 14, hierarchy.y + 38),
        )
        self._draw_text(
            surface,
            f"{'Play' if editor.is_playing else 'Edit'} / {editor.tool.upper()}",
            self.font_regular,
            UI_SUCCESS if not editor.is_playing else UI_WARNING,
            (toolbar.x + 208, toolbar.y + 16),
        )
        self._draw_text(
            surface,
            "LMB: edit  MMB: pan  RMB: menu  Drag: multi-select",
            self.font_regular,
            UI_MUTED,
            (toolbar.x + 208, toolbar.y + 38),
        )

    def draw_selection_marquee(self, surface: pygame.Surface, editor: EditorState) -> None:
        if not editor.selecting:
            return
        rect = pygame.Rect(
            int(editor.selection_origin.x),
            int(editor.selection_origin.y),
            int(editor.selection_current.x - editor.selection_origin.x),
            int(editor.selection_current.y - editor.selection_origin.y),
        )
        rect.normalize()
        pygame.draw.rect(surface, UI_ACCENT, rect, width=2)
        fill = pygame.Surface(rect.size, pygame.SRCALPHA)
        fill.fill((131, 165, 152, 40))
        surface.blit(fill, rect.topleft)

    def _draw_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font, color: pygame.Color, pos: tuple[int, int]) -> None:
        surface.blit(font.render(text, True, color), pos)
