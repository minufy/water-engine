import dearpygui.dearpygui as dpg
from element import Element, MeshRendererComponent, ScriptComponent, TransformComponent
from scene import Scene


scene = Scene(
    elements=[]
)
element_rows = []
component_rows = []
context_element = None
context_component = None
rename_target_element = None
selected_element = None
selected_component = None

COMPONENT_TYPES = ["Transform", "Mesh Renderer", "Script"]


def get_hovered_element():
    for item_tag, element in element_rows:
        if dpg.is_item_hovered(item_tag):
            return element
    return None


def get_hovered_component():
    for item_tag, component in component_rows:
        if dpg.is_item_hovered(item_tag):
            return component
    return None


def get_element_name(element) -> str:
    return element.name if hasattr(element, "name") else str(element)


def create_component(component_type: str):
    if component_type == "Transform":
        return TransformComponent(type_name="Transform")
    if component_type == "Mesh Renderer":
        return MeshRendererComponent(type_name="Mesh Renderer")
    if component_type == "Script":
        return ScriptComponent(type_name="Script")
    return TransformComponent(type_name="Transform")


def on_component_selected(sender, app_data, user_data) -> None:
    global selected_component
    selected_component = user_data
    refresh_inspector()


def add_component_callback() -> None:
    if selected_element is None:
        return
    component_type = dpg.get_value("component_type_combo")
    component = create_component(component_type)
    selected_element.add_component(component)
    refresh_inspector()


def remove_component_callback() -> None:
    global selected_component, context_component
    if selected_element is None or context_component is None:
        dpg.configure_item("component_context_menu", show=False)
        return
    components = getattr(selected_element, "components", [])
    if context_component in components:
        selected_element.remove_component(context_component)
    if selected_component == context_component:
        selected_component = None
    context_component = None
    dpg.configure_item("component_context_menu", show=False)
    refresh_inspector()


def close_all_context_menus() -> None:
    dpg.configure_item("hierarchy_context_menu", show=False)
    dpg.configure_item("component_context_menu", show=False)


def on_component_right_click() -> None:
    global context_component
    context_component = get_hovered_component()
    dpg.configure_item("remove_component_menu_item", enabled=context_component is not None)
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    dpg.configure_item(
        "component_context_menu",
        pos=[int(mouse_x), int(mouse_y)],
        show=True,
    )


def on_hierarchy_right_click() -> None:
    global context_element
    context_element = get_hovered_element()
    dpg.configure_item("rename_element_menu_item", enabled=context_element is not None)
    dpg.configure_item("remove_element_menu_item", enabled=context_element is not None)
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    dpg.configure_item(
        "hierarchy_context_menu",
        pos=[int(mouse_x), int(mouse_y)],
        show=True,
    )


def open_rename_element_popup_callback() -> None:
    global rename_target_element
    if context_element is None:
        dpg.configure_item("hierarchy_context_menu", show=False)
        return

    rename_target_element = context_element
    dpg.set_value("rename_element_input", get_element_name(rename_target_element))
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    dpg.configure_item(
        "rename_element_popup",
        pos=[int(mouse_x), int(mouse_y)],
        show=True,
    )
    dpg.focus_item("rename_element_input")
    dpg.configure_item("hierarchy_context_menu", show=False)


def open_rename_selected_element_callback() -> None:
    global rename_target_element
    target_element = selected_element if selected_element is not None else context_element
    if target_element is None:
        return

    rename_target_element = target_element
    dpg.set_value("rename_element_input", get_element_name(rename_target_element))
    mouse_x, mouse_y = dpg.get_mouse_pos(local=False)
    dpg.configure_item(
        "rename_element_popup",
        pos=[int(mouse_x), int(mouse_y)],
        show=True,
    )
    dpg.focus_item("rename_element_input")


def apply_rename_element_callback() -> None:
    global rename_target_element
    if rename_target_element is None:
        dpg.configure_item("rename_element_popup", show=False)
        return

    new_name = str(dpg.get_value("rename_element_input")).strip()
    if new_name and hasattr(rename_target_element, "name"):
        rename_target_element.name = new_name

    refresh_scene_elements()
    refresh_inspector()
    rename_target_element = None
    dpg.configure_item("rename_element_popup", show=False)


