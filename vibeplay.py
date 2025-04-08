#!/usr/bin/env python3
"""
Simple Pokémon Red emulator with game state monitoring
"""

import os
import sys
import time
import argparse
import base64
from io import BytesIO
import numpy as np
from PIL import Image
import anthropic
from pyboy import PyBoy
from dotenv import load_dotenv
from pyboy.utils import WindowEvent
import threading
from queue import Queue, Empty
import tempfile

# Load environment variables
load_dotenv()

# Claude API configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")

# Memory map constants for Pokemon Red
PLAYER_X = 0xD362  # Player X position on map
PLAYER_Y = 0xD361  # Player Y position on map
PLAYER_DIRECTION = 0xD368  # Player facing direction (0=down, 4=up, 8=left, 0C=right)
MAP_ID = 0xD35E  # Current map ID
BATTLE_TYPE = 0xD057  # Battle type (0=no battle)
MENU_STATE = 0xD356  # Menu state
JOYPAD_STATE = 0xFF00  # Joypad state register

# Player details memory addresses
PLAYER_NAME = 0xD2B5  # Player's name (10 bytes)
PLAYER_MONEY = 0xD347  # Player's money (3 bytes)
PLAYER_BADGES = 0xD356  # Player's badges (1 byte)
PLAYER_POKEDEX = 0xD2F7  # Pokedex owned (2 bytes)
PLAYER_POKEDEX_SEEN = 0xD2F9  # Pokedex seen (2 bytes)

# Pokemon party memory addresses
PARTY_COUNT = 0xD163  # Number of Pokemon in party
PARTY_START = 0xD164  # Start of party data
POKEMON_SIZE = 44  # Size of each Pokemon data structure

# Pokemon data offsets within structure
POKEMON_SPECIES = 0  # Species ID
POKEMON_LEVEL = 21  # Current level
POKEMON_HP = 22  # Current HP
POKEMON_MAX_HP = 24  # Maximum HP
POKEMON_STATUS = 16  # Status condition
POKEMON_MOVES = 8  # Start of moves (4 moves)

# Add map name dictionary
MAP_NAMES = {
    0x00: "Pallet Town",
    0x27: "Oak's Lab",
    0x28: "Player's House 1F",
    0x29: "Player's House 2F",
    0x2A: "Rival's House",
    0x2B: "Route 1",
    0x2C: "Viridian City",
    # Add more as needed
}

# Add direction name dictionary
DIRECTION_NAMES = {
    0x00: "Down",
    0x04: "Up",
    0x08: "Left",
    0x0C: "Right",
    # Diagonal/special cases
    0x01: "Down (running)",
    0x05: "Up (running)",
    0x09: "Left (running)",
    0x0D: "Right (running)"
}

# Add suggestion queue at the top level
suggestion_queue = Queue()

def add_suggestion(suggestion):
    """Add a suggestion to be used in the next AI decision."""
    suggestion_queue.put(suggestion)
    print(f"\nSuggestion added: {suggestion}")

def clear_suggestions():
    """Clear any pending suggestions."""
    while not suggestion_queue.empty():
        suggestion_queue.get()
    print("\nSuggestions cleared")

def get_current_suggestion():
    """Get the current suggestion if one exists."""
    try:
        return suggestion_queue.get_nowait()
    except Empty:
        return None

def get_map_name(map_id):
    return MAP_NAMES.get(map_id, f"Map 0x{map_id:02X}")

def get_direction_name(direction):
    return DIRECTION_NAMES.get(direction, f"Unknown (0x{direction:02X})")

def format_ram_values(values):
    lines = []
    for i in range(0, len(values), 4):
        addr = 0xD350 + i
        chunk = values[i:i+4]
        hex_values = " ".join(f"0x{x:02X}" for x in chunk)
        lines.append(f"0x{addr:04X}: {hex_values}")
    return "\n".join(lines)

