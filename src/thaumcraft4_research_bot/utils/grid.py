from typing import Dict, Tuple, Optional, List


class HexGrid:
    grid: Dict[Tuple[int, int], Tuple[Optional[str], Tuple[int, int]]]

    def __init__(self) -> None:
        self.grid = {}

    def set_value(
        self, coord: Tuple[int, int], value: str, pixelCoord: Tuple[int, int]
    ) -> None:
        self.grid[coord] = (value, pixelCoord)

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
            # if neighbor_coord in self.grid:
            #     print(self.grid[neighbor_coord][0])

            if (
                neighbor_coord in self.grid
                and self.grid[neighbor_coord][0] != "Missing"
            ):
                neighbors_with_values.append(neighbor_coord)

        return neighbors_with_values

    def pathfind(self, start: Tuple[int, int], end: Tuple[int, int]):
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
