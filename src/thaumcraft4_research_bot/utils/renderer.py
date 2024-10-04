
from PIL import ImageDraw
import PIL.Image
from typing import Tuple, List

from thaumcraft4_research_bot.utils.grid import HexGrid
from thaumcraft4_research_bot.utils.finder import get_center_of_box
from thaumcraft4_research_bot.utils.colors import aspect_colors

def get_aspect_icon_from_name(name):
    try:
        return PIL.Image.open(f"resources/aspects/color/{name}.png")
    except FileNotFoundError:
        print(f"!!! Could not find aspect icon for {name}")
        return PIL.Image.open("resources/aspects/mono/perditio.png")

def draw_board_coords(grid, draw: ImageDraw.ImageDraw):
    for (grid_x, grid_y), (name, (img_x, img_y)) in grid.grid.items():
        color = (200, 0, 0) if name == "Missing" else (0, 200, 0)
        draw.text((img_x, img_y), f"{grid_x}/{grid_y}", fill=color)

    return

def draw_board_path(image: PIL.Image.Image, grid: HexGrid, merged_path: List[Tuple[str, Tuple[int, int]]]):
    for aspect, board_coord in merged_path:
        boardImgX, boardImgY = grid.get_pixel_location(board_coord)

        icon = get_aspect_icon_from_name(aspect)
        icon_width, icon_height = icon.size
        image.paste(
            icon, (int(boardImgX - icon_width // 2), int(boardImgY - icon_height // 2)), icon
        )

def draw_placing_hints(image, draw, grid, inventory_aspects, merged_path: List[Tuple[str, Tuple[int, int]]]):
    for aspect, board_coord in merged_path:
        inventory_location = next(
            (loc for loc, name in inventory_aspects if name == aspect), None
        )
        if inventory_location is None:
            print("Could not find aspect", aspect, "in", inventory_aspects)
            continue

        invImgX, invImgY = get_center_of_box(inventory_location)
        boardImgX, boardImgY = grid.get_pixel_location(board_coord)

        color = aspect_colors[aspect]
        draw.line((invImgX, invImgY, boardImgX, boardImgY), fill=color, width=2)

        icon = get_aspect_icon_from_name(aspect)
        icon_width, icon_height = icon.size

        image.paste(
            icon, (invImgX - icon_width // 2, invImgY - icon_height // 2), icon
        )