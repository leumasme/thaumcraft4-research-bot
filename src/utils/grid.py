import base64
import hashlib
import json
import itertools
from functools import lru_cache
from typing import Dict, Tuple, Optional, List
from copy import deepcopy

from ..utils.aspects import aspect_costs, find_cheapest_element_paths_many 
from ..utils.log import log
from ..utils.aspects import aspect_graph

type Coordinate = Tuple[int, int]

class HexGrid:
    # Grid coordinate -> Aspect, Screen Coordinate
    grid: Dict[Tuple[int, int], Tuple[str, Tuple[int, int]]]
    connected_positions_cache: List[set[tuple[int, int]]]

    def __init__(self) -> None:
        self.grid = {}
        self.connected_positions_cache = list()

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

    @staticmethod
    @lru_cache(maxsize=1000)
    def calculate_distance(start: Coordinate, end: Coordinate) -> int:
        # Very good resource: https://www.redblobgames.com/grids/hexagons/#distances
        # We use "Doubled coordinates" (doubleheight) with y being the height
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        return dx + max(0, (dy - dx) // 2)

    @lru_cache(maxsize=1000)
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
            log.error("!!! Found no board paths")
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

    def pathfind_board_lengths_to_many(
        self, start: Coordinate, ends: List[Coordinate], n_list: List[int]
    ):
        # Depth 3 for: Different ends, Alternative Paths, Nodes in Path
        paths_many: List[List[List[Coordinate]]] = [[] for _ in ends]

        # Pre-compute info needed to check if a path is complete
        # Faster as a dictionary lookup than looping through the zip every time
        end_to_info = {end: (i, n) for i, (end, n) in enumerate(zip(ends, n_list))}

        # Stack entries: (current_node, current_path)
        stack = [(start, [start])]

        while stack:
            current_node, current_path = stack.pop()

            # Check if we can reach any end from current position (pruning optimization)
            can_reach_any = False
            for i, end in enumerate(ends):
                distance = HexGrid.calculate_distance(current_node, end)
                if distance <= n_list[i] - len(current_path):
                    can_reach_any = True
                    break
            if not can_reach_any:
                continue

            for neighbor in self.get_neighbors(current_node):
                if neighbor in current_path:
                    continue

                # Create new path with neighbor added
                new_path = current_path + [neighbor]

                # Check if we've reached any end with correct length
                if neighbor in end_to_info:
                    i, curr_n = end_to_info[neighbor]
                    if len(new_path) == curr_n:
                        paths_many[i].append(list(new_path))

                # Don't cross over non-free board spaces.
                # Stepping on the occupied end space is allowed, but that is already checked above.
                neighbor_value = self.get_value(neighbor)
                if neighbor_value == "Free":
                    stack.append((neighbor, new_path))

        return paths_many

    def pathfind_both_lengths_to_many(self, start: Coordinate, ends: List[Coordinate], lengths: List[int], aspect_variations = 1, board_variations = 1) -> List[tuple[List[str], List[Coordinate]]]:
        assert len(lengths) == len(ends), "Lengths and ends must be the same length"
        assert len(ends) > 0, "Must have at least one end"
        end_aspects = [self.get_value(end) for end in ends]
        element_paths = find_cheapest_element_paths_many(self.get_value(start), end_aspects, lengths)

        board_paths = self.pathfind_board_lengths_to_many(start, ends, lengths)

        valid_path_combinations: list[tuple[List[str], List[Coordinate]]] = []
        for i in range(len(lengths)):
            combinations = itertools.product(element_paths[i][:aspect_variations], board_paths[i][:board_variations])
            valid_path_combinations.extend(combinations)
    
        return valid_path_combinations

    def pathfind_both_to_many(self, start: Tuple[int, int], ends: List[Tuple[int, int]]) -> List[tuple[List[str], List[Coordinate]]]:
        assert len(ends) > 0, "Must have at least one end"
        shortest_path_list = self.pathfind_board_shortest_to_many(start, ends)

        reachable_ends: List[Tuple[int, int]] = []
        shortest_paths_clean: List[List[Tuple[int, int]]] = []
        for i in range(len(ends)):
            if shortest_path_list[i] is None:
                # No path found
                continue
            shortest_paths_clean.append(shortest_path_list[i])
            reachable_ends.append(ends[i])
        lengths = [len(path) for path in shortest_paths_clean]

        if len(reachable_ends) == 0:
            # None of the ends is even reachable on the board at all
            return []

        paths = self.pathfind_both_lengths_to_many(start, reachable_ends, lengths)

        if len(paths) < 10:
            lengths_plus_one = [length + 1 for length in lengths]
            paths.extend(self.pathfind_both_lengths_to_many(start, reachable_ends, lengths_plus_one))

        return paths
    
    def _populate_connected_positions_cache(self, start: Coordinate) -> set[Coordinate]:
        visited: set[Coordinate] = set()
        queue = [start]

        while queue:
            current = queue.pop(0)
            visited.add(current)

            for neighbor in self.get_neighbors(current):
                # Is the current aspect connectable to the neighbor aspect?
                if neighbor not in visited and self.get_value(neighbor) in aspect_graph[self.get_value(current)]:
                    queue.append(neighbor)

        self.connected_positions_cache.append(visited)
        return visited
    
    def get_connected_positions(self, start: Coordinate) -> set[Coordinate]:
        # Check if the start coordinate is already in the cache
        for connected_set in self.connected_positions_cache:
            if start in connected_set:
                return connected_set

        # If not, populate the cache and return the connected positions
        return self._populate_connected_positions_cache(start)

    def are_positions_connected(self, start: Coordinate, end: Coordinate) -> bool:
        # Check if the start and end coordinates are connected by a path of aspects which may connect to each other
        for connected_set in self.connected_positions_cache:
            if start in connected_set or end in connected_set:
                return start in connected_set and end in connected_set

        reachable = self._populate_connected_positions_cache(start)
        return end in reachable
    
    def get_unconnected_filled_positions(self, target: Coordinate) -> List[Coordinate]:
        return [
            coord
            for (coord, aspect) in self
            if not self.are_positions_connected(target, coord)
            and aspect != "Free"
            and aspect != "Missing"
        ]

    def invalidate_cache(self) -> None:
        # Invalidate the cache of connected positions, for use when the grid changes (via SolvingHexGrid)
        self.connected_positions_cache = []

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
    
    def __iter__(self):
        return HexGridIterator(self)
            

class SolvingHexGrid(HexGrid):
    applied_paths: List[List[Tuple[str, Tuple[int, int]]]]
    _grid_cache: Dict[Tuple[int, int], str]

    def __init__(self) -> None:
        super().__init__()
        self.applied_paths = []
        self._grid_cache = None

    def invalidate_cache(self):
        self._grid_cache = None
        return super().invalidate_cache()

    def apply_path(self, path: List[Tuple[int, int]], element_path: List[str]) -> None:
        self.applied_paths.append(list(zip(element_path, path)))
        self.invalidate_cache()

    def get_value(self, coord: Tuple[int, int]) -> Optional[str]:
        if self._grid_cache is None:
            # Load base state from the underlying HexGrid
            self._grid_cache = {coord: aspect for coord, (aspect, _) in self.grid.items()}
            # Add paths
            for path in self.applied_paths:
                for element, path_coord in path:
                    self._grid_cache[path_coord] = element
        
        return self._grid_cache[coord]

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

class HexGridIterator:
    def __init__(self, hexgrid: HexGrid):
        self.hexgrid = hexgrid
        self.coordinates = list(hexgrid.grid.keys())
        self.index = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.index >= len(self.coordinates):
            raise StopIteration
        
        coord = self.coordinates[self.index]
        # Use get_value instead of the .grid values so this also works with SolvingHexGrid
        value = self.hexgrid.get_value(coord)
        self.index += 1
        return (coord, value)
