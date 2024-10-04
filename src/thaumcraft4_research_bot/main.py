from collections import defaultdict
import itertools
from pprint import pprint
import pyautogui as gui
from time import sleep
from PIL import ImageDraw
import PIL.Image
from typing import Tuple
import pathlib

# Local libs
from thaumcraft4_research_bot.utils.aspectobj import Aspect, AspectManager
from thaumcraft4_research_bot.utils.window import *
from thaumcraft4_research_bot.utils.finder import *
from thaumcraft4_research_bot.utils.grid import HexGrid, SolvingHexGrid
from thaumcraft4_research_bot.utils.aspects import find_all_element_paths_of_length_n
from thaumcraft4_research_bot.utils.colors import aspect_colors
from thaumcraft4_research_bot.utils.solvers.ringsolver import solve as ringsolver_solve
from thaumcraft4_research_bot.utils.renderer import *
import time

aspect_manager = AspectManager()


def setup_image(test_mode=True):
    if test_mode:
        image = PIL.Image.open("debug_input.png")
        window_base_coords = (0, 0)
    else:
        window = find_game()

        if not window.isActive:
            window.activate()
            sleep(0.5)

        if not window.isMaximized:
            window.moveTo(10, 10)
            sleep(0.5)
            window.maximize()
            sleep(0.5)

        image, window_base_coords = screenshot_window(window)
        image.save("debug_input.png")

    return image, window_base_coords


def analyze_image(image: PIL.Image.Image):
    pixels = image.load()

    frame_aspects_left = find_frame(image, pixels, (100, 123, 123))
    frame_aspects_right = find_frame(image, pixels, (200, 123, 123))
    board = find_frame(image, pixels, (150, 123, 123))

    print("Aspects on board:")
    board_aspects = find_aspects_in_frame(board, pixels)
    print(board_aspects)

    print("Empty spaces on board:")
    empty_hexagons = find_squares_in_frame(board, pixels, (195, 195, 195))
    print(empty_hexagons)

    print("Aspects in inventory:")
    start_time = time.time()
    inventory_aspects = find_aspects_in_frame(
        frame_aspects_left, pixels
    ) + find_aspects_in_frame(frame_aspects_right, pixels)
    end_time = time.time()

    print(f"Time taken to find inventory aspects: {end_time - start_time} seconds")
    print(inventory_aspects)

    return board_aspects, empty_hexagons, inventory_aspects


def group_hexagons(empty_hexagons, board_aspects, image_height):
    grouped = defaultdict(list)
    for x, y in empty_hexagons:
        grouped[x].append((x, y, "Free"))

    for box_coords, name in board_aspects:
        left, top, right, bottom = box_coords
        x = int((right + left) / 2)
        y = (bottom + top) / 2

        # Merge close x coordinates
        for existing_x in grouped.keys():
            if abs(existing_x - x) <= 2:
                x = existing_x
                break
        grouped[x].append((x, y, name))

    grouped_items = sorted(grouped.items(), key=lambda e: e[0])

    columns = []
    smallest_y_diff = image_height

    for _, coords in grouped_items:
        coords.sort(key=lambda c: c[1])

        if len(coords) == 1:
            column = [coords[0]]
            columns.append(column)
            continue

        difference_y = min(
            abs(coords[i + 1][1] - coords[i][1]) for i in range(len(coords) - 1)
        )
        if smallest_y_diff > difference_y:
            smallest_y_diff = difference_y

        if difference_y < 10:
            raise Exception(
                "Bad diff y, board is probably not clean:", difference_y, coords
            )

        column = [coords[0]]
        for i in range(len(coords) - 1):
            curr_diff = coords[i + 1][1] - column[-1][1]
            print("Curr diff vs expected is", curr_diff, difference_y)
            while curr_diff > 1.5 * difference_y:
                column.append((coords[i][0], coords[i][1] + difference_y, "Missing"))
                curr_diff -= difference_y
            column.append(coords[i + 1])
        print(column)
        columns.append(column)

    print("Smallest y diff is", smallest_y_diff)
    valid_y_coords = []

    for col in columns:
        for row_entry in col:
            x, y, value = row_entry
            if any(
                abs(entry - y) < max(smallest_y_diff / 4, 5) for entry in valid_y_coords
            ):
                continue
            valid_y_coords.append(y)

    valid_y_coords.sort()
    print(valid_y_coords)
    return columns, valid_y_coords, smallest_y_diff


