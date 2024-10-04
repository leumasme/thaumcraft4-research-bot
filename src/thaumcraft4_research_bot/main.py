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
from thaumcraft4_research_bot.utils.grid import HexGrid
from thaumcraft4_research_bot.utils.aspects import find_all_paths_of_length_n
from thaumcraft4_research_bot.utils.colors import colors


aspect_manager = AspectManager()

def setup_image(test_mode=True):
    if test_mode:
        image = PIL.Image.open("test2.png")
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
        image.save("test.png")

    return image, window_base_coords

def analyze_image(image):
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
    inventory_aspects = find_aspects_in_frame(frame_aspects_left, pixels) + \
                        find_aspects_in_frame(frame_aspects_right, pixels)
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
            raise Exception("Bad diff y, board is probably not clean:", difference_y, coords)

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
            if any(abs(entry - y) < max(smallest_y_diff / 4, 5) for entry in valid_y_coords):
                continue
            valid_y_coords.append(y)

    valid_y_coords.sort()
    print(valid_y_coords)
    return columns, valid_y_coords, smallest_y_diff

def build_grid(columns, valid_y_coords, grid, smallest_y_diff):
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

            grid.set_value((x_index, y_index), value, (x, y))
    print("Grid is", grid.grid)

def get_aspect_icon_from_name(name):
    try:
        return PIL.Image.open(f"resources/aspects/color/{name}.png")
    except FileNotFoundError:
        print(f"!!! Could not find aspect icon for {name}")
        return PIL.Image.open("resources/aspects/mono/perditio.png")

def pathfind_and_connect_coords(grid, inventory_aspects, window_base_coords, start, end, test_mode, draw, image):
    board_path = grid.pathfind(start, end)
    print("Board Path:", board_path)

    start_aspect = grid.get_value(start)
    end_aspect = grid.get_value(end)
    element_paths = find_all_paths_of_length_n(start_aspect, end_aspect, len(board_path))
    # element_paths = aspect_manager.build_element_route(start_aspect, end_aspect, len(board_path) - 2)

    if not element_paths:
        print(
            "!!! Found no element paths between",
            start_aspect,
            "and",
            end_aspect,
            "in length",
            len(board_path),
        )
        return

    selected_element_path = element_paths[0]
    print("Element Path:", selected_element_path)

    for board_coord, element in zip(board_path[1:-1], selected_element_path[1:-1]):
        inventory_location = next(
            (loc for loc, name in inventory_aspects if name == element), None
        )
        if inventory_location is None:
            print("Could not find aspect", element, "in", inventory_aspects)
            continue

        invX, invY = add_offset(
            window_base_coords, get_center_of_box(inventory_location)
        )
        boardX, boardY = add_offset(
            window_base_coords, grid.get_pixel_location(board_coord)
        )

        if test_mode:
            color = image.getpixel((invX-5, invY - 5))
            draw.line((invX, invY, boardX, boardY), fill=color, width=2)
            icon = get_aspect_icon_from_name(element)
            icon_width, icon_height = icon.size
            image.paste(icon, (boardX - icon_width // 2, boardY - icon_height // 2), icon)
            image.paste(icon, (invX - icon_width // 2, invY - icon_height // 2), icon)

        else:
            gui.moveTo(invX, invY)
            sleep(0.1)
            gui.dragTo(boardX, boardY)
            sleep(0.1)

def main():
    test_mode = True
    image, window_base_coords = setup_image(test_mode)
    draw = ImageDraw.Draw(image)

    board_aspects, empty_hexagons, inventory_aspects = analyze_image(image)
    columns, valid_y_coords, smallest_y_diff = group_hexagons(empty_hexagons, board_aspects, image.height)

    grid = HexGrid()
    build_grid(columns, valid_y_coords, grid, smallest_y_diff)
    # print("Start neighbors:", grid.get_neighbors((0, 11)))
    # print all aspects from grid that are bot free and save a list of them
    start_aspects = []
    for (grid_x, grid_y), (name, (img_x, img_y)) in grid.grid.items():
        if name != "Free":
            start_aspects.append((grid_x, grid_y))
    # pprint(start_aspects)
    # paths_to_connect so that they create a loop
    # {name+i: (name, (grid_x, grid_y)} that are not free
    start_aspects_dict = {}
    # key is (grid_x,grid_y) value is (name, (display_x, display_y))
    for i, ((grid_x, grid_y), (name, (img_x, img_y))) in enumerate(grid.grid.items()):
        if name != "Free" and name != "Missing":
            start_aspects_dict[f"{name}_{i}"] = (grid_x, grid_y)
    pprint(start_aspects_dict)
    # return
    paths_to_connect = []
    for i in range(len(start_aspects)):
        if i == 1: break
        paths_to_connect.append((start_aspects[i], start_aspects[(i+1)%len(start_aspects)]))
    print(paths_to_connect)
    # # create paths_to_connect, list of all combinations of start_aspects
    # paths_to_connect = list(itertools.combinations(start_aspects, 2))
    # print("A")
    # print(paths_to_connect)
    # create len(start_aspects) -1 paths_to_connect
    # paths_to_connect = []
    # for i in range(len(start_aspects)):
    #     for j in range(i + 1, len(start_aspects)):
    #         paths_to_connect.append((start_aspects[i], start_aspects[j]))
    # print(paths_to_connect)

    # Define the paths to connect
    # paths_to_connect = [
    #     ((0, 11), (1, 2)),
    #     ((1, 2), (6, 1)),
    #     ((6, 1), (8, 7)),
    #     ((8, 7), (5, 14)),
    #     ((5, 14), (0, 11))
    # ]
    # paths_to_connect = [
    #     ((0, 6), (2, 0)),
    #     ((1, 2), (6, 1)),
    #     ((6, 1), (8, 7)),
    #     ((8, 7), (5, 14)),
    #     ((5, 14), (0, 11))
    # ]
    # paths_to_connect = [((0, 6), (2, 0))]

    for start, end in paths_to_connect:
        try:
            pathfind_and_connect_coords(
                grid, inventory_aspects, window_base_coords, start, end, test_mode, draw, image
            )
        except Exception as e:
            print(e)

    for (grid_x, grid_y), (name, (img_x, img_y)) in grid.grid.items():
        draw.text((img_x, img_y), f"{grid_x}/{grid_y}")

    image.save("debug_test22.png")

if __name__ == "__main__":
    main()

def test_element_list():
    elements = pathlib.Path("resources/aspects/color").glob("*.png")
    elements = [e.stem for e in elements]
    for color in colors.keys():
        if color not in elements:
            print(color)


def test_aspect():
    aspect = Aspect("aer")
    # print(aspect)
    aspect_manager = AspectManager()


    route_t = find_all_paths_of_length_n("tabernus", "alienis", 5)
    route_r = aspect_manager.build_element_route("tabernus", "alienis", 3)
    # pprint(route_t)
    # pprint(route_r)
    for path in route_t:
        print(path, aspect_manager.validate_element_route(path))
    print("-"*100)
    for path in route_r:
        print(path, aspect_manager.validate_element_route(path))
