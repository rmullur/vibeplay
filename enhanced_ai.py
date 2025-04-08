#!/usr/bin/env python3
"""
Enhanced Pokemon AI with Danny-E 33 + FroggestSpirit color patch support.
"""

from pyboy import PyBoy
from pyboy.utils import WindowEvent
import time
import random
import os
import sys
import numpy as np
from color_settings import AUTHENTIC_PALETTE, apply_custom_palette

# Configure ROM paths
ORIGINAL_ROM = "Pokemon Red.gb"
COLOR_ROM = "Pokemon Red Color.gb"

class PokemonAI:
    def __init__(self, rom_path, palette=AUTHENTIC_PALETTE, use_color=True, load_saved_state=False):
        self.rom_path = rom_path
        self.pyboy = None
        self.palette = palette
        self.use_color = use_color
        self.load_saved_state = load_saved_state
        
    def start_game(self):
        """Start the PyBoy emulator with the ROM"""
        if not os.path.exists(self.rom_path):
            print(f"ROM file not found at {self.rom_path}")
            return False
            
        print("Starting PyBoy emulator...")
        
        # Check for existing save files
        ram_file = f"{self.rom_path}.ram"
        state_file = f"{self.rom_path}.state"
        
        if os.path.exists(ram_file):
            print(f"Found save RAM file: {ram_file}")
            print("In-game saves will be automatically loaded")
        
        if os.path.exists(state_file) and self.load_saved_state:
            print(f"Found save state file: {state_file}")
            print("Save state will be loaded after initialization")
            
        # Initialize with explicit rendering parameters and GBC mode if using color ROM
        self.pyboy = PyBoy(self.rom_path, window="SDL2", scale=3, cgb=self.use_color)
        self.pyboy.set_emulation_speed(1)
        
        # The colors come from the patched ROM itself
        if self.use_color:
            print("Color mode enabled: Game Boy Color")
            # Colors are provided by the patched ROM, not custom palettes
            apply_custom_palette(self.pyboy, self.palette)
        
        # Print debug info
        print(f"Cartridge title: {self.pyboy.cartridge_title}")
        print(f"Window title: {self.pyboy.window_title}")
        
        # Give the window time to initialize and appear
        for _ in range(10):
            self.pyboy.tick(render=True)
            time.sleep(0.1)
            
        # Load save state if requested and available
        if self.load_saved_state and os.path.exists(state_file):
            try:
                with open(state_file, "rb") as f:
                    self.pyboy.load_state(f)
                print(f"Loaded save state from {state_file}")
            except Exception as e:
                print(f"Error loading save state: {e}")
            
        return True
        
    def press_button(self, button, duration=0.1):
        """Press a button for a specified duration"""
        valid_buttons = ['up', 'down', 'left', 'right', 'a', 'b', 'start', 'select']
        if button not in valid_buttons:
            print(f"Unknown button: {button}")
            return
            
        # Press button and hold
        self.pyboy.button_press(button)
        self.pyboy.tick(render=True)  # Force render the frame
        time.sleep(duration)
        
        # Release button
        self.pyboy.button_release(button)
        self.pyboy.tick(render=True)  # Force render the frame
        
    # Memory address constants
    RAM_ADDR = {
        # Player info
        "PLAYER_X": 0xD362,
        "PLAYER_Y": 0xD361,
        "CURRENT_MAP": 0xD35E,
        "PLAYER_DIRECTION": 0xC109,
        "PLAYER_NAME": 0xD158,  # Player name (11 bytes)
        "PLAYER_MONEY": 0xD347,  # Player money (3 bytes BCD)
        "BADGE_COUNT": 0xD356,  # Badges obtained
        
        # Game state
        "MENU_STATE": 0xCC24,
        "DIALOGUE_STATE": 0xCC26,
        "CURRENT_SCREEN": 0xCC2B,
        "GAME_STATE": 0xCC2C,
        
        # Item inventory
        "ITEM_COUNT": 0xD31D,  # Number of items in inventory
        "ITEMS_START": 0xD31E,  # Start of items list
        
        # Pokemon party info
        "PARTY_COUNT": 0xD163,
        "PARTY_SPECIES_START": 0xD164,  # 6 bytes, one per party slot
        
        # First Pokemon details
        "FIRST_POKEMON_SPECIES": 0xD16B,
        "FIRST_POKEMON_LEVEL": 0xD18C,
        "FIRST_POKEMON_HP": 0xD16C,
        "FIRST_POKEMON_MAX_HP": 0xD16D,
        "FIRST_POKEMON_EXP": 0xD179,  # Experience points (3 bytes)
        
        # Move info for first Pokemon
        "FIRST_POKEMON_MOVE1": 0xD173,
        "FIRST_POKEMON_MOVE2": 0xD174,
        "FIRST_POKEMON_MOVE3": 0xD175,
        "FIRST_POKEMON_MOVE4": 0xD176,
        "FIRST_POKEMON_MOVE1_PP": 0xD186,
        "FIRST_POKEMON_MOVE2_PP": 0xD187,
        "FIRST_POKEMON_MOVE3_PP": 0xD188,
        "FIRST_POKEMON_MOVE4_PP": 0xD189,
        
        # Status conditions
        "FIRST_POKEMON_STATUS": 0xD16F,
        
        # Game progress
        "EVENT_FLAGS": 0xD747,  # Start of event flags (2 bits per flag)
        "POKEDEX_OWNED": 0xD2F7,  # Start of Pokédex owned flags
        "POKEDEX_SEEN": 0xD30A,  # Start of Pokédex seen flags
        
        # Step counter (for Safari Zone, eggs in later games)
        "STEP_COUNTER": 0xD49C
    }
    
    # Status condition mapping
    STATUS_CONDITIONS = {
        0: "Healthy",
        1: "Asleep",
        2: "Poisoned",
        3: "Burned",
        4: "Frozen",
        5: "Paralyzed",
        8: "Toxic"  # Badly poisoned
    }
    
    def get_ram_state(self):
        """Get the current RAM state as a dictionary of important game values"""
        try:
            # Get the RAM object
            ram = self.pyboy.mb.cartridge.ram
            
            # Get basic player and game state
            ram_state = {
                "player_x": ram[self.RAM_ADDR["PLAYER_X"]],
                "player_y": ram[self.RAM_ADDR["PLAYER_Y"]],
                "current_map": ram[self.RAM_ADDR["CURRENT_MAP"]],
                "player_direction": ram[self.RAM_ADDR["PLAYER_DIRECTION"]],
                "menu_state": ram[self.RAM_ADDR["MENU_STATE"]],
                "dialogue_state": ram[self.RAM_ADDR["DIALOGUE_STATE"]],
                "current_screen": ram[self.RAM_ADDR["CURRENT_SCREEN"]],
                "game_state": ram[self.RAM_ADDR["GAME_STATE"]],
            }
            
            # Get player info
            player_name_bytes = [ram[self.RAM_ADDR["PLAYER_NAME"] + i] for i in range(11)]
            player_name = ""
            for b in player_name_bytes:
                if b == 0x50:  # End of name marker
                    break
                # Simple conversion from Pokemon character set to ASCII
                if 0x80 <= b <= 0x99:  # A-Z
                    player_name += chr(b - 0x80 + ord('A'))
                elif 0xA0 <= b <= 0xB9:  # a-z
                    player_name += chr(b - 0xA0 + ord('a'))
                elif b == 0xE8:  # Space
                    player_name += " "
                else:
                    player_name += "?"
            
            # Get money (BCD format)
            money_bytes = [ram[self.RAM_ADDR["PLAYER_MONEY"] + i] for i in range(3)]
            player_money = (money_bytes[0] + (money_bytes[1] << 8) + (money_bytes[2] << 16))
            
            # Convert BCD to decimal
            money_decimal = 0
            for i in range(6):  # 6 BCD digits
                digit = (player_money >> (i * 4)) & 0x0F
                money_decimal += digit * (10 ** i)
            
            # Get badge count (each bit is a badge)
            badge_byte = ram[self.RAM_ADDR["BADGE_COUNT"]]
            badge_count = bin(badge_byte).count('1')
            
            ram_state["player"] = {
                "name": player_name,
                "money": money_decimal,
                "badges": badge_count
            }
            
            # Get party count
            party_count = ram[self.RAM_ADDR["PARTY_COUNT"]]
            ram_state["party_count"] = party_count
            
            # Get party species
            party_species = []
            for i in range(min(6, party_count)):
                species_id = ram[self.RAM_ADDR["PARTY_SPECIES_START"] + i]
                party_species.append(species_id)
            ram_state["party_species"] = party_species
            
            # Get first Pokemon details
            status_value = ram[self.RAM_ADDR["FIRST_POKEMON_STATUS"]]
            status_text = self.STATUS_CONDITIONS.get(status_value, f"Unknown ({status_value})")
            
            # Get experience points (3 bytes)
            exp_bytes = [ram[self.RAM_ADDR["FIRST_POKEMON_EXP"] + i] for i in range(3)]
            exp_points = exp_bytes[0] + (exp_bytes[1] << 8) + (exp_bytes[2] << 16)
            
            # Get move PP
            move_pp = [
                ram[self.RAM_ADDR["FIRST_POKEMON_MOVE1_PP"]],
                ram[self.RAM_ADDR["FIRST_POKEMON_MOVE2_PP"]],
                ram[self.RAM_ADDR["FIRST_POKEMON_MOVE3_PP"]],
                ram[self.RAM_ADDR["FIRST_POKEMON_MOVE4_PP"]]
            ]
            
            ram_state["player_pokemon"] = {
                "species": ram[self.RAM_ADDR["FIRST_POKEMON_SPECIES"]],
                "level": ram[self.RAM_ADDR["FIRST_POKEMON_LEVEL"]],
                "hp": ram[self.RAM_ADDR["FIRST_POKEMON_HP"]],
                "max_hp": ram[self.RAM_ADDR["FIRST_POKEMON_MAX_HP"]],
                "exp": exp_points,
                "status": status_text,
                "moves": [
                    ram[self.RAM_ADDR["FIRST_POKEMON_MOVE1"]],
                    ram[self.RAM_ADDR["FIRST_POKEMON_MOVE2"]],
                    ram[self.RAM_ADDR["FIRST_POKEMON_MOVE3"]],
                    ram[self.RAM_ADDR["FIRST_POKEMON_MOVE4"]]
                ],
                "move_pp": move_pp
            }
            
            
            # Get item count and basic inventory
            item_count = ram[self.RAM_ADDR["ITEM_COUNT"]]
            items = []
            
            # Only read up to 20 items to avoid potential issues
            for i in range(min(20, item_count)):
                item_id = ram[self.RAM_ADDR["ITEMS_START"] + (i * 2)]
                item_quantity = ram[self.RAM_ADDR["ITEMS_START"] + (i * 2) + 1]
                if item_id > 0:
                    items.append({"id": item_id, "quantity": item_quantity})
            
            ram_state["inventory"] = {
                "item_count": item_count,
                "items": items
            }
            
            # Get Pokedex info
            pokedex_owned_count = 0
            pokedex_seen_count = 0
            
            # Count owned Pokemon (process first 26 bytes = 151 Pokemon)
            for i in range(26):
                owned_byte = ram[self.RAM_ADDR["POKEDEX_OWNED"] + i]
                seen_byte = ram[self.RAM_ADDR["POKEDEX_SEEN"] + i]
                
                # Count bits for owned and seen
                for j in range(8):
                    if (owned_byte >> j) & 1:
                        pokedex_owned_count += 1
                    if (seen_byte >> j) & 1:
                        pokedex_seen_count += 1
            
            ram_state["pokedex"] = {
                "owned": pokedex_owned_count,
                "seen": pokedex_seen_count
            }
            
            # Get step counter
            ram_state["step_counter"] = ram[self.RAM_ADDR["STEP_COUNTER"]]
            
            return ram_state
        except Exception as e:
            print(f"Error getting RAM state: {e}")
            return None

    def get_screen(self):
        """Get the current game state from RAM instead of screen"""
        ram_state = self.get_ram_state()
        if ram_state is None:
            return None
            
        # Convert RAM state to a format Claude can understand
        state_description = f"""
Current Game State:
- Position: ({ram_state['player_x']}, {ram_state['player_y']})
- Map: {ram_state['current_map']}
- Direction: {ram_state['player_direction']}
- Menu State: {ram_state['menu_state']}
- Dialogue State: {ram_state['dialogue_state']}
- Current Screen: {ram_state['current_screen']}
- Game State: {ram_state['game_state']}
- Step Counter: {ram_state['step_counter']}

Player Information:
- Name: {ram_state['player']['name']}
- Money: ₽{ram_state['player']['money']}
- Badges: {ram_state['player']['badges']}
- Pokédex: {ram_state['pokedex']['owned']} owned, {ram_state['pokedex']['seen']} seen

Player's Party:
- Pokemon Count: {ram_state['party_count']}
- Party Species IDs: {ram_state['party_species']}

Player's Active Pokemon:
- Species: {ram_state['player_pokemon']['species']}
- Level: {ram_state['player_pokemon']['level']}
- HP: {ram_state['player_pokemon']['hp']}/{ram_state['player_pokemon']['max_hp']}
- Experience: {ram_state['player_pokemon']['exp']}
- Status: {ram_state['player_pokemon']['status']}
- Moves: {ram_state['player_pokemon']['moves']}
- Move PP: {ram_state['player_pokemon']['move_pp']}

Inventory:
- Item Count: {ram_state['inventory']['item_count']}
- Items: {ram_state['inventory']['items']}
"""

            
        return state_description
        
    def random_walk(self, steps=100, step_delay=0.5):
        """Perform a random walk in the game world"""
        directions = ['up', 'down', 'left', 'right']
        
        for i in range(steps):
            direction = random.choice(directions)
            print(f"Step {i+1}/{steps}: Moving {direction}")
            self.press_button(direction, duration=0.2)
            
            # Make sure frames are rendered between steps
            for _ in range(5):  # Render a few frames between steps
                self.pyboy.tick(render=True)
                
            time.sleep(step_delay)
    
    def navigate_path(self, path, step_delay=0.5):
        """Follow a specific path of directions"""
        for i, direction in enumerate(path):
            print(f"Step {i+1}/{len(path)}: Moving {direction}")
            self.press_button(direction, duration=0.2)
            time.sleep(step_delay)
            
    def save_state(self, state_file=None):
        """Save the current emulator state to a file"""
        if not self.pyboy:
            print("Emulator not running")
            return False
            
        if state_file is None:
            state_file = f"{self.rom_path}.state"
            
        try:
            with open(state_file, "wb") as f:
                self.pyboy.save_state(f)
            print(f"Game state saved to {state_file}")
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
            
    def load_state(self, state_file=None):
        """Load an emulator state from a file"""
        if not self.pyboy:
            print("Emulator not running")
            return False
            
        if state_file is None:
            state_file = f"{self.rom_path}.state"
            
        if not os.path.exists(state_file):
            print(f"State file not found: {state_file}")
            return False
            
        try:
            with open(state_file, "rb") as f:
                self.pyboy.load_state(f)
            print(f"Game state loaded from {state_file}")
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False
            
    def stop(self):
        """Stop the emulator"""
        if self.pyboy:
            # Explicitly save game RAM when exiting
            self.pyboy.stop(save=True)
            print("Game progress saved to RAM file.")

