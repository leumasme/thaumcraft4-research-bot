import pyautogui as gui
from time import sleep
from PIL import ImageDraw
from typing import Tuple

# local libs
from window import *
from finder import *
from grid import HexGrid
from aspects import find_all_paths_of_length_n

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

# Define the target color to search for (R, G, B)
target_color = (255, 0, 0)  # Example: Red color

# Get pixel data
pixels = image.load()

frame_aspects_left = find_frame(image, pixels, (100, 123, 123))
frame_aspects_right = find_frame(image, pixels, (200, 123, 123))
board = find_frame(image, pixels, (150, 123, 123))

# Find aspects within each of the frames
print("Aspects on board:")
board_aspects = find_aspects_in_frame(board, pixels)
print(board_aspects)

# hexagon is rendered partially transparent
# empty_hexagons = find_squares_in_frame(board, pixels, (125, 123, 123))
print("Empty spaces on board:")
empty_hexagons = find_squares_in_frame(board, pixels, (195, 195, 195))
print(empty_hexagons)

print("Aspects in inventory:")
inventory_aspects = find_aspects_in_frame(
    frame_aspects_left, pixels
) + find_aspects_in_frame(frame_aspects_right, pixels)
print(inventory_aspects)

# group the hexagons by their x coordinate
from collections import defaultdict

grouped = defaultdict(list)
for x, y in empty_hexagons:
    grouped[x].append((x, y, "Free"))

for box_coords, name in board_aspects:
    left, top, right, bottom = box_coords
    x = int((right + left) / 2)
    y = (bottom + top) / 2

    # Check if any of the existing column-x-coords are within +-2 of x
    for existing_x in grouped.keys():
        if abs(existing_x - x) <= 2:
            x = existing_x
            break
    grouped[x].append((x, y, name))


grouped_items = list(grouped.items())
grouped_items.sort(key=lambda e: e[0])

print(grouped_items)

columns: list[list[Tuple[int, int, str]]] = list()
smallest_y_diff = image.height

for _, coords in grouped_items:
    coords.sort(key=lambda c: c[1])

    # If we have only one coord, we cant calculate the difference between coords
    if len(coords) == 1:
        column.append(coords[0])
        continue

    difference_y = min(
        abs(coords[i + 1][1] - coords[i][1]) for i in range(len(coords) - 1)
    )
    if smallest_y_diff > difference_y:
        smallest_y_diff = difference_y

    if difference_y < 10:
        print("!!!! bad diff y", difference_y, coords)

    column = list([coords[0]])
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
valid_y_coords = list()

for col in columns:
    for row_entry in col:
        x, y, value = row_entry
        skip_entry = False
        for entry in valid_y_coords:
            if abs(entry - y) < max(smallest_y_diff / 4, 5):
                skip_entry = True
                break
        if skip_entry:
            continue

        valid_y_coords.append(y)

valid_y_coords.sort()
print(valid_y_coords)

grid = HexGrid()

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

print("Start neigh:", grid.get_neighbors((0, 11)))
# raise KeyboardInterrupt()

def pathfind_and_connect_coords(start: Tuple[int, int], end: Tuple[int, int]):
    board_path = grid.pathfind(start, end)  # praecantatio, victus
    print("Board Path:", board_path)

    start_aspect = grid.get_value(start)
    end_aspect = grid.get_value(end)
    element_paths = find_all_paths_of_length_n(start_aspect, end_aspect, len(board_path))

    if len(element_paths) == 0:
        print("!!! Found no element paths between", start_aspect, "and", end_aspect, "in length", len(board_path))

    selected_element_path = element_paths[0]
    print("Element Path:", selected_element_path)

    for boaard_coord, element in list(zip(board_path, selected_element_path))[1:-1]:
        inventory_location = next((loc for loc, name in inventory_aspects if name == element), None)
        if inventory_location == None:
            print("Couldnt find aspect", element, "in", inventory_aspects)

        invX, invY = add_offset(window_base_coords, get_center_of_box(inventory_location))
        gui.moveTo(invX, invY)
        sleep(0.1)
        boardX, boardY = add_offset(window_base_coords, grid.get_pixel_location(boaard_coord))
        gui.dragTo(boardX, boardY)
        sleep(0.1)

pathfind_and_connect_coords((0, 11), (1, 2))
pathfind_and_connect_coords((1, 2), (6, 1))
pathfind_and_connect_coords((6, 1), (8, 7))
pathfind_and_connect_coords((8, 7), (5, 14))
pathfind_and_connect_coords((5, 14), (0, 11))


draw = ImageDraw.Draw(image)

for (grid_x, grid_y), (name, (img_x, img_y)) in grid.grid.items():
    draw.text((img_x, img_y), str(grid_x)+"/"+str(grid_y))

image.save("test.png")
