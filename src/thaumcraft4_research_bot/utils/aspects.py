from typing import List, Tuple

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

# Build the graph as an adjacency list
from collections import defaultdict
from itertools import product

graph = defaultdict(set)

# Add edges between aspects and their parents
for aspect, parents in aspect_parents.items():
    for parent in parents:
        if parent is not None:
            graph[aspect].add(parent)
            graph[parent].add(aspect)

# Compute aspect costs without recursion by caching the results in a dictionary
aspect_costs = {}
remaining_aspects = set(aspect_parents.keys())

# Initialize primal aspects (aspects without parents) with cost 1
for aspect, parents in aspect_parents.items():
    if parents == (None, None) or parents == (None,):
        aspect_costs[aspect] = 1
        remaining_aspects.remove(aspect)

# Iteratively compute costs for aspects whose parents' costs are known
while remaining_aspects:
    progress = False
    for aspect in list(remaining_aspects):
        parents = aspect_parents[aspect]
        # Check if all parents' costs are known
        if all(parent in aspect_costs for parent in parents if parent is not None):
            # Compute the aspect's cost as the sum of its parents' costs
            total_cost = sum(
                aspect_costs[parent] for parent in parents if parent is not None
            )
            aspect_costs[aspect] = total_cost
            remaining_aspects.remove(aspect)
            progress = True
    if not progress:
        # Cannot compute aspect costs due to missing parents or cycles
        print(
            "Cannot compute aspect costs for some aspects due to missing parents or cycles:"
        )
        print(", ".join(remaining_aspects))
        break


def find_all_element_paths_of_length_n(start: str, end: str, n: int):
    """
    Find all paths of length n between start and end in the graph.
    """
    paths: List[List[str]] = []

    def dfs(current_node: str, current_path: List[str]):
        if len(current_path) == n:
            if current_node == end:
                paths.append(list(current_path))
            return

        for neighbor in graph[current_node]:
            current_path.append(neighbor)
            dfs(neighbor, current_path)
            current_path.pop()

    dfs(start, [start])

    if len(paths) == 0:
        print("No aspect path found from", start, "to", end, "of length", n)
        return []

    paths.sort(key=lambda p: calculate_cost_of_aspect_path(p))

    return paths

def find_all_element_paths_many(start: str, ends_arg: List[str], n_list: List[int]):
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

        for neighbor in graph[current_node]:
            current_path.append(neighbor)
            dfs(neighbor, current_path)
            current_path.pop()

    dfs(start, [start])

    for paths in paths_many:
        paths.sort(key=lambda p: calculate_cost_of_aspect_path(p))

    return paths_many

def calculate_cost_of_aspect_path(path: List[str]) -> int:
    return sum(aspect_costs[aspect] for aspect in path)


# Example usage:
# starts = ["aer", "ignis"]
# ends = ["terra", "aqua"]
# n = 6
# combinations = find_all_path_combinations_of_length_n(starts, ends, n)
# for combo in combinations:
#     print(combo)
