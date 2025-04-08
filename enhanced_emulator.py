#!/usr/bin/env python3
"""
Enhanced Pokemon Red Emulator with Danny-E 33 + FroggestSpirit color patch support.
This script automatically detects and uses the colorized ROM if available.
"""

from pyboy import PyBoy
from pyboy.utils import WindowEvent
import time
import os
import sys
from color_settings import (
    AUTHENTIC_PALETTE, 
    HIGH_CONTRAST_PALETTE, 
    SAMEBOY_PALETTE,
    apply_custom_palette
)

# Configure ROM paths
ORIGINAL_ROM = "Pokemon Red.gb"
COLOR_ROM = "Pokemon Red Color.gb"

def get_palette_choice():
    """Get user's palette choice (informational only)"""
    print("\nSelect color palette preference (informational only):")
    print("Note: Colors are provided by the ROM patch itself, not by these settings.")
    print("1. Authentic GBC (Game Boy Color hardware)")
    print("2. High Contrast (better visibility)")
    print("3. SameBoy-inspired (high quality emulator)")
    
    choice = input("Enter choice (1-3) [default=1]: ").strip() or "1"
    
    palette_map = {
        "1": AUTHENTIC_PALETTE,
        "2": HIGH_CONTRAST_PALETTE,
        "3": SAMEBOY_PALETTE,
    }
    
    return palette_map.get(choice, AUTHENTIC_PALETTE)

def patch_rom_if_needed():
    """Check if we need to patch the ROM and offer to do so"""
    if os.path.exists(COLOR_ROM):
        return True
        
    if not os.path.exists(ORIGINAL_ROM):
        print(f"Error: Original ROM not found: {ORIGINAL_ROM}")
        return False
        
    if not os.path.exists("pokered_color/pokered_color_gen2.ips"):
        print("Error: Color patch files not found in pokered_color/ directory")
        return False
        
    print("\nColorized ROM not found. Would you like to create it now?")
    choice = input("Apply color patch to create colorized ROM? (y/n) [default=y]: ").strip().lower() or "y"
    
    if choice != "y":
        print("Using original monochrome ROM...")
        return False
        
    # Execute the patch_rom.py script
    try:
        import patch_rom
        success = patch_rom.main()
        return success
    except Exception as e:
        print(f"Error patching ROM: {e}")
        return False

def main():
    """Main emulator function"""
    print("\n===== Enhanced Pokemon Red Emulator =====")
    print("With Danny-E 33 + FroggestSpirit full color patch")
    
    # Check if we have or can create a colorized ROM
    has_color = patch_rom_if_needed()
    
    # Determine which ROM to use
    if has_color:
        rom_path = COLOR_ROM
        print(f"\nUsing colorized ROM: {COLOR_ROM}")
    else:
        rom_path = ORIGINAL_ROM
        print(f"\nUsing original ROM: {ORIGINAL_ROM}")
    
    # Check if ROM exists
    if not os.path.exists(rom_path):
        print(f"ERROR: ROM file not found at {rom_path}")
        sys.exit(1)
    
    # Check for existing save files
    ram_file = f"{rom_path}.ram"
    state_file = f"{rom_path}.state"
    
    if os.path.exists(ram_file):
        print(f"Found save RAM file: {ram_file}")
        print("In-game saves will be automatically loaded")
    
    if os.path.exists(state_file):
        print(f"Found save state file: {state_file}")
        print("You can load this state by pressing F8 after the game starts")
    
    # Get palette choice (informational only - colors come from ROM patch)
    selected_palette = get_palette_choice() if has_color else None
    
    # Initialize PyBoy with explicit window and Game Boy Color mode enabled
    try:
        print("\nStarting enhanced Pokemon Red emulator...")
        
        # Initialize with GBC mode if using color ROM
        # Setting auto_load_save to True ensures .ram file is loaded if it exists
        pyboy = PyBoy(rom_path, window="SDL2", scale=3, cgb=has_color)
        print(f"Cartridge title: {pyboy.cartridge_title}")
        
        if has_color:
            print("Color mode enabled: Game Boy Color")
            
            # The colors come from the patched ROM itself
            apply_custom_palette(pyboy, selected_palette)
        
        # Initialization loop - run a few frames to ensure window appears
        print("Initializing display...")
        for _ in range(10):
            pyboy.tick(render=True)
            time.sleep(0.1)
            
        # Press Start to begin the game
        print("Pressing START button to begin game...")
        pyboy.button('start')
        for _ in range(10):
            pyboy.tick(render=True)
            time.sleep(0.1)
            
        # Main game loop - keep rendering frames
        print("\nGame started! Use keyboard to control the game.")
        print("Controls: Arrow keys for movement, Z for A, X for B, ENTER for Start, BACKSPACE for Select")
        print("Save/Load: F5 to save state, F8 to load state")
        print("Press CTRL+C to exit")
        
        frame_count = 0
        while True:
            # Process events for save/load state functionality
            # PyBoy doesn't have get_events() - events are automatically processed by tick()
            # F5 and F8 are already mapped to STATE_SAVE and STATE_LOAD in PyBoy
            # The events are processed internally when we call pyboy.tick()
            
            # Process frame with rendering
            # This will also handle internal events like F5/F8 for save/load
            pyboy.tick(render=True)
            
            frame_count += 1
            if frame_count % 60 == 0:
                print(f"Processed {frame_count} frames")
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\nExiting emulator...")
    except Exception as e:
        print(f"Error running emulator: {e}")
    finally:
        if 'pyboy' in locals():
            # Explicitly save game RAM when exiting
            pyboy.stop(save=True)
            print("Game progress saved to RAM file.")
    
    print("Emulator closed.")

if __name__ == "__main__":
    main()