def get_pokemon_name(species_id):
    """Convert Pokemon species ID to name"""
    # Basic list of early Pokemon for testing
    POKEMON_NAMES = {
        1: "Bulbasaur",
        4: "Charmander",
        7: "Squirtle",
        10: "Caterpie",
        13: "Weedle",
        16: "Pidgey",
        19: "Rattata",
        25: "Pikachu",
        35: "Clefairy",
        39: "Jigglypuff",
        50: "Diglett",
        52: "Meowth",
        54: "Psyduck",
        56: "Mankey",
        58: "Growlithe",
        60: "Poliwag",
        63: "Abra",
        66: "Machop",
        69: "Bellsprout",
        72: "Tentacool",
        74: "Geodude",
        77: "Ponyta",
        79: "Slowpoke",
        81: "Magnemite",
        84: "Doduo",
        86: "Seel",
        88: "Grimer",
        90: "Shellder",
        92: "Gastly",
        95: "Onix",
        96: "Drowzee",
        98: "Krabby",
        100: "Voltorb",
        102: "Exeggcute",
        104: "Cubone",
        106: "Hitmonlee",
        107: "Hitmonchan",
        108: "Lickitung",
        109: "Koffing",
        111: "Rhyhorn",
        113: "Chansey",
        114: "Tangela",
        115: "Kangaskhan",
        116: "Horsea",
        118: "Goldeen",
        120: "Staryu",
        121: "Starmie",
        122: "Mr. Mime",
        123: "Scyther",
        124: "Jynx",
        125: "Electabuzz",
        126: "Magmar",
        127: "Pinsir",
        128: "Tauros",
        129: "Magikarp",
        130: "Gyarados",
        131: "Lapras",
        132: "Ditto",
        133: "Eevee",
        134: "Vaporeon",
        135: "Jolteon",
        136: "Flareon",
        137: "Porygon",
        138: "Omanyte",
        139: "Omastar",
        140: "Kabuto",
        141: "Kabutops",
        142: "Aerodactyl",
        143: "Snorlax",
        144: "Articuno",
        145: "Zapdos",
        146: "Moltres",
        147: "Dratini",
        148: "Dragonair",
        149: "Dragonite",
        150: "Mewtwo",
        151: "Mew"
    }
    return POKEMON_NAMES.get(species_id, f"Pokemon #{species_id}")

def get_pokemon_status(status):
    """Convert status condition to readable text"""
    if status == 0:
        return "OK"
    elif status & 0x80:  # Poisoned
        return "PSN"
    elif status & 0x40:  # Burned
        return "BRN"
    elif status & 0x20:  # Frozen
        return "FRZ"
    elif status & 0x10:  # Paralyzed
        return "PAR"
    elif status & 0x08:  # Asleep
        return "SLP"
    else:
        return "???"

def get_party_info(pyboy):
    """Get information about the player's Pokemon party"""
    party_count = pyboy.memory[PARTY_COUNT]
    if party_count == 0:
        return "No Pokemon in party"
    
    party_info = []
    for i in range(party_count):
        base_addr = PARTY_START + (i * POKEMON_SIZE)
        species = pyboy.memory[base_addr + POKEMON_SPECIES]
        level = pyboy.memory[base_addr + POKEMON_LEVEL]
        hp = (pyboy.memory[base_addr + POKEMON_HP + 1] << 8) | pyboy.memory[base_addr + POKEMON_HP]
        max_hp = (pyboy.memory[base_addr + POKEMON_MAX_HP + 1] << 8) | pyboy.memory[base_addr + POKEMON_MAX_HP]
        status = pyboy.memory[base_addr + POKEMON_STATUS]
        
        party_info.append(f"{get_pokemon_name(species)} Lv{level} HP:{hp}/{max_hp} [{get_pokemon_status(status)}]")
    
    return "\n".join(party_info)

def get_player_info(pyboy):
    """Get information about the player"""
    # Read player name (10 bytes)
    name_bytes = [pyboy.memory[PLAYER_NAME + i] for i in range(10)]
    name = "".join(chr(b) for b in name_bytes if b != 0x50)  # 0x50 is the terminator
    
    # Read money (3 bytes)
    money = (pyboy.memory[PLAYER_MONEY + 2] << 16) | (pyboy.memory[PLAYER_MONEY + 1] << 8) | pyboy.memory[PLAYER_MONEY]
    
    # Read badges
    badges = pyboy.memory[PLAYER_BADGES]
    badge_count = bin(badges).count('1')
    
    return f"Trainer: {name}\nMoney: ¥{money:,}\nBadges: {badge_count}/8"

