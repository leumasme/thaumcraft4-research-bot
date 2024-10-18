from thaumcraft4_research_bot.utils.grid import HexGrid, SolvingHexGrid
from thaumcraft4_research_bot.utils.aspects import calculate_cost_of_aspect_path
from typing import Tuple, List, Dict


def solve(grid: HexGrid, start_aspects: List[Tuple[int, int]]) -> SolvingHexGrid:
    solving = SolvingHexGrid.from_hexgrid(grid)

    # create paths_to_connect by finding the 2 closest neighbors of each aspect via pathfinding.
    closest_neighbors: Dict[Tuple[int, int], List[Tuple[Tuple[int, int], int]]] = {}
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
            if len(start_aspects) == 2:
                # If there's only one pair of aspects, we don't need to do this
                break
            raise Exception(
                "Could not find 2 neighbors for", start_aspect, solving.grid
            )

        closest_neighbors[start_aspect] = neigh_paths[:2]

    print("Closest neighbors:", closest_neighbors)

    nodes_to_connect = []
    seen_hexes = set()
    current_start = start_aspects[1]  # change index to change ring rotation
    if len(start_aspects) == 2:
        nodes_to_connect = [(start_aspects[0], start_aspects[1])]
    else:
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

    # TODO: refactor so this fallback isn't needed
    if len(nodes_to_connect) != len(start_aspects) - 1:
        for aspect_loc in start_aspects:
            if not any(aspect_loc in conn for conn in nodes_to_connect):
                neighbor, _ = closest_neighbors[aspect_loc][0]
                nodes_to_connect.append((neighbor, aspect_loc))

    # (type[], (x, y)[])[][]
    # different source-destination ; different alternate paths ; different steps of path
    all_paths: List[List[Tuple[List[Tuple[str]], List[Tuple[int, int]]]]] = []
    path_indices: List[int] = []
    index = 0  # write head

    while index < len(nodes_to_connect):
        start, end = nodes_to_connect[index]

        print("Ringsolver stage 2 is Pathfinding from", start, "to", end)

        board_paths: List[List[Tuple[int, int]]]
        element_paths: List[List[str]]

        board_paths, element_paths = solving.pathfind_both(start, end)

        new_paths = [(element_paths[0], board_path) for board_path in board_paths]

        for applied_path in solving.applied_paths:
            for _, coords in applied_path[1:-1]:
                # maybe could be made cheaper? maybe use bfs here? TODO: do multiple paths at once!
                board_paths, element_paths = solving.pathfind_both(
                    coords, end
                )  # order matters!
                new_paths += [
                    (element_paths[0], board_path) for board_path in board_paths
                ]


        if len(new_paths) == 0:
            print("Pathfinding failed, alternating previous path")

            if index == 0:
                raise Exception("Ringsolver failed: Pathfinding failed on very first path")

            if path_indices[index - 1] == len(all_paths[index - 1]) - 1:
                print("Pathfinding failed and no previous path alternatives left, backtracking")
                # No more paths to try for this one, backtrack
                index -= 1

                if index == 0:
                    raise Exception("Ringsolver failed: Backtracked all the way to the start")

                path_indices.pop()
                solving.applied_paths.pop()
            path_indices[index - 1] += 1
    
            current_elem_path, current_board_path = all_paths[index - 1][
                path_indices[index - 1]
            ]
            solving.applied_paths[index - 1] = list(
                zip(current_elem_path, current_board_path)
            )
            continue

        new_paths.sort(
            key=lambda x: calculate_cost_of_aspect_path(x[0])
        )  # todo: second grade sort by something else?

        all_paths.append(new_paths)

        initial_elem_path, initial_board_path = new_paths[0]

        solving.apply_path(initial_board_path, initial_elem_path)
        path_indices.append(0)
        index += 1

        print(
            f"Ringsolver applied path from {initial_board_path[0]} to {initial_board_path[-1]} : {initial_elem_path} {initial_board_path}",
        )

        # TODO: do we still want to backtrack already if no direct connection is found?
        # alternate connections may be shorter anyway. probably doesn't matter

    return solving
