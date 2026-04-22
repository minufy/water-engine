from __future__ import annotations

from .components import Collider, LuaScript, Sprite, Transform
from .scene import Scene


def build_demo_scene(engine) -> Scene:
    scene = Scene("SampleScene", engine)

    player = scene.create_object("Player")
    player_transform = player.get_component(Transform)
    player_transform.position.update(120, 120)
    player.add_component(Sprite(size=(72, 72), color="#22c55e"))
    player.add_component(Collider(width=72, height=72))
    player.add_component(LuaScript(engine, "scripts/demo_controller.lua"))

    wall = scene.create_object("Wall")
    wall_transform = wall.get_component(Transform)
    wall_transform.position.update(460, 220)
    wall.add_component(Sprite(size=(140, 180), color="#f59e0b"))
    wall.add_component(Collider(width=140, height=180))

    goal = scene.create_object("Goal")
    goal_transform = goal.get_component(Transform)
    goal_transform.position.update(760, 420)
    goal.add_component(Sprite(size=(96, 96), color="#ef4444"))
    goal.add_component(Collider(width=96, height=96, visible=True, is_trigger=True))

    scene.selected_object = player
    return scene
