from thaumcraft4_research_bot.utils.grid import HexGrid
from typing import Tuple


def solve(grid: HexGrid, start_aspects: list[Tuple[int, int]]):
    # create paths_to_connect by finding the 2 closest neighbors of each aspect via pathfinding.
    closest_neighbors = {}
    for start_aspect in start_aspects:
        neigh_paths = []  # How far is it to each of the other aspects?
        for other in start_aspects:
            if other == start_aspect:
                continue
            # try:
            neigh_paths.append((other, len(grid.pathfind_board_shortest(start_aspect, other))))
            # except:
            #     print("Pathfind from", start_aspect, "to", other, "failed")
            #     continue
        # Take closest 2 other aspects and store
        neigh_paths.sort(key=lambda x: x[1])
        if len(neigh_paths) < 2:
            raise Exception("Could not find 2 neighbors for", start_aspect, grid.grid)

        closest_neighbors[start_aspect] = neigh_paths[:2]

    print("Closest neighbors:", closest_neighbors)

    paths_to_connect = []
    seen_hexes = set()
    current_start = start_aspects[0]
    while True:
        seen_hexes.add(current_start)
        neigh_a, neigh_b = closest_neighbors[current_start]
        if neigh_a[0] not in seen_hexes:
            paths_to_connect.append((current_start, neigh_a[0]))
            current_start = neigh_a[0]
        elif neigh_b[0] not in seen_hexes:
            paths_to_connect.append((current_start, neigh_b[0]))
            current_start = neigh_b[0]
        else:
            break

    for start, end in paths_to_connect:
        grid.pathfind_both_and_update_grid(start, end)
        print("Outer Applied paths is now", grid.applied_paths)