def cancel_rename_element_callback() -> None:
    global rename_target_element
    rename_target_element = None
    dpg.configure_item("rename_element_popup", show=False)


def is_mouse_over_any_component_row() -> bool:
    for item_tag, _ in component_rows:
        if dpg.is_item_hovered(item_tag):
            return True
    return False


def refresh_inspector() -> None:
    global selected_component, component_rows
    component_rows = []
    dpg.delete_item("inspector_content_group", children_only=True)
    if selected_element is None:
        dpg.add_text("No element selected", parent="inspector_content_group")
        selected_component = None
        return

    dpg.add_text(f"Name: {get_element_name(selected_element)}", parent="inspector_content_group")
    dpg.add_separator(parent="inspector_content_group")
    dpg.add_text("Components", parent="inspector_content_group")
    dpg.add_combo(
        items=COMPONENT_TYPES,
        default_value="Transform",
        tag="component_type_combo",
        parent="inspector_content_group",
        width=-1,
    )
    dpg.add_button(label="Add Component", callback=add_component_callback, parent="inspector_content_group")
    dpg.add_separator(parent="inspector_content_group")

    components = getattr(selected_element, "components", [])
    if not components:
        dpg.add_text("- None", parent="inspector_content_group")
        return

    if selected_component not in components:
        selected_component = None

    for index, component in enumerate(components):
        item_tag = f"component_{index}"
        component_name = getattr(component, "type_name", component.__class__.__name__)
        dpg.add_selectable(
            label=component_name,
            tag=item_tag,
            default_value=component == selected_component,
            callback=on_component_selected,
            user_data=component,
            parent="inspector_content_group",
        )
        component_rows.append((item_tag, component))


def on_element_selected(sender, app_data, user_data) -> None:
    global selected_element, selected_component
    selected_element = user_data
    selected_component = None
    refresh_inspector()


def refresh_scene_elements() -> None:
    global element_rows
    element_rows = []
    dpg.delete_item("scene_elements_group", children_only=True)
    for index, element in enumerate(scene.elements):
        item_tag = f"scene_element_{index}"
        dpg.add_selectable(
            label=get_element_name(element),
            tag=item_tag,
            parent="scene_elements_group",
            callback=on_element_selected,
            user_data=element,
        )
        element_rows.append((item_tag, element))


def add_scene_element_callback() -> None:
    scene.add_element(
        Element(
            name=f"Element {len(scene.elements) + 1}",
            components=[TransformComponent(type_name="Transform")],
        )
    )
    refresh_scene_elements()
    dpg.configure_item("hierarchy_context_menu", show=False)


def remove_scene_element_callback() -> None:
    global context_element, rename_target_element, selected_element
    if context_element is None:
        dpg.configure_item("hierarchy_context_menu", show=False)
        return
    if context_element in scene.elements:
        scene.remove_element(context_element)
        if selected_element == context_element:
            selected_element = None
        if rename_target_element == context_element:
            rename_target_element = None
    context_element = None
    refresh_scene_elements()
    refresh_inspector()
    dpg.configure_item("hierarchy_context_menu", show=False)


def on_right_click(sender, app_data) -> None:
    if app_data != dpg.mvMouseButton_Right:
        return
    if dpg.is_item_hovered("hierarchy_window"):
        close_all_context_menus()
        on_hierarchy_right_click()
        return
    if dpg.is_item_hovered("inspector_window") and is_mouse_over_any_component_row():
        close_all_context_menus()
        on_component_right_click()
        return


def on_left_click(sender, app_data) -> None:
    if app_data != dpg.mvMouseButton_Left:
        return
    if dpg.is_item_shown("hierarchy_context_menu") and not dpg.is_item_hovered("hierarchy_context_menu"):
        dpg.configure_item("hierarchy_context_menu", show=False)
    if dpg.is_item_shown("component_context_menu") and not dpg.is_item_hovered("component_context_menu"):
        dpg.configure_item("component_context_menu", show=False)


def on_f2_pressed(sender, app_data) -> None:
    if app_data != dpg.mvKey_F2:
        return
    open_rename_selected_element_callback()


def on_enter_pressed(sender, app_data) -> None:
    if app_data != dpg.mvKey_Return:
        return
    if dpg.is_item_shown("rename_element_popup"):
        apply_rename_element_callback()


