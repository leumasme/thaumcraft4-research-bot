from thaumcraft4_research_bot.utils.grid import HexGrid, SolvingHexGrid
from typing import Tuple


def solve(grid: HexGrid, start_aspects: list[Tuple[int, int]]) -> SolvingHexGrid:
    solving = SolvingHexGrid.from_hexgrid(grid)

    # create paths_to_connect by finding the 2 closest neighbors of each aspect via pathfinding.
    closest_neighbors = {}
    for start_aspect in start_aspects:
        neigh_paths = []  # How far is it to each of the other aspects?
        for other in start_aspects:
            if other == start_aspect:
                continue
            # try:
            neigh_paths.append((other, len(solving.pathfind_board_shortest(start_aspect, other))))
            # except:
            #     print("Pathfind from", start_aspect, "to", other, "failed")
            #     continue
        # Take closest 2 other aspects and store
        neigh_paths.sort(key=lambda x: x[1])
        if len(neigh_paths) < 2:
            raise Exception("Could not find 2 neighbors for", start_aspect, solving.grid)

        closest_neighbors[start_aspect] = neigh_paths[:2]

    print("Closest neighbors:", closest_neighbors)

    nodes_to_connect = []
    seen_hexes = set()
    current_start = start_aspects[1] # change index to change rotation
    while True:
        seen_hexes.add(current_start)
        neigh_a, neigh_b = closest_neighbors[current_start]
        if neigh_a[0] not in seen_hexes:
            nodes_to_connect.append((current_start, neigh_a[0]))
            current_start = neigh_a[0]
        elif neigh_b[0] not in seen_hexes:
            nodes_to_connect.append((current_start, neigh_b[0]))
            current_start = neigh_b[0]
        else:
            break


    all_paths = []
    path_indices = []
    index = 0 # write head

    print("Let's go backtracking!")

    while index < len(nodes_to_connect):
        start, end = nodes_to_connect[index]

        try: 
            board_paths, element_path = solving.pathfind_both_and_update_grid(start, end)
            all_paths.append(board_paths)
            # all_paths[index] = solving.pathfind_both_and_update_grid(start, end)
            path_indices.append(0)
            # path_indices[index] = 0
            index += 1

        except:
            print("LET'S BACKTRACK")
            if path_indices[index - 1] == len(all_paths[index - 1]) - 1:
                # No more paths to try for this one, backtrack
                index -= 1
                if index == 0:
                    # raise Exception("No more paths to try in backtracking")
                    print("No more paths to try in backtracking")
                    return solving

                path_indices.pop()
                solving.applied_paths.pop()
                print("Pop, Applied paths is now", solving.applied_paths)

            path_indices[index - 1] += 1
            element_path, _ = list(zip(*solving.applied_paths[index - 1]))
            solving.applied_paths[index - 1] = list(zip(element_path, all_paths[index - 1][path_indices[index - 1]]))
            print("Set, Applied paths is now", solving.applied_paths)
            print("Was zipping", element_path, "with", all_paths[index - 1][path_indices[index - 1]])




    # for start, end in nodes_to_connect:
    #     solving.pathfind_both_and_update_grid(start, end)
    #     print("Outer Applied paths is now", solving.applied_paths)

    return solving
