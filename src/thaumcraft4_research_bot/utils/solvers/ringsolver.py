from thaumcraft4_research_bot.utils.grid import HexGrid, SolvingHexGrid
from thaumcraft4_research_bot.utils.aspects import calculate_cost_of_aspect_path
from typing import Tuple, List


def solve(grid: HexGrid, start_aspects: List[Tuple[int, int]]) -> SolvingHexGrid:
    solving = SolvingHexGrid.from_hexgrid(grid)

    # create paths_to_connect by finding the 2 closest neighbors of each aspect via pathfinding.
    closest_neighbors = {}
    for start_aspect in start_aspects:
        neigh_paths = []  # How far is it to each of the other aspects?
        for other in start_aspects:
            if other == start_aspect:
                continue
            # try:
            print("Ringsolver is Pathfinding from", start_aspect, "to", other)
            neigh_paths.append(
                (other, len(solving.pathfind_board_shortest(start_aspect, other)))
            )
            # except:
            #     print("Pathfind from", start_aspect, "to", other, "failed")
            #     continue
        # Take closest 2 other aspects and store
        neigh_paths.sort(key=lambda x: x[1])
        if len(neigh_paths) < 2:
            raise Exception(
                "Could not find 2 neighbors for", start_aspect, solving.grid
            )

        closest_neighbors[start_aspect] = neigh_paths[:2]

    print("Closest neighbors:", closest_neighbors)

    nodes_to_connect = []
    seen_hexes = set()
    current_start = start_aspects[1]  # change index to change rotation
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

    # (type[], (x, y)[])[][]
    # different source-destination ; different alternate paths ; different steps of path
    all_paths: List[List[Tuple[List[Tuple[str]], List[Tuple[int, int]]]]] = []
    path_indices: List[int] = []
    index = 0  # write head

    while index < len(nodes_to_connect):
        start, end = nodes_to_connect[index]

        try:
            # todo: maybe sort board paths to push into the center?
            board_paths, element_paths = solving.pathfind_both(start, end)

            path_indices.append(0)

            new_paths = [(element_paths[0], board_path) for board_path in board_paths]

            for applied_path in solving.applied_paths:
                for _, coords in applied_path[1:-1]:
                    try:
                        # maybe could be made cheaper? maybe use bfs here? TODO: do multiple paths at once!
                        board_paths, element_paths = solving.pathfind_both(
                            coords, end
                        )  # order matters!
                        new_paths += [
                            (element_paths[0], board_path) for board_path in board_paths
                        ]

                    except:
                        continue

            new_paths.sort(
                key=lambda x: calculate_cost_of_aspect_path(x[0])
            )  # todo: second grade sort by something else?

            all_paths.append(new_paths)

            initial_elem_path, initial_board_path = new_paths[0]

            solving.apply_path(initial_board_path, initial_elem_path)
            index += 1

            # TODO: do we still want to backtrack already if no direct connection is found?
            # alternate connections may be shorter anyway. probably doesn't matter
        except:
            print("Pathfinding failed, backtracking")
            # if index < 2: # TODO: Why 2? 1 couldn't work, but that doesn't make sense
            #     raise Exception("No more paths to try in backtracking")
            #     print("No more paths to try in backtracking")
            #     return solving
            if path_indices[index - 1] == len(all_paths[index - 1]) - 1:
                # No more paths to try for this one, backtrack
                index -= 1

                path_indices.pop()
                solving.applied_paths.pop()
            path_indices[index - 1] += 1

            current_elem_path, current_board_path = all_paths[index - 1][
                path_indices[index - 1]
            ]
            solving.applied_paths[index - 1] = list(
                zip(current_elem_path, current_board_path)
            )

    return solving
