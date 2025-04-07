from collections import defaultdict
from pathlib import Path
import pyautogui as gui
from time import sleep
from PIL import ImageDraw
import PIL.Image
from typing import Tuple
import time
import sys
import traceback

# Local libs
from thaumcraft4_research_bot.utils.window import *
from thaumcraft4_research_bot.utils.finder import *
from thaumcraft4_research_bot.utils.grid import HexGrid, SolvingHexGrid
from thaumcraft4_research_bot.utils.aspects import aspect_parents
from thaumcraft4_research_bot.utils.solvers.ringsolver import solve as ringsolver_solve
from thaumcraft4_research_bot.utils.renderer import *
from thaumcraft4_research_bot.utils.log import log

# Disable 0.1 seconds delay between each pyautogui call
gui.PAUSE = 0

# (min_x, min_y, max_x, max_y), aspect_name
type OnscreenAspect = Tuple[Tuple[int, int, int, int], str]

MODE = sys.argv[1] if len(sys.argv) > 1 else None
TEST_MODE = MODE == "test"  # Read debug_input and dont perform actions
TEST_ALL_MODE = MODE == "test_all"  # Run test for all collected test_inputs


def main():
    print("MODE=", MODE)
    if TEST_ALL_MODE:
        test_all_samples()
    else:
        normal_mode()

def normal_mode():
    inventory_aspects: list[OnscreenAspect] = None
    while True:
        image, window_base_coords = setup_image(
            TEST_MODE, inventory_aspects is not None
        )

        pixels = image.load()
        grid = generate_hexgrid_from_image(image, pixels)

        if inventory_aspects is None:
            inventory_aspects = generate_inventory_aspects_from_image(image, pixels)

        save_input_image(image, grid)

        solved = generate_solution_from_hexgrid(grid)

        for path in solved.applied_paths:
            draw_board_path(image, solved, path)

        draw = ImageDraw.Draw(image)
        draw_board_coords(solved, draw)

        image.save("debug_render.png")

        if TEST_MODE:
            break
        for path in solved.applied_paths:
            for aspect, coord in path[1:-1]:
                place_aspect_at(
                    window_base_coords, inventory_aspects, grid, aspect, coord
                )

        input("-- Press enter to process next board --")


def test_all_samples():
    test_files = list(Path("./test_inputs").glob("board_*.png"))
    print(f"Found {len(test_files)} test samples to check")

    for test_file in test_files:
        print("Testing file", test_file)
        image = PIL.Image.open(test_file)

        try:
            start_time = time.time()
            pixels = image.load()
            grid = generate_hexgrid_from_image(image, pixels)
            end_time = time.time()
        except Exception as e:
            print("Failed to parse:", traceback.format_exc())
            continue

        parse_time_ms = (end_time - start_time) * 1000

        try:
            start_time = time.time()
            solved = generate_solution_from_hexgrid(grid)
            end_time = time.time()
        except Exception as e:
            print("Failed to solve:", traceback.format_exc())
            continue

        solve_time_ms = (end_time - start_time) * 1000
        print(
            f"Solved with score {solved.calculate_cost()} in {parse_time_ms:.2f}+{solve_time_ms:.2f}ms"
        )


def setup_image(test_mode=True, skip_focus=False):
    if test_mode:
        image = PIL.Image.open("debug_input.png")
        window_base_coords = (0, 0)
    else:
        window = find_game()

        if not skip_focus:
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


def analyze_image_board(image: PIL.Image.Image, pixels):
    pixels = image.load()

    board = find_frame(image, (150, 123, 123))

    board_aspects = find_aspects_in_frame(board, pixels)
    log.debug("Aspects on board: %s", board_aspects)

    empty_hexagons = find_squares_in_frame(board, pixels, (195, 195, 195))
    log.debug("Empty spaces on board: %s", empty_hexagons)

    return board_aspects, empty_hexagons


