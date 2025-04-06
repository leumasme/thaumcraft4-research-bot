from collections import defaultdict
from typing import Dict, List, Tuple

class Inventory:
    def __init__(self):
        self.aspects: Dict[str, int] = defaultdict(int)

    def add_aspect(self, aspect: str, count: int = 1):
        self.aspects[aspect] += count

    def remove_aspect(self, aspect: str, count: int = 1):
        if self.aspects[aspect] >= count:
            self.aspects[aspect] -= count
            if self.aspects[aspect] == 0:
                del self.aspects[aspect]
        else:
            raise ValueError(f"Not enough {aspect} in inventory")

    def get_aspect_count(self, aspect: str) -> int:
        return self.aspects[aspect]

    def has_aspect(self, aspect: str) -> bool:
        return aspect in self.aspects

    def update_from_image_analysis(self, inventory_aspects: List[Tuple[Tuple[int, int, int, int], str]]):
        self.aspects.clear()
        for _, aspect_name in inventory_aspects:
            self.add_aspect(aspect_name)

    def __str__(self):
        return "\n".join(f"{aspect}: {count}" for aspect, count in self.aspects.items())
