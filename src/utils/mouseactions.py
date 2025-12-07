import pyautogui as gui
from time import sleep

from .aspects import aspect_parents
from .finder import get_center_of_box
from .grid import HexGrid, Coordinate, OnscreenAspect, SolvingHexGrid
from .window import add_offset
from .log import log

def drag_mouse_from_to(window_base_coords: Coordinate, start: Coordinate, end: Coordinate):
    start_x, start_y = add_offset(window_base_coords, start)
    end_x, end_y = add_offset(window_base_coords, end)

    gui.moveTo(start_x, start_y)
    sleep(0.03)
    gui.mouseDown()
    sleep(0.03)
    gui.moveTo(end_x, end_y)
    sleep(0.03)
    gui.mouseUp()
    sleep(0.03)
    gui.moveTo(window_base_coords + (10, 10))

def place_all_aspects(window_base_coords: Coordinate, inventory_aspects: list[OnscreenAspect], solved: SolvingHexGrid):
    for path in solved.applied_paths:
        for aspect, coord in path[1:-1]:
            place_aspect_at(
                window_base_coords, inventory_aspects, solved, aspect, coord
            )

def place_aspect_at(
    window_base_coords: Coordinate,
    inventory_aspects: list[OnscreenAspect],
    grid: HexGrid,
    aspect: str,
    board_coord: Coordinate,
):
    inventory_location = next(
        (loc for loc, name in inventory_aspects if name == aspect), None
    )
    if inventory_location is None:
        log.error("Could not find aspect %s in inventory %s", aspect, inventory_aspects)
        return

    inv_img_pos = get_center_of_box(inventory_location)
    board_img_pos = grid.get_pixel_location(board_coord)

    drag_mouse_from_to(window_base_coords, inv_img_pos, board_img_pos)

def craft_missing_inventory_aspects(window_base_coords: Coordinate, inventory_aspects: list[OnscreenAspect], missing_aspects: set[str]) -> int:
    # TODO: when crafting an aspect we never had before, the screen positions of other aspects may change, which can break this!
    missing_aspects = missing_aspects.copy()
    maybe_empty_aspects = set()
    crafts = 0
    needs_next_iter = True
    while needs_next_iter:
        maybe_missing_aspects = missing_aspects.union(maybe_empty_aspects)
        needs_next_iter = False
        # Only loop through missing_aspects, not maybe_empty_aspects, as those aren't actually guaranteed to be empty
        for aspect in missing_aspects:
            parent_a, parent_b = aspect_parents[aspect]

            if parent_a in maybe_missing_aspects or parent_b in maybe_missing_aspects:
                continue

            if craft_inventory_aspect(window_base_coords, inventory_aspects, aspect):
                # The two parent aspects might be empty now, but we definitely have the child because we just crafted it.
                maybe_empty_aspects.add(parent_a)
                maybe_empty_aspects.add(parent_b)
                missing_aspects.remove(aspect)
                needs_next_iter = True
                crafts += 1
                break

    return crafts

def craft_inventory_aspect(window_base_coords: Coordinate, inventory_aspects: list[OnscreenAspect], aspect: str) -> bool:
    parent_a, parent_b = aspect_parents[aspect]

    if parent_a is None or parent_b is None:
        log.error("Missing Aspect that can't be crafted: %s", aspect)
        return False

    parent_a_pos = next((box for (box, name) in inventory_aspects if name == parent_a), None)
    parent_b_pos = next((box for (box, name) in inventory_aspects if name == parent_b), None)

    if parent_a_pos is None or parent_b_pos is None:
        log.error("Missing Parent aspects from inventory to craft %s", aspect)
        return False

    print("Crafting aspect", aspect, "from", parent_a, parent_b)
    drag_mouse_from_to(window_base_coords, get_center_of_box(parent_a_pos), get_center_of_box(parent_b_pos))

    return True