def analyze_image_inventory(image: PIL.Image.Image, pixels):
    frame_aspects_left = find_frame(image, (100, 123, 123))
    frame_aspects_right = find_frame(image, (200, 123, 123))

    start_time = time.time()
    inventory_aspects = find_aspects_in_frame(
        frame_aspects_left, pixels
    ) + find_aspects_in_frame(frame_aspects_right, pixels)
    end_time = time.time()

    log.info(f"Time taken to find inventory aspects: {end_time - start_time} seconds")
    log.debug("Aspects in inventory: %s", inventory_aspects)

    return inventory_aspects


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
        # Sort rows by y
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
            log.debug("Curr diff vs expected is", curr_diff, difference_y)
            while curr_diff > 1.5 * difference_y:
                column.append((coords[i][0], coords[i][1] + difference_y, "Missing"))
                curr_diff -= difference_y
            column.append(coords[i + 1])
        log.debug("Generated board column: %s", column)
        columns.append(column)

    log.debug("Smallest y diff between parsed board hexagons is", smallest_y_diff)
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

    # Patch holes in valid y coords
    for i in range(len(valid_y_coords) - 1):
        if valid_y_coords[i + 1] - valid_y_coords[i] > 0.75 * smallest_y_diff:
            log.debug("Fixing Y-hole between", valid_y_coords[i], valid_y_coords[i + 1])
            valid_y_coords.append(valid_y_coords[i] + smallest_y_diff * 0.5)

    valid_y_coords.sort()
    log.debug("Valid Y coords: %s", valid_y_coords)

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

def generate_inventory_aspects_from_image(
    image: Image, pixels
) -> list[OnscreenAspect]:
    inventory_aspects = analyze_image_inventory(image, pixels)
    
    inventory_aspects = inventory_aspects
    missing = False
    for aspect, (parent_a, parent_b) in aspect_parents.items():
        if not any([name == aspect for _, name in inventory_aspects]):
            missing = True
            log.error(
                f"Missing aspect {aspect} from inventory (made from {parent_a} + {parent_b})"
            )
    if missing:
        raise Exception("Missing aspects from inventory... safety shutdown")
    
    return inventory_aspects

def generate_hexgrid_from_image(image: Image, pixels) -> HexGrid:
    board_aspects, empty_hexagons = analyze_image_board(
        image, pixels
    )
    columns, valid_y_coords, smallest_y_diff = group_hexagons(
        empty_hexagons, board_aspects, image.height
    )

    grid = HexGrid()
    build_grid(columns, valid_y_coords, grid, smallest_y_diff)
    log.debug("Grid: %s", grid.grid)

    return grid


def generate_solution_from_hexgrid(grid: HexGrid) -> SolvingHexGrid:
    start_aspects: list[Tuple[int, int]] = []
    for (grid_x, grid_y), (name, _) in grid.grid.items():
        if name != "Free" and name != "Missing":
            start_aspects.append((grid_x, grid_y))

    log.debug("Starting solve computation")
    start_time = time.time()
    solved = ringsolver_solve(grid, start_aspects)
    end_time = time.time()

    log.info(f"Time taken to compute solution: {end_time - start_time} seconds")
    log.info("Total solution cost: %s", solved.calculate_cost())
    return solved


def save_input_image(image: Image, grid: HexGrid):
    board_hash = grid.hash_board()[:6]
    log.info("Saving sample image, Board hash is %s", board_hash)
    img_path = Path("./test_inputs/board_" + board_hash + ".png")
    if not img_path.exists():
        img_path.parent.mkdir(exist_ok=True)
        image.save(str(img_path))


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
        log.error("Could not find aspect %s in inventory %s", aspect, inventory_aspects)
        return

    invImgX, invImgY = get_center_of_box(inventory_location)
    boardImgX, boardImgY = grid.get_pixel_location(board_coord)

    invX, invY = add_offset(window_base_coords, (invImgX, invImgY))
    boardX, boardY = add_offset(window_base_coords, (boardImgX, boardImgY))

    gui.moveTo(invX, invY)
    sleep(0.03)
    gui.mouseDown()
    sleep(0.03)
    gui.moveTo(boardX, boardY)
    sleep(0.03)
    gui.mouseUp()
    sleep(0.03)

if __name__ == "__main__":
    main()