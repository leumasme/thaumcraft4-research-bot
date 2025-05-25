from typing import Tuple, List, Dict

from ..utils.grid import HexGrid, SolvingHexGrid
from ..utils.aspects import calculate_cost_of_aspect_path
from ..utils.log import log

def solve(grid: HexGrid, start_aspects: List[Tuple[int, int]]) -> SolvingHexGrid:
    solving = SolvingHexGrid.from_hexgrid(grid)

    ring_solver = RingSolver(solving, start_aspects)
    return ring_solver.solve()

class RingSolver:
    solving: SolvingHexGrid
    start_aspects: List[Tuple[int, int]]

    best_solution: SolvingHexGrid
    best_solution_cost: int
    # (type[], (x, y)[])[][]
    # different source-destination ; different alternate paths ; different steps of path
    all_paths: List[List[Tuple[List[str], List[Tuple[int, int]]]]]
    path_variation_indices: List[int]
    next_path_index: int  # Path write head

    iteration_count: int

    initial_nodes: List[Tuple[int, int]]

    def __init__(self, solving: SolvingHexGrid, start_aspects: List[Tuple[int, int]]):
        self.solving = solving
        self.start_aspects = start_aspects
        self.best_solution_cost = 999999999  # TODO: proper placeholder value
        self.all_paths = []
        self.path_variation_indices = []
        self.next_path_index = 0
        self.iteration_count = 0

    def alternate_previous_path(self) -> bool:
        """
        :returns: True if successful, False if there are no more options to try (search is done)
        """
        if self.next_path_index == 0:
            # TODO: not an exception, handle gracefully?
            raise Exception("Ringsolver failed: Pathfinding failed on very first path")

        while (
            self.path_variation_indices[self.next_path_index - 1]
            == len(self.all_paths[self.next_path_index - 1]) - 1
        ):
            result = self.backtrack_hard()
            if not result:
                return False

        self.path_variation_indices[self.next_path_index - 1] += 1

        current_elem_path, current_board_path = self.all_paths[
            self.next_path_index - 1
        ][self.path_variation_indices[self.next_path_index - 1]]
        self.solving.applied_paths[self.next_path_index - 1] = list(
            zip(current_elem_path, current_board_path)
        )
        self.solving.invalidate_cache()
        return True

    def backtrack_hard(self):
        """
        :returns: False if there's nothing to backtrack to (search is done)
        """
        log.debug(
            "Pathfinding failed and no previous path alternatives left, backtracking"
        )
        # No more paths to try for this one, backtrack
        self.next_path_index -= 1

        if self.next_path_index == 0:
            # print("Done! Lowest Solution cost is", self.best_solution_cost, "at", self.total_runs)
            log.info("Done! Lowest Solution cost is %s", self.best_solution_cost)
            return False

        self.path_variation_indices.pop()
        self.solving.applied_paths.pop()
        self.all_paths.pop()
        return True

    def report_solution(self):
        new_cost = self.solving.calculate_cost()
        log.debug("Found a solution of cost %s at iteration %s", new_cost, self.iteration_count)
        if new_cost < self.best_solution_cost:
            log.debug("Found a new best solution of cost %s at iteration %s", new_cost, self.iteration_count)
            self.best_solution = self.solving.copy()
            self.best_solution_cost = self.best_solution.calculate_cost()

    def do_solver_iteration(self) -> bool:
        """
        :returns: False if no next iteration is possible (search is done)
        """
        self.iteration_count += 1
        target = self.initial_nodes[self.next_path_index]
        unconnected_nodes = self.solving.get_unconnected_filled_positions(target)

        if len(unconnected_nodes) == 0:
            # Found a solution
            self.report_solution()
            return self.alternate_previous_path()  # or backtrack hard?

        # TODO: Do something with the aspect variations number
        # new_paths = self.solving.pathfind_both_to_many(end, [start] + alternative_targets)
        new_paths = self.solving.pathfind_both_to_many(target, unconnected_nodes)

        if len(new_paths) == 0:
            # print("No paths found for ", end, [start] + alternative_targets)
            return self.alternate_previous_path()

        min_extra_length = min([len(path[0]) for path in new_paths]) - 2
        if  self.solving.calculate_cost() + min_extra_length * 1.5 >= self.best_solution_cost:
            log.debug("Skipping pathfinding for %s, cost too high, at depth %s of %s", target, self.next_path_index, len(self.initial_nodes))
            return self.alternate_previous_path()

        new_paths.sort(
            key=lambda x: calculate_cost_of_aspect_path(x[0])
        )  # TODO: second grade sort by something else?

        self.all_paths.append(new_paths)

        initial_elem_path, initial_board_path = new_paths[0]

        self.solving.apply_path(initial_board_path, initial_elem_path)
        self.path_variation_indices.append(0)
        self.next_path_index += 1

        # Invalidate cache of connected positions, as the grid has changed
        self.solving.invalidate_cache()

        return True

    def solve(self):
        # TODO: Use ring rotation?
        self.initial_nodes = [
            coord
            for (coord, aspect) in self.solving
            if aspect != "Free" and aspect != "Missing"
        ]

        done = False
        while not done:
            done = not self.do_solver_iteration()

        return self.best_solution
