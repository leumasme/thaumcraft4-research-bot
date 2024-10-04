from typing import Dict, Tuple, Optional, List
from copy import deepcopy
from collections import deque
from thaumcraft4_research_bot.utils.aspects import aspect_costs
from thaumcraft4_research_bot.utils.aspects import find_all_element_paths_of_length_n


class HexGrid:
    grid: Dict[Tuple[int, int], Tuple[str, Tuple[int, int]]]
    applied_paths: List[List[Tuple[str, Tuple[int, int]]]]

    def __init__(self) -> None:
        self.grid = {}
        self.applied_paths = []

    def set_hex(
        self, coord: Tuple[int, int], value: str, pixelCoord: Tuple[int, int]
    ) -> None:
        self.grid[coord] = (value, pixelCoord)

    def set_value(self, coord: Tuple[int, int], value: str) -> None:
        self.grid[coord] = (value, self.grid[coord][1])

    def get_value(self, coord: Tuple[int, int]) -> Optional[str]:
        return self.grid[coord][0]

    def get_pixel_location(self, coord: Tuple[int, int]) -> Tuple[int, int]:
        return self.grid[coord][1]

    def get_neighbors(self, coord: Tuple[int, int]) -> List[Tuple[int, int]]:
        q, r = coord
        neighbor_deltas = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]

        neighbors_with_values = []
        for dq, dr in neighbor_deltas:
            neighbor_coord = (q + dq, r + dr)

            if (
                neighbor_coord in self.grid
                and self.grid[neighbor_coord][0] != "Missing"
            ):
                neighbors_with_values.append(neighbor_coord)

        return neighbors_with_values

    def pathfind_board_shortest(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        print("Pathfinding from", start, "to", end)
        seen = {start: (0, None)}
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current == end:
                break

            current_distance, _ = seen[current]
            for neighbor in self.get_neighbors(current):
                if neighbor not in seen:
                    seen[neighbor] = (current_distance + 1, current)
                    queue.append(neighbor)

        path = []
        if end in seen:
            step = end
            while step is not None:
                path.append(step)
                step = seen[step][1]
            path.reverse()

            print("Found", len(path), "board paths")

            return path

        print("!!! Found no board paths", path)
        return None

    def pathfind_board_of_length(
        self, start: Tuple[int, int], end: Tuple[int, int], n: int
    ) -> List[List[Tuple[int, int]]]:
        print("Pathfinding from", start, "to", end, "with length", n)
        all_paths = []

        def dfs(current: Tuple[int, int], path: List[Tuple[int, int]]):
            if len(path) > n:
                return

            if current == end and len(path) == n:
                all_paths.append(path[:])
                return

            for neighbor in self.get_neighbors(current):
                neighbor_value = self.get_value(neighbor)
                if neighbor not in path and (
                    neighbor_value == "Free" or neighbor == end
                ):
                    path.append(neighbor)
                    dfs(neighbor, path)
                    path.pop()

        dfs(start, [start])

        print("Found", len(all_paths), "paths of length", n)
        return all_paths

    def pathfind_both(
        self, start: Tuple[int, int], end: Tuple[int, int]
    ) -> Tuple[List[List[Tuple[int, int]]], List[List[str]]]:
        # use the imported find_all_element_paths_of_length_n(start_value, end_value, desired_length) -> list[list[str]]
        # it returns a list of element paths
        # if required_length is None:

        shortest_board_path = self.pathfind_board_shortest(start, end)
        board_paths = self.pathfind_board_of_length(start, end, len(shortest_board_path))
        if len(board_paths) == 0:
            print("pathfind_both found no board paths", start, end)
            return [], []

        start_value = self.get_value(start)
        end_value = self.get_value(end)
        required_length = len(board_paths[0])

        element_paths = find_all_element_paths_of_length_n(
            start_value, end_value, required_length
        )

        while not element_paths:
            required_length += 1

            board_paths = self.pathfind_board_of_length(start, end, required_length)
            if len(board_paths) == 0:
                print("!!! When trying to extend path length, found no board paths")
                continue
            element_paths = find_all_element_paths_of_length_n(
                start_value, end_value, required_length
            )

        return board_paths, element_paths

    def apply_path(self, path: List[Tuple[int, int]], element_path: List[str]) -> None:
        for coord, element in zip(path[1:-1], element_path[1:-1]):
            self.set_value(coord, element)
        self.applied_paths.append(list(zip(element_path, path)))
        print("Applied paths is now", self.applied_paths)

    def pathfind_both_and_update_grid(
        self, start: Tuple[int, int], end: Tuple[int, int]
    ) -> None:
        board_paths, element_paths = self.pathfind_both(start, end)
        if len(board_paths) == 0:
            raise Exception("No paths found", start, end)
        # Element paths are already sorted so cheapest path is first
        self.apply_path(board_paths[0], element_paths[0])
        print("Pathfind and update grid success!")

    def calculate_total_value(self) -> int:
        current_sum = 0
        for _, (value, _) in self.grid.items():
            if value in aspect_costs and aspect_costs[value] is not None:
                current_sum += aspect_costs[value]
        return current_sum

    def copy(self) -> "HexGrid":
        return deepcopy(self)