def build_grid(columns, valid_y_coords, grid: HexGrid, smallest_y_diff):
    for x_index, col in enumerate(columns):
        for hex in col:
            x, y, value = hex
            y_index = -1
            for index, curr_y in enumerate(valid_y_coords):
                if abs(curr_y - y) < max(smallest_y_diff / 4, 5):
                    y_index = index
                    break
            if y_index == -1:
                raise Exception("Y value failure", y, valid_y_coords)

            grid.set_hex((x_index, y_index), value, (x, y))
    print("Grid is", grid.grid)


def main():
    image, window_base_coords = setup_image(False)
    draw = ImageDraw.Draw(image)

    board_aspects, empty_hexagons, inventory_aspects = analyze_image(image)
    columns, valid_y_coords, smallest_y_diff = group_hexagons(
        empty_hexagons, board_aspects, image.height
    )

    grid = HexGrid()
    build_grid(columns, valid_y_coords, grid, smallest_y_diff)
    print("Grid:", grid.grid)

    start_aspects: list[Tuple[int, int]] = []
    for (grid_x, grid_y), (name, _) in grid.grid.items():
        if name != "Free" and name != "Missing":
            start_aspects.append((grid_x, grid_y))

    # bla = grid.pathfind_board_shortest((0, 12), (3, 15))
    # print(bla)
    # rab = grid.pathfind_board_of_length((0, 12), (3, 15), len(bla))
    # print(rab)
    
    solved: SolvingHexGrid
    # try:
    solved = ringsolver_solve(grid, start_aspects)
    # except Exception as e:
    #     print("Ringsolver failed to solve", e)

    # for path in grid.applied_paths:
    #     for aspect, coord in path[1:-1]:
    #         place_aspect_at(window_base_coords, inventory_aspects, grid, aspect, coord)

    draw_board_coords(solved, draw)
    
    print("Applied paths is", solved.applied_paths)

    for path in solved.applied_paths:
        draw_board_path(image, solved, path)
    image.save("debug_render.png")


if __name__ == "__main__":
    main()


def place_aspect_at(
    window_base_coords,
    inventory_aspects,
    grid: HexGrid,
    aspect: str,
    board_coord: Tuple[int, int],
):
    inventory_location = next(
        (loc for loc, name in inventory_aspects if name == aspect), None
    )
    if inventory_location is None:
        print("Could not find aspect", aspect, "in inventory", inventory_aspects)
        return

    invImgX, invImgY = get_center_of_box(inventory_location)
    boardImgX, boardImgY = grid.get_pixel_location(board_coord)

    invX, invY = add_offset(window_base_coords, (invImgX, invImgY))
    boardX, boardY = add_offset(window_base_coords, (boardImgX, boardImgY))

    gui.moveTo(invX, invY)
    sleep(0.1)
    gui.dragTo(boardX, boardY)
    sleep(0.1)


def test_element_list():
    elements = pathlib.Path("resources/aspects/color").glob("*.png")
    elements = [e.stem for e in elements]
    for color in aspect_colors.keys():
        if color not in elements:
            print(color)


def test_aspect():
    aspect = Aspect("aer")
    # print(aspect)
    aspect_manager = AspectManager()

    route_t = find_all_element_paths_of_length_n("tabernus", "alienis", 5)
    route_r = aspect_manager.build_element_route("tabernus", "alienis", 3)
    # pprint(route_t)
    # pprint(route_r)
    for path in route_t:
        print(path, aspect_manager.validate_element_route(path))
    print("-" * 100)
    for path in route_r:
        print(path, aspect_manager.validate_element_route(path))
