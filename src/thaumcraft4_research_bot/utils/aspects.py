from typing import List, Tuple

from thaumcraft4_research_bot.utils.log import log

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

graph: defaultdict[str, List[str]] = defaultdict(list)

# Add edges between aspects and their parents
for aspect, parents in aspect_parents.items():
    for parent in parents:
        if parent is not None:
            if aspect not in graph[parent]:
                graph[parent].append(aspect)
            if parent not in graph[aspect]:
                graph[aspect].append(parent)

# Compute aspect costs without recursion by caching the results in a dictionary
aspect_costs = {}
remaining_aspects = set(aspect_parents.keys())

# Initialize primal aspects (aspects without parents) with cost 1
for aspect, parents in aspect_parents.items():
    if parents == (None, None) or parents == (None,):
        aspect_costs[aspect] = 1
        remaining_aspects.remove(aspect)

# temp cause im low on aer
aspect_costs["aqua"] = 2
aspect_costs["aer"] = 2
aspect_costs["ignis"] = 2
aspect_costs["perditio"] = 2

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
        log.error(
            "Cannot compute aspect costs for some aspects due to missing parents or cycles:"
        )
        log.error(", ".join(remaining_aspects))
        break

# Make sure the cheaper aspects are first in the neighbor list
# This is very cheap and makes the aspect path dfs heuristic work better
for aspect in graph.values():
    aspect.sort(key=lambda a: aspect_costs[a])

def find_all_element_paths_many(start: str, ends_list: List[str], n_list: List[int]):
    max_n = max(n_list)

    # Heuristic to speed this up dramatically
    # With this, the function won't actually return *all* paths, but definitely the cheapest ones
    min_costs = [999999999] * len(ends_list) # todo: proper default value
    max_min_cost_index = 0

    # Depth 3 for: Different ends, Alternative Paths, Nodes in Path
    paths_many: List[List[List[str]]] = [[] for _ in ends_list]

    def dfs(current_node: str, current_path: List[str], current_cost: int):
        nonlocal max_min_cost_index
        for i, (curr_end, curr_n) in enumerate(zip(ends_list, n_list)):
            if current_node == curr_end and len(current_path) == curr_n:
                paths_many[i].append(list(current_path))
                
                min_costs[i] = min(min_costs[i], current_cost)
                if min_costs[max_min_cost_index] < min_costs[i]:
                    max_min_cost_index = i

        if len(current_path) == max_n:
            return
        
        # If we're going to be worse than the worst best path, we can't find a best path anymore
        min_extra_cost = n_list[max_min_cost_index] - len(current_path)
        if min_extra_cost < 0:
            min_extra_cost = 0
        if current_cost + min_extra_cost > min_costs[max_min_cost_index]:
            return

        for neighbor in graph[current_node]:
            current_path.append(neighbor)
            dfs(neighbor, current_path, current_cost + aspect_costs[neighbor])
            current_path.pop()

    dfs(start, [start], 0)

    for paths in paths_many:
        paths.sort(key=calculate_cost_of_aspect_path)

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
