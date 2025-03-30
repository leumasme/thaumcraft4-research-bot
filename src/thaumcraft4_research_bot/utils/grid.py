import base64
import hashlib
import json
import time
from typing import Dict, Tuple, Optional, List
from copy import deepcopy
from thaumcraft4_research_bot.utils.aspects import aspect_costs, calculate_cost_of_aspect_path, find_all_element_paths_many

class HexGrid:
    # Grid coordinate -> Aspect, Screen Coordinate
    grid: Dict[Tuple[int, int], Tuple[str, Tuple[int, int]]]

    def __init__(self) -> None:
        self.grid = {}

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
        # todo: maybe sort neighbors by distance to center to promote going towards center?
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

    def score_distance_from_center(self, coords: List[Tuple[int, int]]) -> int:
        # Distance from center, for guiding path selection towards the center. Lower is better.
        bottom = 0
        right = 0
        for _, (x, y) in self.grid.values():
            bottom = max(bottom, y)
            right = max(right, x)
        center_x = right / 2
        center_y = bottom / 2
        total_distance = 0
        for x, y in coords:
            # y-axis is stretched 2x so we reduce its value back to match
            total_distance += abs(center_x - x) + abs(center_y - y) / 2

        return total_distance

    def pathfind_board_shortest(
        self, start: Tuple[int, int], end: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        seen = {start: (0, None)}
        queue = [start]
        while queue:
            current = queue.pop(0)

            current_distance, _ = seen[current]
            for neighbor in self.get_neighbors(current):
                if neighbor not in seen:
                    seen[neighbor] = (current_distance + 1, current)

                    # End early if we find the end node 
                    if neighbor == end:
                        queue = []
                        break

                    # Don't cross over non-free board spaces. End is already checked above.
                    if self.get_value(neighbor) == "Free":
                        queue.append(neighbor)

        if not end in seen:
            print("!!! Found no board paths")
            return None

        path = []
        step = end
        while step is not None:
            path.append(step)
            step = seen[step][1]
        path.reverse()

        # print("Found length", len(path), "board path")
        return path


    def pathfind_board_of_length(
        self, start: Tuple[int, int], end: Tuple[int, int], n: int
    ) -> List[List[Tuple[int, int]]]:
        # print("Pathfinding from", start, "to", end, "with length", n)
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

        # print("Found", len(all_paths), "paths of length", n)
        return all_paths

    def pathfind_board_shortest_to_many(
        self, start: Tuple[int, int], ends_arg: List[Tuple[int, int]]
    ):
        seen = {start: (0, None)}
        queue = [start]
        ends = set(ends_arg)

        found_paths: List[List[Tuple[int, int]]] = [None for _ in ends_arg]
        # no dict for deterministic order!
        # found_paths: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

        def resolve_path(end: Tuple[int, int]):
            path = []
            step = end
            while step is not None:
                path.append(step)
                step = seen[step][1]
            path.reverse()
            found_paths[ends_arg.index(end)] = path
            ends.remove(end)

        while queue:
            current = queue.pop(0)

            current_distance, _ = seen[current]
            for neighbor in self.get_neighbors(current):
                if neighbor not in seen:
                    seen[neighbor] = (current_distance + 1, current)

                    # End early if we find the end node 
                    if neighbor in ends:
                        resolve_path(neighbor)
                        if len(ends) == 0:
                            return found_paths
                        continue

                    # Don't cross over non-free board spaces.
                    if self.get_value(neighbor) == "Free":
                        queue.append(neighbor)

        # Didn't find all ends
        return found_paths

    # TODO: Use this?
    def pathfind_board_lengths_to_many(
        self, start: Tuple[int, int], ends_arg: List[Tuple[int, int]], n_list: List[int]
    ):
        ends = set(ends_arg)

        max_n = max(n_list)

        # Depth 3 for: Different ends, Alternative Paths, Nodes in Path
        paths_many: List[List[List[str]]] = [[] for _ in ends]

        def dfs(current_node: str, current_path: List[str]):
            for i, (curr_end, curr_n) in enumerate(zip(ends, n_list)):
                if current_node == curr_end and len(current_path) == curr_n:
                    paths_many[i].append(list(current_path))

            if len(current_path) == max_n:
                return

            for neighbor in self.get_neighbors(current_node):
                if neighbor in current_path:
                    continue

                current_path.append(neighbor)
                dfs(neighbor, current_path)
                current_path.pop()

        dfs(start, [start])

        return paths_many

    def pathfind_both_many(self, start: Tuple[int, int], ends: List[Tuple[int, int]], aspect_variations = 1):
        shortest_path_list = self.pathfind_board_shortest_to_many(start, ends)

        # would this be correctly aligned with each other?
        # end_aspects = [self.get_value(end) for end in shortest_path_dict.keys()]
        # lengths = [len(path) for path in shortest_path_dict.values()]

        shortest_paths_clean: List[List[Tuple[int, int]]] = []
        end_aspects: List[str] = []
        lengths: List[int] = []
        for i in range(len(ends)):
            if shortest_path_list[i] is None:
                # No path found
                continue
            shortest_paths_clean.append(shortest_path_list[i])
            end_aspects.append(self.get_value(ends[i]))
            lengths.append(len(shortest_path_list[i]))

        # print("Searching element paths for", self.get_value(start), "to", end_aspects, "in steps", lengths)

        start_time = time.time()
        element_paths = find_all_element_paths_many(self.get_value(start), end_aspects, lengths)
        end_time = time.time()
        # print(f"Time taken for aspect DFS: {end_time - start_time} seconds")
        # print(f"From {start} to {[path[-1] for path in shortest_paths_clean]}")


        # We need a list[tuple[List[str], List[Tuple[int, int]]]]

        all_paths: list[tuple[List[str], List[Tuple[int, int]]]] = []
        for i in range(len(end_aspects)):
            if len(element_paths[i]) == 0:
                # No element path found
                continue                

            # Consider only the cheapest element path
            # element_path = element_paths[i][0]
            # all_paths.append((element_path, shortest_paths_clean[i]))


            first_element_path = element_paths[i][0]
            best_element_paths = [first_element_path]

            best_element_path_cost = calculate_cost_of_aspect_path(first_element_path)
            for alternative_path in element_paths[i][1:]:
                if calculate_cost_of_aspect_path(alternative_path) != best_element_path_cost:
                    break
                best_element_paths.append(alternative_path)

            for element_path in best_element_paths[:aspect_variations]:
                all_paths.append((element_path, shortest_paths_clean[i]))

        # todo: extend, not just for not working but also for cost?
        return all_paths

    def hash_board(self) -> str:
        # Hashes only the "Grid Coordinate -> Aspect" part of the grid, ignoring the screen coordinates
        # Returns a filesystem-friendly hash string

        # This is stupid
        elems = [(coord, aspect) for coord, (aspect, _) in self.grid.items()]
        elems.sort()
        hash_out = hashlib.md5(json.dumps(elems).encode(), usedforsecurity=False)
        base64_str = base64.urlsafe_b64encode(hash_out.digest()).decode('ascii')
        base64_str = base64_str.rstrip("=")

        return base64_str
            

class SolvingHexGrid(HexGrid):
    applied_paths: List[List[Tuple[str, Tuple[int, int]]]]

    def __init__(self) -> None:
        super().__init__()
        self.applied_paths = []

    def apply_path(self, path: List[Tuple[int, int]], element_path: List[str]) -> None:
        self.applied_paths.append(list(zip(element_path, path)))

    def pathfind_both_and_update_grid(
        self, start: Tuple[int, int], end: Tuple[int, int]
    ):
        board_paths, element_paths = self.pathfind_both(start, end)
        if len(board_paths) == 0:
            raise Exception("No paths found", start, end)
        # Element paths are already sorted so cheapest path is first
        self.apply_path(board_paths[0], element_paths[0])
        return board_paths, element_paths[0]

    def get_value(self, coord: Tuple[int, int]) -> Optional[str]:
        # Check applied paths first
        for path in reversed(self.applied_paths):
            for element, path_coord in path:
                if path_coord == coord:
                    return element
        # Fallback to the grid
        # print("Get value for", coord, "is falling back to", super().get_value(coord))
        return super().get_value(coord)

    def get_pixel_location(self, coord: Tuple[int, int]) -> Tuple[int, int]:
        # Check applied paths first
        for path in reversed(self.applied_paths):
            for _, path_coord in path:
                if path_coord == coord:
                    return self.grid[path_coord][1]
        # Fallback to the grid
        return super().get_pixel_location(coord)

    def calculate_cost(self) -> int:
        current_sum = 0
        for path in self.applied_paths:
            for value, _ in path:
                if value in aspect_costs and aspect_costs[value] is not None:
                    current_sum += aspect_costs[value]
        return current_sum

    @classmethod
    def from_hexgrid(cls, hexgrid: HexGrid) -> "SolvingHexGrid":
        solving_hexgrid = cls()
        solving_hexgrid.grid = deepcopy(hexgrid.grid)
        return solving_hexgrid
    
    def copy(self) -> HexGrid:
        new_instance = SolvingHexGrid()
        
        # Does not need to be copied as it is not modified
        new_instance.grid = self.grid 
        
        new_instance.applied_paths = deepcopy(self.applied_paths)
        return new_instance