def on_escape_pressed(sender, app_data) -> None:
    if app_data != dpg.mvKey_Escape:
        return
    if dpg.is_item_shown("rename_element_popup"):
        cancel_rename_element_callback()

dpg.create_context()
dpg.create_viewport(title='Water Engine', width=1000, height=700)
dpg.configure_app(docking=True, docking_space=True)
dpg.setup_dearpygui()

LEFT_PANEL_WIDTH = 280
RIGHT_PANEL_WIDTH = 320

with dpg.window(
    label="Hierarchy",
    tag="hierarchy_window",
    no_move=True,
    no_resize=True,
    no_collapse=True,
    no_close=True,
):
    dpg.add_text("Scene")
    with dpg.tree_node(label="Root"):
        dpg.add_group(tag="scene_elements_group")

with dpg.window(
    label="Hierarchy Context Menu",
    tag="hierarchy_context_menu",
    popup=True,
    show=False,
    no_title_bar=True,
    no_resize=True,
    no_move=True,
    autosize=True,
):
    dpg.add_menu_item(label="Add Element", callback=add_scene_element_callback)
    dpg.add_menu_item(
        label="Rename Element",
        tag="rename_element_menu_item",
        callback=open_rename_element_popup_callback,
        enabled=False,
    )
    dpg.add_menu_item(
        label="Remove Element",
        tag="remove_element_menu_item",
        callback=remove_scene_element_callback,
        enabled=False,
    )

with dpg.window(
    label="Rename Element",
    tag="rename_element_popup",
    popup=True,
    show=False,
    no_resize=True,
    no_move=True,
    autosize=True,
):
    dpg.add_input_text(tag="rename_element_input", width=220)
    dpg.add_button(label="Apply", callback=apply_rename_element_callback)
    dpg.add_button(label="Cancel", callback=cancel_rename_element_callback)

with dpg.window(
    label="Component Context Menu",
    tag="component_context_menu",
    popup=True,
    show=False,
    no_title_bar=True,
    no_resize=True,
    no_move=True,
    autosize=True,
):
    dpg.add_menu_item(
        label="Remove Component",
        tag="remove_component_menu_item",
        callback=remove_component_callback,
        enabled=False,
    )

with dpg.window(
    label="Viewport",
    tag="viewport_window",
    no_move=True,
    no_resize=True,
    no_collapse=True,
    no_close=True,
):
    dpg.add_text("Main content area")

with dpg.window(
    label="Inspector",
    tag="inspector_window",
    no_move=True,
    no_resize=True,
    no_collapse=True,
    no_close=True,
):
    dpg.add_group(tag="inspector_content_group")

with dpg.handler_registry():
    dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Right, callback=on_right_click)
    dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=on_left_click)

with dpg.handler_registry():
    dpg.add_key_press_handler(key=dpg.mvKey_F2, callback=on_f2_pressed)
    dpg.add_key_press_handler(key=dpg.mvKey_Return, callback=on_enter_pressed)
    dpg.add_key_press_handler(key=dpg.mvKey_Escape, callback=on_escape_pressed)

refresh_scene_elements()
refresh_inspector()

dpg.show_viewport()

# below replaces, start_dearpygui()
while dpg.is_dearpygui_running():
    client_width = dpg.get_viewport_client_width()
    client_height = dpg.get_viewport_client_height()

    dpg.set_item_pos("hierarchy_window", [0, 0])
    dpg.set_item_width("hierarchy_window", LEFT_PANEL_WIDTH)
    dpg.set_item_height("hierarchy_window", client_height)

    dpg.set_item_pos("viewport_window", [LEFT_PANEL_WIDTH, 0])
    dpg.set_item_width(
        "viewport_window",
        max(100, client_width - LEFT_PANEL_WIDTH - RIGHT_PANEL_WIDTH),
    )
    dpg.set_item_height("viewport_window", client_height)

    dpg.set_item_pos("inspector_window", [max(LEFT_PANEL_WIDTH, client_width - RIGHT_PANEL_WIDTH), 0])
    dpg.set_item_width("inspector_window", RIGHT_PANEL_WIDTH)
    dpg.set_item_height("inspector_window", client_height)

    dpg.render_dearpygui_frame()

dpg.destroy_context()