from typing import Tuple, List, Dict

from thaumcraft4_research_bot.utils.grid import HexGrid, SolvingHexGrid
from thaumcraft4_research_bot.utils.aspects import calculate_cost_of_aspect_path
from thaumcraft4_research_bot.utils.log import log

def solve(grid: HexGrid, start_aspects: List[Tuple[int, int]]) -> SolvingHexGrid:
    solving = SolvingHexGrid.from_hexgrid(grid)

    ring_solver = RingSolver(solving, start_aspects)
    return ring_solver.solve()

class RingSolver:
    solving: SolvingHexGrid
    start_aspects: List[Tuple[int, int]]

    best_solution: SolvingHexGrid = None
    best_solution_cost = 999999999 # TODO: proper placeholder value

    # (type[], (x, y)[])[][]
    # different source-destination ; different alternate paths ; different steps of path
    all_paths: List[List[Tuple[List[str], List[Tuple[int, int]]]]] = []
    path_indices: List[int] = []
    index = 0  # Path write head

    nodes_to_connect: List[Tuple[Tuple[int,int], Tuple[int, int]]]

    def __init__(self, solving: SolvingHexGrid, start_aspects: List[Tuple[int, int]]):
        self.solving = solving
        self.start_aspects = start_aspects

    def alternate_previous_path(self) -> bool:
        """ 
        :returns: True if successful, False if there are no more options to try (search is done)
        """
        if self.index == 0:
            # TODO: not an exception, handle gracefully?
            raise Exception(
                "Ringsolver failed: Pathfinding failed on very first path"
            )

        while self.path_indices[self.index - 1] == len(self.all_paths[self.index - 1]) - 1:
            result = self.backtrack_hard()
            if not result: return False

        self.path_indices[self.index - 1] += 1

        current_elem_path, current_board_path = self.all_paths[self.index - 1][
            self.path_indices[self.index - 1]
        ]
        self.solving.applied_paths[self.index - 1] = list(
            zip(current_elem_path, current_board_path)
        )

        return True
    
    def backtrack_hard(self):
        """
        :returns: False if there's nothing to backtrack to (search is done)
        """
        log.debug(
            "Pathfinding failed and no previous path alternatives left, backtracking"
        )
        # No more paths to try for this one, backtrack
        self.index -= 1

        if self.index == 0:
            # print("Done! Lowest Solution cost is", self.best_solution_cost, "at", self.total_runs)
            log.info("Done! Lowest Solution cost is %s", self.best_solution_cost)
            return False

        self.path_indices.pop()
        self.solving.applied_paths.pop()
        self.all_paths.pop()
        return True

    def find_initial_nodes_to_connect(self, ring_rotation: int) -> List[Tuple[Tuple[int,int], Tuple[int, int]]]:
        # TODO: With the connecting to any path instead of target node, it might be possible to get a non-connected mesh again?
        # No, maybe not because of the order that the nodes to connect are processed, it auto-guarantees that any existing
        # path is connected to the target node anyway...?

        if len(self.start_aspects) == 2:
            return [(self.start_aspects[0], self.start_aspects[1])]

        # create paths_to_connect by finding the 2 closest neighbors of each aspect via pathfinding.
        closest_neighbors: Dict[Tuple[int, int], List[Tuple[Tuple[int, int], int]]] = {}
        for start_aspect in self.start_aspects:
            neigh_paths = []  # How far is it to each of the other aspects?

            neigh_paths_list = self.solving.pathfind_board_shortest_to_many(
                start_aspect, self.start_aspects
            )
            neigh_paths = [(path[-1], len(path)) for path in neigh_paths_list if path]

            # Take closest 2 other aspects and store
            neigh_paths.sort(key=lambda x: x[1])
            if len(neigh_paths) < 2:
                raise Exception(
                    "Could not find 2 neighbors for", start_aspect, self.solving.grid
                )

            closest_neighbors[start_aspect] = neigh_paths[:2]

        log.debug("Closest neighbors:", closest_neighbors)

        nodes_to_connect = []
        seen_hexes = set()
        current_start = self.start_aspects[ring_rotation]

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

        # TODO: refactor so this fallback isn't needed.
        # Otherwise currently, it would be possible to build a graph that doesn't actually connect all starts
        if len(nodes_to_connect) != len(self.start_aspects) - 1:
            for aspect_loc in self.start_aspects:
                if not any(aspect_loc in conn for conn in nodes_to_connect):
                    neighbor, _ = closest_neighbors[aspect_loc][0]
                    nodes_to_connect.append((neighbor, aspect_loc))

        return nodes_to_connect

    def report_solution(self):
        assert self.index == len(self.nodes_to_connect)
        new_cost = self.solving.calculate_cost()
        log.debug("Found a solution of cost", new_cost)
        if new_cost < self.best_solution_cost:
            log.debug("Found a new best solution of cost", new_cost)
            self.best_solution = self.solving.copy()
            self.best_solution_cost = self.best_solution.calculate_cost()

    def do_solver_iteration(self) -> bool:
        """
        :returns: False if no next iteration is possible (search is done)
        """
        if self.index == len(self.nodes_to_connect):
            # Found a solution
            self.report_solution()
            return self.alternate_previous_path() # or backtrack hard?
        
        start, end = self.nodes_to_connect[self.index]

        # TODO: Also include the start/end nodes of existing placed paths
        alternative_targets = [
            coords
            for applied_path in self.solving.applied_paths
            for (_, coords) in applied_path
        ]

        # TODO: Do something with the aspect variations number
        new_paths = self.solving.pathfind_both_many(end, [start] + alternative_targets, 1)

        if len(new_paths) == 0:
            # print("No paths found for ", end, [start] + alternative_targets)
            return self.alternate_previous_path()

        new_paths.sort(
            key=lambda x: calculate_cost_of_aspect_path(x[0])
        )  # TODO: second grade sort by something else?

        self.all_paths.append(new_paths)

        initial_elem_path, initial_board_path = new_paths[0]

        self.solving.apply_path(initial_board_path, initial_elem_path)
        self.path_indices.append(0)
        self.index += 1

        return True

    def solve(self):
        # TODO: Use ring rotation?
        self.nodes_to_connect = self.find_initial_nodes_to_connect(1)

        done = False
        while not done:
            done = not self.do_solver_iteration()

        return self.best_solution