def send_button_press(pyboy, button, duration=0.2):
    """Send a button press and release with specified duration."""
    try:
        print(f"\nPressing button: {button}")
        
        # Validate button
        if button not in ["a", "b", "start", "select", "up", "down", "left", "right"]:
            print(f"Invalid button: {button}")
            return
            
        # Press button using send_input for directional buttons
        if button in ["up", "down", "left", "right"]:
            event = getattr(WindowEvent, f"PRESS_ARROW_{button.upper()}")
            pyboy.send_input(event)
        else:
            pyboy.button_press(button.upper())
            
        # Run a few frames to process the input
        for _ in range(5):
            pyboy.tick(render=True)
        
        # Wait for duration
        time.sleep(duration)
        
        # Release button
        if button in ["up", "down", "left", "right"]:
            event = getattr(WindowEvent, f"RELEASE_ARROW_{button.upper()}")
            pyboy.send_input(event)
        else:
            pyboy.button_release(button.upper())
            
        # Run a few frames to process the release
        for _ in range(5):
            pyboy.tick(render=True)
        
        # Wait after release
        time.sleep(0.2)
            
    except Exception as e:
        print(f"Error sending button press: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def screen_to_base64(screen_array):
    """Convert screen numpy array to base64 string for API"""
    img = Image.fromarray(screen_array)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_game_state(pyboy):
    """Get current game state including screen and RAM values"""
    # Get screen as numpy array
    screen = pyboy.screen.ndarray
    
    # Get RAM values
    ram_values = pyboy.memory[0xD350:0xD370]
    
    # Get player info
    player_info = get_player_info(pyboy)
    
    # Get party info
    party_info = get_party_info(pyboy)
    
    # Get location info
    x = pyboy.memory[PLAYER_X]
    y = pyboy.memory[PLAYER_Y]
    direction = pyboy.memory[PLAYER_DIRECTION]
    map_id = pyboy.memory[MAP_ID]
    battle_type = pyboy.memory[BATTLE_TYPE]
    menu_state = pyboy.memory[MENU_STATE]
    
    # Format state info
    state_info = f"""
Game State:
{player_info}

Party:
{party_info}

Location: {get_map_name(map_id)}
Position: ({x}, {y})
Direction: {get_direction_name(direction)}
Battle Type: {battle_type}
Menu State: {menu_state}

RAM Values (0xD350-0xD370):
{format_ram_values(ram_values)}
"""
    
    return screen, state_info

def ask_claude_for_action(screen, state_info, last_decision=None, decision_history=None):
    """Ask Claude API for the next action based on screen and state"""
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return ["wait"], None
            
    # Initialize retry variables
    retry_count = 0
    max_retries = 3
    base_delay = 2
            
    try:
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Convert screen to base64
        screen_base64 = screen_to_base64(screen)
        
        # Format decision history context
        history_context = ""
        
        # Use decision_history if available
        if decision_history and len(decision_history) > 0:
            # Format the last 3 decisions (or all if fewer)
            recent_decisions = decision_history[-3:] if len(decision_history) > 3 else decision_history
            for i, decision in enumerate(recent_decisions):
                history_context += f"Decision {len(decision_history) - len(recent_decisions) + i + 1}:\n{decision}\n"
        elif last_decision:
            # Fall back to just the last decision if history not available
            history_context = f"Previous Decision:\n{last_decision}\n"
        else:
            history_context = "No previous decisions.\n"
            
        print(f"\nDecision history context:\n{history_context}")
        
        # Check for any suggestions
        suggestion = get_current_suggestion()
        suggestion_context = f"\nSuggestion: {suggestion}\n" if suggestion else ""
        
        # Create message for Claude
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            temperature=1,
            system=f"""You are controlling a character in Pokemon Red. You have access to the current game state through RAM values and screen capture.
Your task is to decide a sequence of button presses to achieve a specific goal.
The RAM details on the map may not be perfect use the image to analyze where you are on the map. Use tye image heavily. The charector you control is in red color and is in the center of the screen with a cap. You can control this charector. Use your visual skills you really identify other things.

{suggestion_context}

CRITICAL NAVIGATION RULES - BE AGGRESSIVE:
1. You must be RIGHT NEXT TO and FACING an object/NPC to interact with it
2. When moving towards something, ALWAYS take at least 3-5 steps in that direction - you need to be touching it
3. Take LONG action sequences (5-10 actions) in a single turn - don't play it safe
4. If an action fails, immediately try a different, longer sequence
5. When in doubt, take more actions rather than fewer
6. Always include multiple 'a' presses when trying to interact
7. If movement fails, try longer sequences in the same direction
8. When navigating menus, take multiple steps in each direction
9. In battles, use longer sequences of moves and item selections
10. Don't be afraid to experiment with longer sequences - it's better to try too many actions than too few

Previous Game Context:
{history_context}

You will receive a history of your previous decisions. Use this context to make more informed decisions, avoid repeating failed strategies, and build upon successful ones. Each decision should consider what worked or didn't work in previous attempts.

Once the game is loaded, analyze the game state and determine what's happening:
1. What is the player's current position and direction?
2. Is the player in a battle?
3. What is the current menu or dialogue state?
4. What is the overall game state?

Available Actions and Their Meanings:
- up: Move character up (use for menu navigation or walking)
- down: Move character down (use for menu navigation or walking)
- left: Move character left (use for menu navigation or walking)
- right: Move character right (use for menu navigation or walking)
- a: Primary action button
  * Advances dialogue/text
  * Confirms menu selections
  * Interacts with NPCs/objects
  * Uses items in battle
  * Throws Pokeballs
- b: Secondary action button
  * Cancels/backs out of menus
  * Returns to previous screen
  * Runs from battles
  * Closes dialogue boxes
- start: Opens/closes the main menu
  * Access inventory
  * Check Pokemon
  * Save game
  * Options
- select: Secondary menu button
  * Opens Pokedex
  * Switches Pokemon order
  * Uses registered items
- wait: Do nothing for this frame
  * Use when waiting for animations
  * When game is processing
  * When no action is needed

Special handling for game states:
- If in battle, prioritize battle actions - See all Pokemon moves and make sure to use the right one after thinking through.
- If in dialogue, use 'a' to advance text
- If in menu, navigate using direction keys and 'a' to select
- If on world map, use direction keys to move

You can only interact with anything if you are right next to it.

RESPONSE FORMAT:
Your response must follow this exact format:

Previous Action:
[Your analysis of the last action taken, if any]

Current Analysis:
[Your analysis of the game state]

Decision:
[Your reasoning for the chosen action sequence]

Action Sequence: [action1, action2, action3, ...]

Where each action must be exactly one of: up, down, left, right, a, b, start, select, wait

Example responses:
Previous Action:
Last action was pressing 'a' to start dialogue with Professor Oak.

Current Analysis:
The player is in dialogue with Professor Oak. The text box shows "Welcome to the world of POKEMON!" and needs to be advanced.

Decision:
Since we're in dialogue, we need to press the A button to advance the text and continue with Professor Oak's introduction.

Action Sequence: ['a']

Previous Action:
Last action was moving up to approach the Pokemon Center counter.

Current Analysis:
The player needs to navigate to the Pokemon Center. They are currently facing down and need to move up twice, then right once.

Decision:
We'll create a sequence of movements to reach the Pokemon Center entrance.

Action Sequence: ['up', 'up', 'right']

IMPORTANT: The "Action Sequence:" line must be the last line of your response, and it must contain a valid Python list of actions. Each action must be in quotes, like 'up' or 'a', not just the word itself.""",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screen_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"{history_context}State:\n{state_info}"
                        }
                    ]
                }
            ]
        )
        
        # Extract action sequence from response
        response_text = ""
        if message.content:
            for content in message.content:
                if content.type == "text":
                    response_text += content.text
        
        print(f"Raw response from Claude:\n{response_text}\n")
        
        # Parse response to get action sequence
        valid_actions = ["up", "down", "left", "right", "a", "b", "start", "select", "wait"]
        response_lower = response_text.lower()
        
        # Look for action sequence in the response
        try:
            # Find the last line containing "Action Sequence:"
            action_lines = [line for line in response_text.split('\n') if "Action Sequence:" in line]
            if action_lines:
                action_line = action_lines[-1]
                # Extract the list part after "Action Sequence:"
                action_str = action_line.split("Action Sequence:")[1].strip()
                # Clean up the string to ensure it's valid Python list syntax
                action_str = action_str.replace("'", '"')  # Replace single quotes with double quotes
                action_str = action_str.strip('[]')  # Remove outer brackets if present
                action_str = f"[{action_str}]"  # Ensure it's wrapped in brackets
                # Evaluate the string as a Python list
                action_list = eval(action_str)
                # Validate each action
                if all(action in valid_actions for action in action_list):
                    print(f"Found valid action sequence: {action_list}")
                    # Return both the action list and the full response text
                    return action_list, response_text
            else:
                print("No 'Action Sequence:' line found in response")
        except Exception as e:
            print(f"Error parsing action sequence: {e}")
            print(f"Attempted to parse: {action_str}")
        
        print("No valid action sequence found in response, defaulting to ['wait']")
        return ["wait"], None
                
    except Exception as e:
        error_str = str(e)
        if "overloaded_error" in error_str or "529" in error_str:
            retry_count += 1
            if retry_count <= max_retries:
                # Calculate exponential backoff delay
                delay = base_delay * (2 ** (retry_count - 1))
                print(f"Claude API overloaded (attempt {retry_count}/{max_retries}), waiting {delay} seconds...")
                time.sleep(delay)
                return ask_claude_for_action(screen, state_info, last_decision)  # Retry with backoff
            else:
                print("Max retries reached, defaulting to wait")
                return ["wait"], None
        print(f"API Error: {error_str}")
        return ["wait"], None  # Default to waiting if there's an error

