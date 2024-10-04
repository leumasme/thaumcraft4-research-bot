from typing import Dict, List, Tuple, Optional
from thaumcraft4_research_bot.utils.colors import aspect_colors, hex_to_rgb
import random

class Aspect:
    def __init__(self, name: str):
        self.name: str = name
        self.parents: List[str] = [p for p in aspect_parents[name] if p is not None]
        self.children: List[str] = [k for k, v in aspect_parents.items() if name in v]
        self.hex_color: str = aspect_colors.get(name, "000000")
        self.rgb_color: Tuple[int, int, int] = hex_to_rgb(self.hex_color)

    @staticmethod
    def resolve_children(name: str) -> List[str]:
        children = []
        for key, value in aspect_parents.items():
            if name in value:
                children.append(key)
        return children

    
    def __repr__(self) -> str:
        return f"Aspect({self.name}, Parents: {self.parents}, Children: {self.children})"

class AspectManager:
    def __init__(self):
        self.aspects: Dict[str, Aspect] = {}
        self._initialize_aspects()

    def _initialize_aspects(self) -> None:
        for aspect_name in aspect_parents.keys():
            self.aspects[aspect_name] = Aspect(aspect_name)

    def get_aspect(self, name: str) -> Optional[Aspect]:
        return self.aspects.get(name)

    def get_all_aspects(self) -> List[Aspect]:
        return list(self.aspects.values())

    def get_primal_aspects(self) -> List[Aspect]:
        return [aspect for aspect in self.aspects.values() if not aspect.parents]

    def get_compound_aspects(self) -> List[Aspect]:
        return [aspect for aspect in self.aspects.values() if aspect.parents]
    
    def validate_element_route(self, route: List[str]) -> bool:
        if len(route) < 2:
            return False

        for i in range(len(route) - 1):
            current_aspect = self.get_aspect(route[i])
            next_aspect = self.get_aspect(route[i + 1])

            if not current_aspect or not next_aspect:
                return False

            if next_aspect.name not in current_aspect.children and \
               current_aspect.name not in next_aspect.children and \
               next_aspect.name not in current_aspect.parents and \
               current_aspect.name not in next_aspect.parents:
                return False

        return True

    def build_element_route(self, start_aspect: str, end_aspect: str, n: int) -> List[List[str]]:
        if n < 0 or start_aspect not in self.aspects or end_aspect not in self.aspects:
            return []

        if n == 0:
            return [[start_aspect, end_aspect]] if self.validate_element_route([start_aspect, end_aspect]) else []

        unique_routes = set()

        def dfs(current: str, target: str, path: List[str], depth: int) -> None:
            if len(path) == n + 2:
                if current == target:
                    unique_routes.add(tuple(path))
                return

            neighbors = (self.aspects[current].children +
                         self.aspects[current].parents +
                         [asp for asp in self.aspects if current in self.aspects[asp].children or
                                                         current in self.aspects[asp].parents])

            for neighbor in neighbors:
                dfs(neighbor, target, path + [neighbor], depth + 1)

        dfs(start_aspect, end_aspect, [start_aspect], 0)
        return [list(route) for route in unique_routes]

# Note to self: Elements can connect to their parent aspect and their children aspects
# So aer -> tempestas -> aqua is a valid path
aspect_parents = {
    "aer": (None, None),
    "aqua": (None, None),
    "ordo": (None, None),
    "terra": (None, None),
    "ignis": (None, None),
    "perditio": (None, None),
    "lux": ("aer", "ignis"),
    "motus": ("aer", "ordo"),
    "arbor": ("aer", "herba"),
    "ira": ("telum", "ignis"),
    "sano": ("victus", "ordo"),
    "iter": ("motus", "terra"),
    "victus": ("aqua", "terra"),
    "volatus": ("aer", "motus"),
    "limus": ("victus", "aqua"),
    "gula": ("fames", "vacuos"),
    "tempestas": ("aer", "aqua"),
    "vitreus": ("terra", "ordo"),
    "herba": ("victus", "terra"),
    "radio": ("lux", "potentia"),
    "tempus": ("vacuos", "ordo"),
    "vacuos": ("aer", "perditio"),
    "potentia": ("ordo", "ignis"),
    "bestia": ("motus", "victus"),
    "sensus": ("aer", "spiritus"),
    "fames": ("victus", "vacuos"),
    "astrum": ("lux", "primordium"),  # astrum = custom4
    "gelum": ("ignis", "perditio"),
    "messis": ("herba", "humanus"),
    "lucrum": ("humanus", "fames"),
    "primordium": ("vacuos", "motus"),  # primordium = custom3
    "gloria": ("humanus", "iter"),  # gloria = custom5
    "luxuria": ("corpus", "fames"),
    "invidia": ("sensus", "fames"),
    "venenum": ("aqua", "perditio"),
    "corpus": ("mortuus", "bestia"),
    "magneto": ("metallum", "iter"),
    "aequalitas": ("cognitio", "ordo"),  # aequalitas = custom1
    "tabernus": ("tutamen", "iter"),
    "metallum": ("terra", "vitreus"),
    "auram": ("praecantatio", "aer"),
    "exanimis": ("motus", "mortuus"),
    "perfodio": ("humanus", "terra"),
    "mortuus": ("victus", "perditio"),
    "spiritus": ("victus", "mortuus"),
    "alienis": ("vacuos", "tenebrae"),
    "cognitio": ("ignis", "spiritus"),
    "humanus": ("bestia", "cognitio"),
    "vinculum": ("motus", "perditio"),
    "vesania": ("cognitio", "vitium"),  # vesania = custom2
    "superbia": ("volatus", "vacuos"),
    "caelum": ("vitreus", "metallum"),
    "terminus": ("lucrum", "alienis"),
    "permutatio": ("perditio", "ordo"),
    "meto": ("messis", "instrumentum"),
    "telum": ("instrumentum", "ignis"),
    "nebrisum": ("perfodio", "lucrum"),
    "instrumentum": ("humanus", "ordo"),
    "electrum": ("potentia", "machina"),
    "desidia": ("vinculum", "spiritus"),
    "tutamen": ("instrumentum", "terra"),
    "pannus": ("instrumentum", "bestia"),
    "machina": ("motus", "instrumentum"),
    "strontio": ("cognitio", "perditio"),
    "infernus": ("ignis", "praecantatio"),
    "praecantatio": ("vacuos", "potentia"),
    "vitium": ("praecantatio", "perditio"),
    "fabrico": ("humanus", "instrumentum"),
    "tenebrae": ("vacuos", "lux"),  # missing from automatic scraping for some reason
}



