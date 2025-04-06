from typing import Set, Tuple, List
import numpy as np

from ..utils.colors import rgb_to_aspect
from ..utils.log import log

# Function to check if there are consecutive pixels of the same color in a direction
def has_consecutive_pixels(image, pixels, x, y, dx, dy):
    target_color = pixels[x, y]
    for i in range(10):
        nx, ny = x + i * dx, y + i * dy
        if (
            not (0 <= nx < image.width and 0 <= ny < image.height)
            or pixels[nx, ny] != target_color
        ):
            return False
    return True

def find_frame(image, target_color):
    try:
        return find_frame_fast(image, target_color)
    except Exception as e:
        log.error("Fast frame detection failed, falling back to slow method...")
        log.exception(e)
        return find_frame_slow(image, target_color)

def find_frame_slow(image, target_color):
    # Slower method, but may be more accurate in some cases...
    # Initialize bounding box coordinates
    left_x, top_y = 0, 0
    right_x, bottom_y = image.width, image.height
    pixels = image.load()

    # Iterate over all pixels to find the bounding box of the target color frame
    # Uses a Shrinking approach to find the INNER bounding box of the frame if its thick
    for y in range(image.height):
        for x in range(image.width):
            if pixels[x, y] == target_color:
                # Check for updating the top-left corner (min_x, min_y)
                if (
                    (x > left_x or y > top_y)
                    and has_consecutive_pixels(image, pixels, x, y, 1, 0)
                    and has_consecutive_pixels(image, pixels, x, y, 0, 1)
                ):
                    left_x, top_y = x, y

                # Check for updating the bottom-right corner (max_x, max_y)
                if (
                    (x < right_x or y < bottom_y)
                    and has_consecutive_pixels(image, pixels, x, y, -1, 0)
                    and has_consecutive_pixels(image, pixels, x, y, 0, -1)
                ):
                    right_x, bottom_y = x, y
    return (left_x, top_y, right_x, bottom_y)

def find_frame_fast(image, target_color):
    # Convert PIL image to numpy array
    img_array = np.array(image)
    
    # Doing this on all 3 channels manually is much faster than using np.all() for some reason?
    # mask = np.all(img_array == np.array(target_color), axis=2)
    r_match = img_array[:,:,0] == target_color[0]
    g_match = img_array[:,:,1] == target_color[1]
    b_match = img_array[:,:,2] == target_color[2]
    mask = r_match & g_match & b_match

    y_indices, x_indices = np.where(mask)
    min_x, max_x = np.min(x_indices), np.max(x_indices)
    min_y, max_y = np.min(y_indices), np.max(y_indices)

    # Sanity Checks. There could randomly be other pixels with the frame color that mess this up
    dx = max_x - min_x
    dy = max_y - min_y
    if dx < 10 or dy < 10:
        log.error("Frame too small, frame detection failed... x:%s-%s y:%s-%s", min_x, max_x, min_y, max_y)
        raise Exception("Frame too small, frame detection failed...")
    
    # Check all corners to ensure they actually have the right color
    if not (mask[min_y, min_x] and mask[min_y, max_x] and mask[max_y, min_x] and mask[max_y, max_x]):
        log.error("Corners of the frame do not match the target color... x:%s-%s y:%s-%s", min_x, max_x, min_y, max_y)
        raise Exception("Corners of the frame do not match the target color...")

    return (min_x, min_y, max_x, max_y)

def find_aspects_in_frame(
    frame: Tuple[int, int, int, int], pixels
) -> List[Tuple[Tuple[int, int, int, int], str]]:
    min_x, min_y, max_x, max_y = frame
    frame_bounds = (min_x, min_y, max_x, max_y)
    visited = set()
    found_aspects = []

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if (x, y) in visited:
                continue
            color = pixels[x, y]
            aspect_name = rgb_to_aspect(color)
            if aspect_name is not None:
                # Found a valid aspect pixel
                bounding_box = flood_fill(pixels, x, y, color, visited, frame_bounds)
                bb_min_x, bb_min_y, bb_max_x, bb_max_y = bounding_box
                smaller_side = min(bb_max_x - bb_min_x, bb_max_y - bb_min_y)
                # TODO: False positive on the letter color, bad fix doesn't work with larger gui size?
                if smaller_side > 8:
                    found_aspects.append((bounding_box, aspect_name))
            else:
                visited.add((x, y))

    return found_aspects


def flood_fill(
    pixels,
    x: int,
    y: int,
    target_color: Tuple[int, int, int],
    visited: Set[Tuple[int, int]],
    frame_bounds: Tuple[int, int, int, int],
) -> Tuple[int, int, int, int]:
    min_x, min_y, max_x, max_y = frame_bounds
    # Initialize the bounding box to the starting point
    min_x_bb = x
    max_x_bb = x
    min_y_bb = y
    max_y_bb = y

    stack = [(x, y)]
    visited.add((x, y))

    while stack:
        cx, cy = stack.pop()
        # Update bounding box
        min_x_bb = min(min_x_bb, cx)
        max_x_bb = max(max_x_bb, cx)
        min_y_bb = min(min_y_bb, cy)
        max_y_bb = max(max_y_bb, cy)

        # Check neighbors (4-connected)
        neighbors = [(cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)]

        for nx, ny in neighbors:
            if nx < min_x or nx > max_x or ny < min_y or ny > max_y:
                continue  # Out of frame bounds
            if (nx, ny) in visited:
                continue
            neighbor_color = pixels[nx, ny]
            if neighbor_color == target_color:
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                visited.add((nx, ny))

    return (min_x_bb, min_y_bb, max_x_bb, max_y_bb)


def find_squares_in_frame(
    frame: Tuple[int, int, int, int], pixels, target_color: Tuple[int, int, int]
) -> List[Tuple[int, int]]:
    min_x, min_y, max_x, max_y = frame
    squares = []
    squares_bounding_boxes = []

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            color = pixels[x, y]
            if color != target_color:
                continue
            # Check if this pixel is inside any of the existing squares
            in_existing_square = False
            for bbox in squares_bounding_boxes:
                bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox
                if bbox_min_x <= x <= bbox_max_x and bbox_min_y <= y <= bbox_max_y:
                    in_existing_square = True
                    break
            if in_existing_square:
                continue  # Skip pixels inside squares we've already processed
            # Find the size of the square
            size = 1
            # Find width by moving right
            while x + size <= max_x and pixels[x + size, y] == target_color:
                size += 1
            # Find height by moving down
            size_y = 1
            while y + size_y <= max_y and pixels[x, y + size_y] == target_color:
                size_y += 1
            # Take the smaller of width and height as the square size
            square_size = min(size, size_y)
            # Record the bounding box
            bbox = (x, y, x + square_size - 1, y + square_size - 1)
            squares_bounding_boxes.append(bbox)
    # Convert bounding boxes to center points using list comprehension
    squares = [
        get_center_of_box((min_x_bb, min_y_bb, max_x_bb, max_y_bb))
        for min_x_bb, min_y_bb, max_x_bb, max_y_bb in squares_bounding_boxes
    ]
    return squares


def get_center_of_box(box: Tuple[int, int, int, int]) -> Tuple[int, int]:
    min_x, min_y, max_x, max_y = box
    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2
    return (center_x, center_y)
