import pyautogui as gui
from time import sleep
from PIL import ImageDraw

# local libs
from window import *
from finder import *

window = getGame()

if not window.isActive:
    window.activate()
    sleep(1)

if not window.isMaximized:
    window.moveTo(10, 10)
    sleep(1)
    window.maximize()
    sleep(1)

image = screenshotWindow(window)

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

columns = list()

for _, coords in grouped_items:
    coords.sort(key=lambda c: c[1])
    
    # If we have only one coord, we cant calculate the difference between coords
    if len(coords) == 1:
        column.append(coords[0])
        continue

    difference_y = min(
        abs(coords[i + 1][1] - coords[i][1]) for i in range(len(coords) - 1)
    )
    column = list([coords[0]])
    for i in range(len(coords) - 1):
        curr_diff = coords[i + 1][1] - column[-1][1]
        print("Curr diff vs expected is", curr_diff, difference_y)
        while curr_diff > 1.5 * difference_y:
            column.append([coords[i][0], coords[i][1] + difference_y, "Missing"])
            curr_diff -= difference_y
        column.append(coords[i + 1])
    print(column)
    columns.append(column)

(min_x, min_y, max_x, max_y) = frame_aspects_left
print(min_x, min_y, max_x, max_y)

draw = ImageDraw.Draw(image)

draw.rectangle(xy=(min_x, min_y, max_x, max_y), outline=(0, 255, 0))

image.save("test.png")