def suggestion_input_thread():
    """Thread that reads suggestions from a file."""
    # Create suggestion file in current directory
    suggestion_file = "ai_suggestions.txt"
    
    # Create empty file if it doesn't exist
    if not os.path.exists(suggestion_file):
        with open(suggestion_file, 'w') as f:
            pass
    
    print(f"\nTo provide suggestions, edit the file: {os.path.abspath(suggestion_file)}")
    print("The AI will check this file for new suggestions.")
    print("To clear suggestions, delete all content from the file.")
    print("The file will be automatically created in the current directory.")
    
    last_modified = 0
    while True:
        try:
            # Check if file exists and has been modified
            if os.path.exists(suggestion_file):
                current_modified = os.path.getmtime(suggestion_file)
                if current_modified > last_modified:
                    with open(suggestion_file, 'r') as f:
                        suggestion = f.read().strip()
                        if suggestion:
                            add_suggestion(suggestion)
                            print(f"\nNew suggestion read from file: {suggestion}")
                        else:
                            clear_suggestions()
                            print("\nSuggestions cleared (file is empty)")
                    last_modified = current_modified
            time.sleep(1)  # Check every second
        except Exception as e:
            print(f"Error in suggestion thread: {e}")
            time.sleep(1)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Pokemon Red Emulator with Game State Monitoring')
    parser.add_argument('--load-state', type=str, help='Path to load state file (e.g. pokemon_red.state)')
    parser.add_argument('--frame-interval', type=int, default=10, help='Number of frames between Claude API calls (default: 10)')
    parser.add_argument('--button-duration', type=float, default=0.2, help='Duration to hold buttons (default: 0.2)')
    args = parser.parse_args()

    # Start suggestion input thread
    threading.Thread(target=suggestion_input_thread, daemon=True).start()

    # Configure ROM paths
    ORIGINAL_ROM = os.environ.get("ORIGINAL_ROM", "Pokemon Red.gb")
    COLOR_ROM = os.environ.get("COLOR_ROM", "Pokemon Red Color.gb")
    
    # Determine which ROM to use
    use_color = os.path.exists(COLOR_ROM)
    rom_path = COLOR_ROM if use_color else ORIGINAL_ROM
    
    if not os.path.exists(rom_path):
        print(f"Error: ROM file '{rom_path}' not found!")
        print("\nPlease ensure one of these ROM files exists:")
        print(f"  - {COLOR_ROM}")
        print(f"  - {ORIGINAL_ROM}")
        print("\nOr set the ROM path in your .env file:")
        print("ORIGINAL_ROM=path/to/your/rom.gb")
        print("COLOR_ROM=path/to/your/color/rom.gb")
        return
    
    print(f"Using ROM: {rom_path}")
    
    # Initialize PyBoy
    pyboy = PyBoy(rom_path, sound=False)
    
    # Load state if provided
    if args.load_state:
        state_file = args.load_state
        if not os.path.exists(state_file):
            print(f"Error: State file '{state_file}' not found!")
            print("Available state files:")
            for f in os.listdir("."):
                if f.endswith(".state"):
                    print(f"  - {f}")
            return
            
        try:
            with open(state_file, "rb") as f:
                pyboy.load_state(f)
            print(f"Loaded state from {state_file}")
        except Exception as e:
            print(f"Error loading state file: {e}")
            return
    
    print("Game started! Monitoring game state...")
    print("Press CTRL+C to exit and save state")
    print(f"Processing every {args.frame_interval} frames")
    
    frame_count = 0
    action_sequence = []
    current_action_index = 0
    last_action_time = time.time()
    last_decision = None  # Track last decision for context
    decision_history = []  # Track multiple past decisions
    pending_api_call = False  # Track if we're waiting for an API response
    current_decision = None  # Initialize current_decision
    
    try:
        while True:
            # Run one frame
            pyboy.tick(render=True)
            frame_count += 1
            
            # Get game state and ask Claude every N frames
            if frame_count % args.frame_interval == 0 and not pending_api_call:
                print(f"\nFrame {frame_count}")
                
                # If we've completed the current action sequence, get a new one
                if current_action_index >= len(action_sequence):
                    # Get current game state
                    screen, state_info = get_game_state(pyboy)
                    
                    # Set pending API call flag
                    pending_api_call = True
                    
                    # Start a new thread for the API call
                    def make_api_call():
                        nonlocal action_sequence, current_action_index, current_decision, last_decision, pending_api_call
                        try:
                            # Ask Claude for next action sequence
                            action_sequence, current_decision = ask_claude_for_action(screen, state_info, last_decision, decision_history)
                            current_action_index = 0
                            
                            # Store the full decision in history (up to 10 decisions)
                            if current_decision:
                                # Extract the relevant parts of the decision
                                decision_parts = current_decision.split("\n\n")
                                analysis = ""
                                for part in decision_parts:
                                    if part.startswith("Current Analysis:") or part.startswith("Decision:"):
                                        analysis += part + "\n\n"
                                
                                # Store the analysis in history
                                if analysis:
                                    decision_history.append(analysis.strip())
                                    if len(decision_history) > 10:
                                        decision_history.pop(0)  # Remove oldest decision
                            
                            # Update last_decision with current decision
                            last_decision = current_decision
                            print(f"New action sequence: {action_sequence}")
                        finally:
                            pending_api_call = False
                    
                    # Start the API call in a separate thread
                    threading.Thread(target=make_api_call).start()
                
                # Execute the next action in the sequence
                if action_sequence and current_action_index < len(action_sequence):
                    action = action_sequence[current_action_index]
                    print(f"\nExecuting action {current_action_index + 1}/{len(action_sequence)}: {action}")
                    send_button_press(pyboy, action, duration=args.button_duration)
                    current_action_index += 1
                    last_action_time = time.time()
                
    except KeyboardInterrupt:
        print("\nSaving state...")
        state_file = "pokemon_red.state"
        try:
            with open(state_file, "wb") as f:
                pyboy.save_state(f)
            print(f"State saved successfully to {state_file}")
        except Exception as e:
            print(f"Error saving state: {e}")
    finally:
        pyboy.stop()

if __name__ == "__main__":
    main()