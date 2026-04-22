from __future__ import annotations

from typing import Any

import pygame
import pygame_gui
from lupa import LuaRuntime

from .components import Collider, LuaScript, Sprite, Transform
from .config import CANVAS_BG, MOVE_STEP, PANEL_BG, ROTATE_STEP, SCALE_STEP, SCREEN_SIZE, UI_ACCENT, UI_TEXT, WINDOW_BG
from .editor import EditorSnapshot, EditorState, EditorUI
from .runtime import InputAPI, PhysicsAPI, RenderContext
from .scene import GameObject, Scene


class Engine:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Water Engine")
        self.window_size = SCREEN_SIZE
        self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.render_context = RenderContext()
        self.physics = PhysicsAPI()
        self.input = InputAPI()
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.editor = EditorState()
        self.active_scene: Scene | None = None
        self._register_lua_api()
        self.ui = EditorUI(self)

    def canvas_rect(self) -> pygame.Rect:
        return self.ui.canvas_rect()

    def _selection_bounds(self) -> pygame.Rect | None:
        selected = self.get_selected_object()
        if selected is None:
            return None
        return selected.get_bounds()

    def _move_handle_hit(self, local_pos: pygame.Vector2) -> str | None:
        bounds = self._selection_bounds()
        if bounds is None:
            return None
        center = pygame.Vector2(bounds.center)
        x_handle = pygame.Vector2(center.x + 60, center.y)
        y_handle = pygame.Vector2(center.x, center.y - 60)
        if local_pos.distance_to(center) <= 14:
            return "xy"
        if local_pos.distance_to(x_handle) <= 12:
            return "x"
        if local_pos.distance_to(y_handle) <= 12:
            return "y"
        return None

    def _rotate_handle_hit(self, local_pos: pygame.Vector2) -> bool:
        bounds = self._selection_bounds()
        if bounds is None:
            return False
        center = pygame.Vector2(bounds.center)
        distance = local_pos.distance_to(center)
        return 36 <= distance <= 48

    def _scale_handle_hit(self, local_pos: pygame.Vector2) -> str | None:
        bounds = self._selection_bounds()
        if bounds is None:
            return None
        corners = {
            "top_left": pygame.Vector2(bounds.left, bounds.top),
            "top_right": pygame.Vector2(bounds.right, bounds.top),
            "bottom_left": pygame.Vector2(bounds.left, bounds.bottom),
            "bottom_right": pygame.Vector2(bounds.right, bounds.bottom),
        }
        for name, corner in corners.items():
            if local_pos.distance_to(corner) <= 12:
                return name
        return None

    def _register_lua_api(self) -> None:
        we = self.lua.table()
        graphics = self.lua.table()
        physics = self.lua.table()
        input_api = self.lua.table()
        debug = self.lua.table()

        graphics["draw_rect"] = self.render_context.draw_rect
        graphics["draw_circle"] = self.render_context.draw_circle
        graphics["draw_line"] = self.render_context.draw_line

        physics["overlaps"] = self.physics.overlaps
        physics["query_overlaps"] = self._lua_query_overlaps
        input_api["pressed"] = self.input.pressed

        debug["log"] = lambda message: print(f"[Lua] {message}")

        we["graphics"] = graphics
        we["physics"] = physics
        we["input"] = input_api
        we["debug"] = debug
        self.lua.globals()["we"] = we

    def _lua_query_overlaps(self, collider: Collider) -> Any:
        table = self.lua.table()
        for index, game_object in enumerate(self.physics.query_overlaps(collider), start=1):
            table[index] = game_object
        return table

    def load_scene(self, scene: Scene) -> None:
        self.active_scene = scene
        self.editor.selected_component_index = 0
        self.editor.undo_stack.clear()
        self.editor.redo_stack.clear()
        self.editor.pending_snapshot = None
        self.editor.interaction_changed = False
        self.ui.mark_dirty()

    def run(self) -> None:
        if self.active_scene is None:
            raise RuntimeError("No scene loaded.")

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_events()
            self.input.refresh()

            if self.editor.is_playing:
                self.active_scene.update(dt)
                self.active_scene.on_gui()

            self._render(dt)

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            if event.type == pygame.WINDOWRESIZED:
                self._handle_resize(event.x, event.y)
                continue

            self.ui.process_event(event)

            if event.type == pygame_gui.UI_BUTTON_PRESSED and self.ui.handle_button(event.ui_element):
                continue
            if event.type in (pygame_gui.UI_HORIZONTAL_SLIDER_MOVED, pygame_gui.UI_TEXT_ENTRY_FINISHED):
                if self.ui.handle_value_change(event):
                    continue

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_up(event)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event)

    def _handle_resize(self, width: int, height: int) -> None:
        self.window_size = (max(900, width), max(600, height))
        self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.ui.rebuild_manager()
        self.ui.mark_dirty()

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if self.active_scene is None:
            return
        mods = pygame.key.get_mods()

        if not self.editor.is_playing and event.key == pygame.K_z and mods & pygame.KMOD_CTRL:
            if mods & pygame.KMOD_SHIFT:
                self.redo()
            else:
                self.undo()
            return
        if not self.editor.is_playing and event.key == pygame.K_y and mods & pygame.KMOD_CTRL:
            self.redo()
            return

        if event.key == pygame.K_q:
            self.editor.tool = "select"
            self.ui.mark_dirty()
            return
        if event.key == pygame.K_w:
            self.editor.tool = "move"
            self.ui.mark_dirty()
            return
        if event.key == pygame.K_e:
            self.editor.tool = "rotate"
            self.ui.mark_dirty()
            return
        if event.key == pygame.K_r:
            self.editor.tool = "scale"
            self.ui.mark_dirty()
            return
        if event.key == pygame.K_ESCAPE:
            self.ui.close_context_menu()
            self.editor.drag_active = False
            if self.editor.is_playing:
                self.stop_play_mode()
            return
        if event.key == pygame.K_SPACE:
            if self.editor.is_playing:
                self.stop_play_mode()
            else:
                self.enter_play_mode()

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        if event.button == 3:
            self._open_context_menu(event.pos)
            return
        if event.button == 2:
            self._begin_pan(event.pos)
            return
        if event.button != 1:
            return

        action = self.ui.context_action_at(event.pos)
        if action is not None:
            self.ui.close_context_menu()
            self.handle_context_action(action)
            return

        self.ui.close_context_menu()
        if self.editor.is_playing or self.active_scene is None:
            return
        self._begin_canvas_interaction(event.pos)

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            if self.editor.selecting:
                self._finish_selection_box()
            self._finish_interaction()
            self.editor.drag_active = False
            self.editor.drag_axis = None
            self.editor.drag_corner = None
        elif event.button == 2:
            self._finish_interaction()
            self.editor.panning = False

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        if self.editor.panning:
            delta = pygame.Vector2(event.pos) - self.editor.pan_origin_mouse
            new_offset = self.editor.pan_origin_offset - delta
            if new_offset != self.editor.camera_offset:
                self.editor.camera_offset = new_offset
                self.editor.interaction_changed = True
            self.ui.mark_dirty()
            return
        if self.editor.selecting:
            self.editor.selection_current = pygame.Vector2(event.pos)
            self.ui.mark_dirty()
            return
        if not self.editor.drag_active or self.active_scene is None:
            return
        selected = self.get_selected_object()
        if selected is None:
            return
        canvas_rect = self.canvas_rect()
        local_mouse = pygame.Vector2(event.pos[0] - canvas_rect.x, event.pos[1] - canvas_rect.y) + self.editor.camera_offset
        transform = selected.get_component(Transform)

        if self.editor.tool == "move":
            delta = local_mouse - self.editor.drag_origin_mouse
            for game_object in self.get_selected_objects():
                game_transform = game_object.get_component(Transform)
                origin = self.editor.drag_origin_positions.get(game_object, game_transform.position.copy())
                new_position = origin.copy()
                if self.editor.drag_axis == "xy":
                    new_position += delta
                elif self.editor.drag_axis == "x":
                    new_position.x += delta.x
                elif self.editor.drag_axis == "y":
                    new_position.y += delta.y
                game_transform.position.update(new_position)
            self.editor.interaction_changed = True
        elif self.editor.tool == "rotate":
            current_angle = (local_mouse - self.editor.drag_center).as_polar()[1]
            transform.rotation = self.editor.drag_origin_rotation - (current_angle - self.editor.drag_origin_angle)
            self.editor.interaction_changed = True
        elif self.editor.tool == "scale":
            start_width = max(1.0, self.editor.drag_origin_bounds_size.x)
            start_height = max(1.0, self.editor.drag_origin_bounds_size.y)
            anchor = self.editor.drag_anchor
            width = max(8.0, abs(local_mouse.x - anchor.x))
            height = max(8.0, abs(local_mouse.y - anchor.y))
            original_x_side = -1 if self.editor.drag_corner and "left" in self.editor.drag_corner else 1
            original_y_side = -1 if self.editor.drag_corner and "top" in self.editor.drag_corner else 1
            current_x_side = -1 if local_mouse.x < anchor.x else 1
            current_y_side = -1 if local_mouse.y < anchor.y else 1
            sign_x = 1 if current_x_side == original_x_side else -1
            sign_y = 1 if current_y_side == original_y_side else -1
            base_scale_x = abs(self.editor.drag_origin_scale.x)
            base_scale_y = abs(self.editor.drag_origin_scale.y)
            base_sign_x = -1 if self.editor.drag_origin_scale.x < 0 else 1
            base_sign_y = -1 if self.editor.drag_origin_scale.y < 0 else 1
            transform.scale.x = base_scale_x * (width / start_width) * base_sign_x * sign_x
            transform.scale.y = base_scale_y * (height / start_height) * base_sign_y * sign_y
            transform.position.x = min(anchor.x, local_mouse.x)
            transform.position.y = min(anchor.y, local_mouse.y)
            self.editor.interaction_changed = True

        self.ui.mark_dirty()

    def _begin_canvas_interaction(self, mouse_pos: tuple[int, int]) -> None:
        if self.active_scene is None:
            return
        canvas_rect = self.canvas_rect()
        if not canvas_rect.collidepoint(mouse_pos):
            return

        local_mouse = pygame.Vector2(mouse_pos[0] - canvas_rect.x, mouse_pos[1] - canvas_rect.y) + self.editor.camera_offset
        selected = self.get_selected_object()
        hit_existing_handle = False
        if self.editor.tool == "move" and selected is not None and self._move_handle_hit(local_mouse):
            hit_existing_handle = True
        elif self.editor.tool == "rotate" and selected is not None and self._rotate_handle_hit(local_mouse):
            hit_existing_handle = True
        elif self.editor.tool == "scale" and selected is not None and self._scale_handle_hit(local_mouse):
            hit_existing_handle = True
        else:
            selected = self._object_at_canvas_pos(local_mouse)
        if selected is None:
            if self.editor.tool == "select":
                self.editor.selecting = True
                self.editor.selection_origin = pygame.Vector2(mouse_pos)
                self.editor.selection_current = pygame.Vector2(mouse_pos)
                if self.active_scene:
                    self.active_scene.selected_objects = []
                    self.active_scene.selected_object = None
                self.ui.mark_dirty()
            return

        if not hit_existing_handle and self.editor.tool == "select":
            self.select_object(selected)
            return

        if selected not in self.get_selected_objects():
            self.select_object(selected)
        if self.editor.tool == "select":
            return

        if self.editor.tool == "move":
            axis = self._move_handle_hit(local_mouse)
            if axis is None:
                return
            self.editor.drag_axis = axis
        elif self.editor.tool == "rotate":
            if not self._rotate_handle_hit(local_mouse):
                return
        elif self.editor.tool == "scale":
            corner = self._scale_handle_hit(local_mouse)
            if corner is None:
                return
            self.editor.drag_corner = corner

        transform = selected.get_component(Transform)
        bounds = selected.get_bounds()
        self.editor.drag_active = True
        self._begin_interaction_history()
        self.editor.drag_origin_mouse = local_mouse
        self.editor.drag_origin_position = transform.position.copy()
        self.editor.drag_origin_positions = {
            game_object: game_object.get_component(Transform).position.copy()
            for game_object in self.get_selected_objects()
        }
        self.editor.drag_origin_scale = transform.scale.copy()
        self.editor.drag_origin_rotation = transform.rotation
        self.editor.drag_center = pygame.Vector2(bounds.center)
        self.editor.drag_origin_bounds_size = pygame.Vector2(bounds.size)
        self.editor.drag_origin_angle = (local_mouse - self.editor.drag_center).as_polar()[1]
        corner_anchors = {
            "top_left": pygame.Vector2(bounds.right, bounds.bottom),
            "top_right": pygame.Vector2(bounds.left, bounds.bottom),
            "bottom_left": pygame.Vector2(bounds.right, bounds.top),
            "bottom_right": pygame.Vector2(bounds.left, bounds.top),
        }
        if self.editor.drag_corner in corner_anchors:
            self.editor.drag_anchor = corner_anchors[self.editor.drag_corner]

    def _begin_pan(self, mouse_pos: tuple[int, int]) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        if not self.canvas_rect().collidepoint(mouse_pos):
            return
        self._begin_interaction_history()
        self.editor.panning = True
        self.editor.pan_origin_mouse = pygame.Vector2(mouse_pos)
        self.editor.pan_origin_offset = self.editor.camera_offset.copy()

    def _object_at_canvas_pos(self, local_pos: pygame.Vector2) -> GameObject | None:
        if self.active_scene is None:
            return None
        for game_object in reversed(self.active_scene.game_objects):
            if game_object.get_bounds().collidepoint(local_pos):
                return game_object
        return None

    def _finish_selection_box(self) -> None:
        if self.active_scene is None:
            return
        rect = pygame.Rect(
            int(self.editor.selection_origin.x),
            int(self.editor.selection_origin.y),
            int(self.editor.selection_current.x - self.editor.selection_origin.x),
            int(self.editor.selection_current.y - self.editor.selection_origin.y),
        )
        rect.normalize()
        canvas_rect = self.canvas_rect()
        selected_objects: list[GameObject] = []
        for game_object in self.active_scene.game_objects:
            screen_bounds = game_object.get_bounds().move(-self.editor.camera_offset.x + canvas_rect.x, -self.editor.camera_offset.y + canvas_rect.y)
            if rect.colliderect(screen_bounds):
                selected_objects.append(game_object)

        self.editor.selecting = False
        self.active_scene.selected_objects = selected_objects
        self.active_scene.selected_object = selected_objects[-1] if selected_objects else None
        self.ui.mark_dirty()

    def _open_context_menu(self, mouse_pos: tuple[int, int]) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return

        self.ui.refresh(self.active_scene, self.editor)

        hierarchy_rect = self.ui.hierarchy_rect()
        inspector_rect = self.ui.inspector_rect()
        canvas_rect = self.canvas_rect()

        if hierarchy_rect.collidepoint(mouse_pos):
            target = self.ui.object_at(mouse_pos)
            if target:
                self.select_object(target)
                entries = [("Add Object", "object_add"), ("Duplicate Object", "object_duplicate"), ("Delete Object", "object_delete")]
            else:
                entries = [("Add Object", "object_add")]
            self.ui.show_context_menu(mouse_pos, entries)
            return

        if inspector_rect.collidepoint(mouse_pos):
            component_index = self.ui.component_at(mouse_pos)
            if component_index is not None:
                self.select_component(component_index)
            entries = [
                ("Add Sprite", "component_add_sprite"),
                ("Add Collider", "component_add_collider"),
                ("Add LuaScript", "component_add_lua"),
                ("Duplicate Component", "component_duplicate"),
                ("Delete Component", "component_delete"),
            ]
            self.ui.show_context_menu(mouse_pos, entries)
            return

        if canvas_rect.collidepoint(mouse_pos):
            local_pos = pygame.Vector2(mouse_pos[0] - canvas_rect.x, mouse_pos[1] - canvas_rect.y) + self.editor.camera_offset
            target = self._object_at_canvas_pos(local_pos)
            if target:
                self.select_object(target)
                entries = [("Add Object", "object_add"), ("Duplicate Object", "object_duplicate"), ("Delete Object", "object_delete")]
            else:
                entries = [("Add Object", "object_add")]
            self.ui.show_context_menu(mouse_pos, entries)
            return

        self.ui.close_context_menu()

    def handle_context_action(self, action: str) -> None:
        if action == "object_add":
            self.create_empty_object()
        elif action == "object_duplicate":
            self.duplicate_selected_object()
        elif action == "object_delete":
            self.delete_selected_object()
        elif action == "component_add_sprite":
            self.add_component_to_selected("Sprite")
        elif action == "component_add_collider":
            self.add_component_to_selected("Collider")
        elif action == "component_add_lua":
            self.add_component_to_selected("LuaScript")
        elif action == "component_duplicate":
            self.duplicate_selected_component()
        elif action == "component_delete":
            self.delete_selected_component()

    def _render(self, dt: float) -> None:
        if self.active_scene is None:
            return

        canvas_rect = self.canvas_rect()
        self.screen.fill(WINDOW_BG)
        self.ui.draw_chrome(self.screen, self.active_scene, self.editor)
        canvas = self.screen.subsurface(canvas_rect)
        canvas.fill(CANVAS_BG)
        self.render_context.set_surface(canvas)
        self.render_context.set_camera_offset(self.editor.camera_offset)
        self.active_scene.draw(canvas)
        if not self.editor.is_playing:
            self._draw_editor_overlay(canvas)

        self.ui.refresh(self.active_scene, self.editor)
        self.ui.update(dt)
        self.ui.draw(self.screen)
        self.ui.draw_selection_marquee(self.screen, self.editor)
        pygame.display.flip()

    def _draw_editor_overlay(self, surface: pygame.Surface) -> None:
        selected = self.get_selected_object()
        if selected is None:
            return
        for game_object in self.get_selected_objects():
            bounds = game_object.get_bounds()
            screen_bounds = bounds.move(-self.editor.camera_offset.x, -self.editor.camera_offset.y)
            pygame.draw.rect(surface, UI_TEXT if game_object is selected else UI_ACCENT, screen_bounds.inflate(8, 8), width=2)

        bounds = selected.get_bounds()
        screen_bounds = bounds.move(-self.editor.camera_offset.x, -self.editor.camera_offset.y)

        transform = selected.get_component(Transform)
        center = pygame.Vector2(screen_bounds.centerx, screen_bounds.centery)
        if self.editor.tool == "move":
            pygame.draw.circle(surface, pygame.Color("#e2e8f0"), (int(center.x), int(center.y)), 7)
            pygame.draw.line(surface, pygame.Color("#38bdf8"), center, (center.x + 60, center.y), 4)
            pygame.draw.line(surface, pygame.Color("#22c55e"), center, (center.x, center.y - 60), 4)
            pygame.draw.circle(surface, pygame.Color("#38bdf8"), (int(center.x + 60), int(center.y)), 6)
            pygame.draw.circle(surface, pygame.Color("#22c55e"), (int(center.x), int(center.y - 60)), 6)
        elif self.editor.tool == "rotate":
            pygame.draw.circle(surface, pygame.Color("#f59e0b"), (int(center.x), int(center.y)), 42, 3)
            pygame.draw.circle(surface, pygame.Color("#f59e0b"), (int(center.x + 42), int(center.y)), 6)
        elif self.editor.tool == "scale":
            pygame.draw.rect(surface, pygame.Color("#a855f7"), screen_bounds.inflate(18, 18), width=2)
            for corner in ((screen_bounds.left, screen_bounds.top), (screen_bounds.right, screen_bounds.top), (screen_bounds.left, screen_bounds.bottom), (screen_bounds.right, screen_bounds.bottom)):
                handle_rect = pygame.Rect(0, 0, 12, 12)
                handle_rect.center = corner
                pygame.draw.rect(surface, pygame.Color("#a855f7"), handle_rect)

        font = pygame.font.SysFont("consolas", 16)
        text = font.render(
            f"{selected.name} | pos=({transform.position.x:.0f},{transform.position.y:.0f}) rot={transform.rotation:.0f} scale={transform.scale.x:.2f} cam=({self.editor.camera_offset.x:.0f},{self.editor.camera_offset.y:.0f})",
            True,
            pygame.Color("#e2e8f0"),
        )
        surface.blit(text, (12, 12))

    def get_selected_object(self) -> GameObject | None:
        if self.active_scene is None:
            return None
        return self.active_scene.selected_object

    def get_selected_objects(self) -> list[GameObject]:
        if self.active_scene is None:
            return []
        if self.active_scene.selected_objects:
            return self.active_scene.selected_objects
        return [self.active_scene.selected_object] if self.active_scene.selected_object else []

    def select_object(self, game_object: GameObject) -> None:
        if self.active_scene is None:
            return
        self.active_scene.selected_object = game_object
        self.active_scene.selected_objects = [game_object]
        self.editor.selected_component_index = 0
        self.ui.mark_dirty()

    def select_component(self, index: int) -> None:
        selected = self.get_selected_object()
        if selected is None:
            return
        self.editor.selected_component_index = max(0, min(index, len(selected.components) - 1))
        self.ui.mark_dirty()

    def unique_object_name(self, base_name: str) -> str:
        if self.active_scene is None:
            return base_name
        existing = {game_object.name for game_object in self.active_scene.game_objects}
        if base_name not in existing:
            return base_name
        suffix = 2
        while f"{base_name} {suffix}" in existing:
            suffix += 1
        return f"{base_name} {suffix}"

    def create_empty_object(self) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        self.push_undo_state()
        game_object = self.active_scene.create_object(self.unique_object_name("GameObject"))
        transform = game_object.get_component(Transform)
        transform.position.update(80 + len(self.active_scene.game_objects) * 18, 80 + len(self.active_scene.game_objects) * 12)
        self.select_object(game_object)

    def delete_selected_object(self) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        selected_objects = self.get_selected_objects()
        if not selected_objects:
            return
        self.push_undo_state()
        for selected in list(selected_objects):
            if selected in self.active_scene.game_objects:
                self.active_scene.remove_object(selected)
        self.editor.selected_component_index = 0
        self.ui.mark_dirty()

    def duplicate_selected_object(self) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        selected_objects = self.get_selected_objects()
        if not selected_objects:
            return
        self.push_undo_state()
        clones: list[GameObject] = []
        for selected in selected_objects:
            clone = selected.clone_for_scene(self.active_scene)
            clone.name = self.unique_object_name(f"{selected.name} Copy")
            clone_transform = clone.get_component(Transform)
            clone_transform.position.x += 24
            clone_transform.position.y += 24
            self.active_scene.add_existing_object(clone)
            clones.append(clone)
        if clones:
            self.active_scene.selected_objects = clones
            self.active_scene.selected_object = clones[-1]
        self.ui.mark_dirty()

    def add_component_to_selected(self, component_name: str) -> None:
        if self.editor.is_playing:
            return
        selected = self.get_selected_object()
        if selected is None:
            return
        self.push_undo_state()

        if component_name == "Sprite":
            selected.add_component(Sprite())
        elif component_name == "Collider":
            selected.add_component(Collider())
        elif component_name == "LuaScript":
            selected.add_component(LuaScript(self, "scripts/demo_controller.lua"))
        else:
            return

        self.editor.selected_component_index = len(selected.components) - 1
        self.ui.mark_dirty()

    def delete_selected_component(self) -> None:
        if self.editor.is_playing:
            return
        selected = self.get_selected_object()
        if selected is None or not selected.components:
            return
        index = max(0, min(self.editor.selected_component_index, len(selected.components) - 1))
        component = selected.components[index]
        if isinstance(component, Transform):
            return
        self.push_undo_state()
        selected.remove_component(component)
        self.editor.selected_component_index = max(0, min(index - 1, len(selected.components) - 1))
        self.ui.mark_dirty()

    def duplicate_selected_component(self) -> None:
        if self.editor.is_playing:
            return
        selected = self.get_selected_object()
        if selected is None or not selected.components:
            return
        index = max(0, min(self.editor.selected_component_index, len(selected.components) - 1))
        component = selected.components[index]
        if isinstance(component, Transform):
            return
        self.push_undo_state()
        selected.add_component(component.clone_for(self))
        self.editor.selected_component_index = len(selected.components) - 1
        self.ui.mark_dirty()

    def make_snapshot(self) -> EditorSnapshot | None:
        if self.active_scene is None:
            return None
        return EditorSnapshot(
            scene=self.active_scene.clone_for_engine(self),
            camera_offset=self.editor.camera_offset.copy(),
        )

    def push_undo_state(self) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        snapshot = self.make_snapshot()
        if snapshot is None:
            return
        self.editor.undo_stack.append(snapshot)
        self.editor.redo_stack.clear()

    def restore_snapshot(self, snapshot: EditorSnapshot) -> None:
        self.active_scene = snapshot.scene.clone_for_engine(self)
        self.editor.camera_offset = snapshot.camera_offset.copy()
        self.editor.selected_component_index = 0
        self.editor.drag_active = False
        self.editor.drag_axis = None
        self.editor.drag_corner = None
        self.editor.panning = False
        self.editor.selecting = False
        self.editor.pending_snapshot = None
        self.editor.interaction_changed = False
        self.ui.close_context_menu()
        self.ui.mark_dirty()

    def undo(self) -> None:
        if self.editor.is_playing or not self.editor.undo_stack:
            return
        snapshot = self.editor.undo_stack.pop()
        current = self.make_snapshot()
        if current is not None:
            self.editor.redo_stack.append(current)
        self.restore_snapshot(snapshot)

    def redo(self) -> None:
        if self.editor.is_playing or not self.editor.redo_stack:
            return
        snapshot = self.editor.redo_stack.pop()
        current = self.make_snapshot()
        if current is not None:
            self.editor.undo_stack.append(current)
        self.restore_snapshot(snapshot)

    def _begin_interaction_history(self) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        if self.editor.pending_snapshot is None:
            self.editor.pending_snapshot = self.make_snapshot()
        self.editor.interaction_changed = False

    def _finish_interaction(self) -> None:
        if self.editor.pending_snapshot is not None and self.editor.interaction_changed:
            self.editor.undo_stack.append(self.editor.pending_snapshot)
            self.editor.redo_stack.clear()
        self.editor.pending_snapshot = None
        self.editor.interaction_changed = False

    def enter_play_mode(self) -> None:
        if self.active_scene is None or self.editor.is_playing:
            return
        self.ui.close_context_menu()
        self.editor.play_snapshot = self.active_scene.clone_for_engine(self)
        self.active_scene = self.active_scene.clone_for_engine(self)
        self.editor.is_playing = True
        self.editor.selected_component_index = 0
        self.ui.mark_dirty()

    def stop_play_mode(self) -> None:
        if not self.editor.is_playing:
            return
        if self.editor.play_snapshot is not None:
            self.active_scene = self.editor.play_snapshot.clone_for_engine(self)
        self.editor.play_snapshot = None
        self.editor.is_playing = False
        self.editor.selected_component_index = 0
        self.editor.drag_active = False
        self.ui.mark_dirty()
