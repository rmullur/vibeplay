#!/usr/bin/env python3
"""
Tool to apply IPS patches to Pokemon Red ROM.
Based on the pokered_color patches by Danny-E 33 and FroggestSpirit.

This script applies the IPS patch to create a fully colorized version
of Pokemon Red that works with PyBoy's Game Boy Color support.
"""

import os
import sys
import struct
import shutil

# IPS format constants
IPS_HEADER = b'PATCH'
IPS_EOF = b'EOF'
IPS_MAX_SIZE = 0x1000000  # 16MB max size

def apply_ips_patch(rom_path, patch_path, output_path):
    """Apply an IPS patch to a ROM file.
    
    Args:
        rom_path: Path to the original ROM
        patch_path: Path to the IPS patch file
        output_path: Path to write the patched ROM
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # First, make a copy of the original ROM
        shutil.copy(rom_path, output_path)
        
        # Open the patch file
        with open(patch_path, 'rb') as patch_file:
            # Verify IPS header
            header = patch_file.read(5)
            if header != IPS_HEADER:
                print(f"Error: {patch_path} is not a valid IPS patch file")
                return False
            
            # Open the output file for binary update
            with open(output_path, 'r+b') as rom_file:
                while True:
                    # Read offset (3 bytes)
                    offset_bytes = patch_file.read(3)
                    if offset_bytes == IPS_EOF:
                        break  # End of patch
                    if len(offset_bytes) < 3:
                        print("Error: Unexpected end of patch file")
                        return False
                    
                    # Convert offset bytes to integer
                    offset = int.from_bytes(offset_bytes, byteorder='big')
                    
                    # Read size (2 bytes)
                    size_bytes = patch_file.read(2)
                    if len(size_bytes) < 2:
                        print("Error: Unexpected end of patch file")
                        return False
                    
                    size = int.from_bytes(size_bytes, byteorder='big')
                    
                    if size == 0:
                        # RLE encoding
                        rle_size_bytes = patch_file.read(2)
                        if len(rle_size_bytes) < 2:
                            print("Error: Unexpected end of patch file")
                            return False
                        
                        rle_size = int.from_bytes(rle_size_bytes, byteorder='big')
                        
                        value = patch_file.read(1)
                        if len(value) < 1:
                            print("Error: Unexpected end of patch file")
                            return False
                        
                        # Seek to offset and write RLE data
                        rom_file.seek(offset)
                        rom_file.write(value * rle_size)
                    else:
                        # Normal data chunk
                        data = patch_file.read(size)
                        if len(data) < size:
                            print("Error: Unexpected end of patch file")
                            return False
                        
                        # Seek to offset and write data
                        rom_file.seek(offset)
                        rom_file.write(data)
        
        print(f"Successfully applied patch to {output_path}")
        return True
    
    except Exception as e:
        print(f"Error applying patch: {e}")
        return False

def main():
    # Paths
    rom_path = "Pokemon Red.gb"
    output_path = "Pokemon Red Color.gb"
    
    # Check which patch to use
    print("Available patches:")
    print("1. Vanilla color patch (original sprites)")
    print("2. Gen 2 color patch (Gen 2 sprites + EXP bar)")
    
    choice = input("Select patch (1 or 2, default=2): ").strip() or "2"
    
    if choice == "1":
        patch_path = "pokered_color/pokered_color_vanilla.ips"
        patch_name = "vanilla color"
    else:
        patch_path = "pokered_color/pokered_color_gen2.ips"
        patch_name = "Gen 2 color"
    
    # Check if files exist
    if not os.path.exists(rom_path):
        print(f"Error: Original ROM not found at {rom_path}")
        return False
    
    if not os.path.exists(patch_path):
        print(f"Error: Patch file not found at {patch_path}")
        return False
    
    # Apply the patch
    print(f"Applying {patch_name} patch to {rom_path}...")
    if apply_ips_patch(rom_path, patch_path, output_path):
        print(f"\nSuccess! Patched ROM saved to: {output_path}")
        print("\nYou can now use this ROM with the enhanced emulator scripts:")
        print("./standalone_emulator_enhanced.py")
        print("./pokemon_ai_enhanced.py")
        return True
    else:
        print("\nFailed to apply patch.")
        return False

if __name__ == "__main__":
    main()