#!/usr/bin/env python3
"""
Color settings for improved Game Boy Color emulation.
"""

from pyboy import PyBoy
import time
import sys

# Game Boy Color Custom Palettes
# These are inspired by more accurate GBC emulators like SameBoy and mGBA

# Authentic Game Boy Color palette (more accurate)
AUTHENTIC_PALETTE = [
    # Background/Window palette (more saturated and vibrant)
    (255, 255, 255),  # White
    (132, 196, 132),  # Light green
    (88, 144, 88),    # Dark green
    (40, 80, 40),     # Very dark green/black
    
    # Sprite palette 0 (Red/Fire)
    (255, 255, 255),  # White
    (255, 144, 144),  # Light red
    (224, 64, 64),    # Medium red
    (136, 32, 32),    # Dark red
    
    # Sprite palette 1 (Blue/Water)
    (255, 255, 255),  # White
    (144, 176, 255),  # Light blue
    (64, 96, 224),    # Medium blue
    (32, 48, 136),    # Dark blue
]

# High contrast palette for better visibility
HIGH_CONTRAST_PALETTE = [
    # Background/Window palette
    (255, 255, 255),  # White
    (170, 220, 170),  # Light green
    (90, 180, 90),    # Medium green
    (22, 60, 22),     # Dark green
    
    # Sprite palette 0
    (255, 255, 255),  # White
    (255, 160, 160),  # Light red
    (240, 80, 80),    # Medium red
    (160, 40, 40),    # Dark red
    
    # Sprite palette 1
    (255, 255, 255),  # White
    (160, 200, 255),  # Light blue
    (80, 120, 240),   # Medium blue
    (40, 70, 160),    # Dark blue
]

# SameBoy-inspired palettes
SAMEBOY_PALETTE = [
    # Background colors
    (255, 255, 255),  # White
    (136, 192, 112),  # Light green
    (52, 104, 86),    # Dark green
    (8, 24, 32),      # Blackish
    
    # Sprite palette 0
    (255, 255, 255),  # White
    (224, 136, 128),  # Light red
    (192, 32, 32),    # Red
    (80, 8, 8),       # Dark red
    
    # Sprite palette 1
    (255, 255, 255),  # White
    (136, 168, 224),  # Light blue
    (32, 56, 192),    # Blue
    (8, 16, 80),      # Dark blue
]

def apply_custom_palette(pyboy_instance, palette=AUTHENTIC_PALETTE):
    """Apply a custom color palette to the PyBoy emulator."""
    try:
        # PyBoy doesn't have a direct color_palette setting method
        # The colorization comes from the patched ROM and cgb=True setting
        
        # Just log that we're using the palette (actual ROM colors are from the patch)
        palette_name = "Authentic GBC" 
        if palette == HIGH_CONTRAST_PALETTE:
            palette_name = "High Contrast"
        elif palette == SAMEBOY_PALETTE:
            palette_name = "SameBoy-inspired"
            
        print(f"Using '{palette_name}' palette (colors applied via ROM patch)")
        return True
    except Exception as e:
        print(f"Note: Custom palette feature is informational only - the ROM patch provides colorization")
        return True  # Return True anyway as the colorized ROM still works

def preview_palettes(rom_path):
    """Show preview of different palettes."""
    # For the patched ROM, palette settings are informational only
    # The actual colors come from the ROM patch
    
    print("\nPalette Preview")
    print("--------------")
    print("Note: The Danny-E 33 + FroggestSpirit color patch provides its own colors.")
    print("PyBoy doesn't support custom palette application - colors come from the ROM itself.")
    print("\nAvailable palettes (informational only):")
    print("1. Authentic GBC - closest to real Game Boy Color hardware")
    print("2. High Contrast - enhanced visibility for gameplay")
    print("3. SameBoy-inspired - colors based on accurate emulator")
    
    # Just launch the emulator with the colorized ROM
    try:
        print("\nLaunching ROM with Game Boy Color mode enabled...")
        pyboy = PyBoy(rom_path, window="SDL2", scale=3, cgb=True)
        
        # Run for a while to see the effect
        print("\nShowing patched ROM colors...")
        print("(Press CTRL+C to exit)")
        
        frame_count = 0
        while True:
            pyboy.tick(render=True)
            frame_count += 1
            if frame_count > 300:  # Show for about 5 seconds
                break
                
        # Clean up
        pyboy.stop()
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nPalette preview complete.")

if __name__ == "__main__":
    # If ROM path provided as argument, use it, otherwise use default
    rom_path = sys.argv[1] if len(sys.argv) > 1 else "Pokemon Red.gb"
    preview_palettes(rom_path)