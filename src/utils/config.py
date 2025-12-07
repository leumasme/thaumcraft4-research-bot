from functools import cache
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .log import log

CONFIG_FILE_NAME = "config.toml"

DEFAULT_CONFIG = """
# Thaumcraft 4 Research Bot Configuration
# Lines starting with '#' are comments and will be ignored.
[general]
# Title (or beginning of title) of the game window
game-window-title = "GT: New Horizons"

# List of aspects to disable (pretend they do not exist, like if their mod/addon is not installed)
disabled-aspects = []
# Example: disabled-aspects = ["caelum", "tabernus"]

[aspect-costs]
# Define custom aspect costs here
# Research solutions are scored by the total cost of all aspects used in the solution.
# By default, all the primal aspects cost 1, all other aspects cost the sum of their components
# Example:
#   - aqua and terra are primal, so they cost 1 each
#   - victus = aqua + terra, so it costs 2
#   - herba = terra + victus, so it costs 3
# You can override these defaults like this, one entry per line (without the #):
# instrumentum = 1
"""


@dataclass
class Config:
    game_window_title: str
    aspect_cost_overrides: dict[str, int]
    disabled_aspects: list[str]


@cache
def get_global_config() -> Config:
    config_path = Path(CONFIG_FILE_NAME)
    # If config file does not exist, create it with default content
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            log.info(f"Config file '{CONFIG_FILE_NAME}' not found. Creating default config.")
            f.write(DEFAULT_CONFIG.strip())
            
    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)
        
    return Config(
        game_window_title=config_data["general"]["game-window-title"],
        aspect_cost_overrides=config_data.get("aspect-costs", {}),
        disabled_aspects=config_data["general"].get("disabled-aspects", []),
    )
