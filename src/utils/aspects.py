from functools import lru_cache
from typing import List, Tuple


from ..utils.config import get_global_config
from ..utils.log import log

aspect_parents: dict[str, Tuple[str, str] | Tuple[None, None]] = {
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

for disabled_aspect in get_global_config().disabled_aspects:
    disabled_aspect = disabled_aspect.lower()
    if disabled_aspect in aspect_parents:
        del aspect_parents[disabled_aspect]
    else:
        log.warning(f"Disabled aspect '{disabled_aspect}' did not exist in the first place")

# Build the graph as an adjacency list
from collections import defaultdict
# TODO: is this still needed instead of using aspect_parents?
aspect_graph: defaultdict[str, List[str]] = defaultdict(list)

# Add edges between aspects and their parents
for aspect, parents in aspect_parents.items():
    for parent in parents:
        if parent is not None:
            if aspect not in aspect_graph[parent]:
                aspect_graph[parent].append(aspect)
            if parent not in aspect_graph[aspect]:
                aspect_graph[aspect].append(parent)

# Compute aspect costs without recursion by caching the results in a dictionary
aspect_costs = {k.lower(): v for k, v in get_global_config().aspect_cost_overrides.items()}
remaining_aspects = set(aspect_parents.keys())

# Initialize primal aspects (aspects without parents) with cost 1
for aspect, parents in aspect_parents.items():
    if parents == (None, None) and aspect not in aspect_costs:
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
        log.error(
            "Cannot compute aspect costs for some aspects due to missing parents or cycles:"
        )
        log.error(", ".join(remaining_aspects))
        break

# Make sure the cheaper aspects are first in the neighbor list
# This is very cheap and makes the aspect path dfs heuristic work better
for aspect in aspect_graph.values():
    aspect.sort(key=lambda a: aspect_costs[a])

# Wrapper for lru_cache since List is not hashable, and arguments must be hashable
def find_cheapest_element_paths_many(start: str, ends_list: List[str], n_list: List[int]) -> List[List[List[str]]]:
    return _find_cheapest_element_paths_many(start, tuple(ends_list), tuple(n_list))

@lru_cache(maxsize=1000)
def _find_cheapest_element_paths_many(start: str, ends_list: Tuple[str, ...], n_list: Tuple[int, ...]) -> List[List[List[str]]]:
    assert start != "Free" and start != "Missing", f"{start} is not a valid start aspect"
    assert "Free" not in ends_list and "Missing" not in ends_list, f"{ends_list} contains invalid end aspect"

    max_n: int = max(n_list)

    # At each step, track minimum costs to reach an aspect and via which predecessors to reach it
    # step -> {aspect: min_cost to reach that aspect}
    min_costs: list[dict[str, int]] = [{} for _ in range(max_n)]
    # step -> {aspect: [predecessors to reach that aspect]}
    predecessors: list[dict[str, List[str]]] = [{} for _ in range(max_n)]
    
    min_costs[0][start] = aspect_costs[start]
    
    # Iterare forwards from the start aspect to calculate min_costs and predecessors
    previous_step_aspects: List[str] = [start]
    for step in range(max_n - 1):
        for aspect in previous_step_aspects:
            curr_cost = min_costs[step][aspect]
            
            for neighbor in aspect_graph[aspect]:
                new_cost = curr_cost + aspect_costs[neighbor]
                next_step = step + 1
                
                if neighbor not in min_costs[next_step] or new_cost < min_costs[next_step][neighbor]:
                    # Reached a new aspect or found a cheaper path to it
                    # Clear and set the new cost and predecessors
                    min_costs[next_step][neighbor] = new_cost
                    predecessors[next_step][neighbor] = [aspect]
                elif new_cost == min_costs[next_step][neighbor]:
                    # Found another path with the same best cost
                    predecessors[next_step][neighbor].append(aspect)
        
        # Update for next step
        previous_step_aspects = list(min_costs[step+1].keys())
    
    # Iterate backwards to find the cheapest paths for each end aspect
    # end_aspect_index -> step[][]
    paths_many: List[List[List[str]]] = [[] for _ in ends_list]
    for idx, (end, target_length) in enumerate(zip(ends_list, n_list)):
        # Handle special cases
        if target_length <= 0:
            continue
        if target_length == 1:
            if end == start:
                paths_many[idx].append([start])
            continue
        
        # Skip if end not reachable in the target length
        target_step_index = target_length - 1
        if target_step_index >= max_n or end not in min_costs[target_step_index]:
            continue
        
        # Build all minimum cost paths
        def reconstruct_path(current: str, step_idx: int, current_path: List[str]) -> None:
            if step_idx == 0:
                # We've reached the start, complete and save the path
                paths_many[idx].append(current_path)
                return
            
            # Try all predecessors that achieve the minimum cost
            for prev in predecessors[step_idx][current]:
                reconstruct_path(prev, step_idx - 1, [prev] + current_path)
        
        # Start from the end node
        reconstruct_path(end, target_step_index, [end])
    
    return paths_many

def calculate_cost_of_aspect_path(path: List[str]) -> int:
    return sum(aspect_costs[aspect] for aspect in path)
