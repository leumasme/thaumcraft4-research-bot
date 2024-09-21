from typing import Dict, Tuple, Optional, List

class HexGrid:
    radius: int
    grid: Dict[Tuple[int, int], Optional[str]]

    def __init__(self) -> None:
        self.grid = {}

    def set_value(self, coord: Tuple[int, int], value: str) -> None:
        self.grid[coord] = value

    def get_value(self, coord: Tuple[int, int]) -> Optional[str]:
        return self.grid.get(coord, None)

    def get_neighbors(self, coord: Tuple[int, int]) -> List[Tuple[int, int]]:
        q, r = coord
        # Axial coordinate system neighbor offsets
        neighbor_deltas = [
            (1, 0), (0, 1), (-1, 1),
            (-1, 0), (0, -1), (1, -1)
        ]

        neighbors_with_values = []
        for dq, dr in neighbor_deltas:
            neighbor_coord = (q + dq, r + dr)
            if neighbor_coord in self.grid:
                neighbors_with_values.append(neighbor_coord)

        return neighbors_with_values
