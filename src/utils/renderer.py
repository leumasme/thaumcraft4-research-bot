from PIL import ImageDraw
import PIL.Image
from typing import Tuple, List

from ..utils.grid import HexGrid
from ..utils.finder import get_center_of_box
from ..utils.colors import aspect_colors
from ..utils.log import log

def get_aspect_icon_from_name(name):
    try:
        return PIL.Image.open(f"resources/aspects/color/{name}.png")
    except FileNotFoundError:
        log.warning(f"Could not find aspect icon for {name}")
        return PIL.Image.open("resources/aspects/mono/perditio.png")


def draw_board_coords(grid, draw: ImageDraw.ImageDraw):
    for (grid_x, grid_y), (name, (img_x, img_y)) in grid.grid.items():
        color = (200, 0, 0) if name == "Missing" else (0, 200, 0)
        draw.text((img_x, img_y), f"{grid_x}/{grid_y}", fill=color)

    return


def draw_board_path(
    image: PIL.Image.Image,
    grid: HexGrid,
    merged_path: List[Tuple[str, Tuple[int, int]]],
):
    for aspect, board_coord in merged_path:
        boardImgX, boardImgY = grid.get_pixel_location(board_coord)

        icon = get_aspect_icon_from_name(aspect)
        icon_width, icon_height = icon.size
        # todo corpus is broken
        try:
            image.paste(
                icon,
                (int(boardImgX - icon_width // 2), int(boardImgY - icon_height // 2)),
                icon,
            )
        except:
            print("Failed to paste icon for", aspect, "at", boardImgX, boardImgY)


def draw_placing_hints(
    image, draw, grid, inventory_aspects, merged_path: List[Tuple[str, Tuple[int, int]]]
):
    for aspect, board_coord in merged_path:
        inventory_location = next(
            (loc for loc, name in inventory_aspects if name == aspect), None
        )
        if inventory_location is None:
            print("Could not find aspect", aspect, "in", inventory_aspects)
            continue

        inv_img_x, inv_img_y = get_center_of_box(inventory_location)
        board_img_x, board_img_y = grid.get_pixel_location(board_coord)

        color = "#"+aspect_colors[aspect]
        draw.line((inv_img_x, inv_img_y, board_img_x, board_img_y), fill=color, width=2)

        icon = get_aspect_icon_from_name(aspect)
        icon_width, icon_height = icon.size

        try:
            image.paste(icon, (inv_img_x - icon_width // 2, inv_img_y - icon_height // 2), icon)
        except Exception as e:
            log.error("Failed to draw placing hint for aspect %s at board pos %s", aspect, board_coord)