def check_patched_rom():
    """Check if we have the patched color ROM available"""
    if os.path.exists(COLOR_ROM):
        return True
        
    if not os.path.exists(ORIGINAL_ROM):
        print(f"Error: Original ROM not found: {ORIGINAL_ROM}")
        return False
        
    print(f"\nColorized ROM not found: {COLOR_ROM}")
    print("The AI will run with the original monochrome ROM.")
    print("To create a colorized ROM, run: python patch_rom.py")
    return False
            
def main():
    # Determine which ROM to use
    use_color = check_patched_rom()
    
    if use_color:
        rom_path = COLOR_ROM
        print(f"Using colorized ROM: {COLOR_ROM}")
    else:
        rom_path = ORIGINAL_ROM
        print(f"Using original ROM: {ORIGINAL_ROM}")
    
    # Ask if user wants to load a saved state
    load_state = False
    state_path = f"{rom_path}.state"
    if os.path.exists(state_path):
        choice = input(f"Found save state at {state_path}. Load it? (y/n) [default=n]: ").strip().lower()
        load_state = choice == 'y'
    
    # Create AI with authentic GBC colors
    ai = PokemonAI(rom_path, palette=AUTHENTIC_PALETTE, use_color=use_color, load_saved_state=load_state)
    if not ai.start_game():
        return
        
    try:
        print("Game started! Press CTRL+C to exit.")
        
        # Keep the emulator running
        while True:
            ai.pyboy.tick(render=True)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ai.stop()

if __name__ == "__main__":
    main()