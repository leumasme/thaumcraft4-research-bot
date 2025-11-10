# Thaumcraft 4 Research Bot

This is a screenshot-based bot to automate the Thaumcraft 4 research minigame (Minecraft 1.7.10).  
Made for the [Gregtech: New Horizons](https://github.com/GTNewHorizons/GT-New-Horizons-Modpack) Modpack (uses TC Research Tweaks addon)  
- Let me know if there's any other decent 1.7.10 modpacks using Thaumcraft 4, adding support shouldn't be much work

Meant to replace the various Thaumcraft Research "Helper" websites

## Preview

https://github.com/user-attachments/assets/235ce89c-b1fc-477e-9aa5-c23455fcd1ae

## Features
- Pixel-based puzzle recognition
  - Custom Resource Pack required
- Fast, Efficient universal puzzle solver
  - Tested to work on all research puzzles in GTNH
  - Generates solutions that use simple aspects
  - Optimized for speed (for a python project...)
- Automatic mouse control to quickly input found puzzle solutions
- Automatic mouse control to craft undiscovered aspects
  - Experimental

## Usage

Some technical know-how currently required.
- Install [uv](https://docs.astral.sh/uv/) (python runner / package manager)
- Download the code of the project and unzip it into a new folder
- Prepare the Game
  - Install and activate the required resource pack
  - Open a Research Table and put in an unsolved Research Notes item
    - There shouldn't be any aspects on the puzzle board except the initially given ones
  - Make sure the game window is on your main screen and is large enough
  - Make sure a large item tooltip isn't covering up the game board
    - You may want to hide NEI (default keybind in GTNH: `O`)
- Open a terminal in the project folder (Windows Terminal/Powershell/CMD)
- Start the project with the command: `uv run main`
  - The bot will now:
    - Bring the game to the foreground
    - Take a screenshot
    - Parse the puzzle board from the screenshot
    - Generate a solution for the puzzle
    - Move the mouse to place the aspects according to the solution
- After it's done placing aspects, put in the next unsolved Research Notes and press enter in the terminal to solve the next board

## Limitations
- **No Linux Support**
  - I don't want to deal with finding a universal way of taking screenshots and performing mouse input
- Solver algorithm currently doesn't scale well with many (7+) given aspects on large boards
  - It gets quite slow. On the largest boards (9+ given aspects) it may currently take *minutes* to calculate
- No detection for how many Aspects the player owns
  - I don't want to deal with fiddly OCR on the tiny minecraft font
  - This also means which aspects the algorithm considers as "Expensive" and "Cheap" currently doesn't consider things you may have a lot of (like Instrumentum)
- Currently no way to reduce the mouse interaction speed
  - The current speed works consistently for me, but might break on laggier machines.
- Not well tested on different GUI sizes & Screen Resolutions
- Currently not very user-friendly. Missing:
  - A no-code way to configure custom costs for aspects
  - Pre-bundled .exe releases
  - More comprehensible error messages

## FAQ

Q: The mouse control is going wild! How do I stop it?  
A: Smash your mouse into the top-left corner of the screen for an emergency stop

Q: Why not just pre-compute the best solution for all puzzles?  
A: The "holes" in the puzzle board are randomly placed when creating the Research Notes, so puzzles aren't always the same.  

Q: Why Python?  
A: It's the only language I know where I could find decent libraries to take screenshots and perform mouse input.  
Even these aren't good, though: the screenshot library just fails when the Window is at negative screen coordinates?

Q: Why isn't this a mod?  
A: That's too cheaty in my opinion.  

## Issues, Contributions, Contact

Use Github.  
When encountering a crash on a specific puzzle, include the generated "debug_input.png".  
You may also find me on the GTNH discord server.
