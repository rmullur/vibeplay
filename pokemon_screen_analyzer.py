#!/usr/bin/env python3
"""
Pokemon Screen Analyzer - Tools to analyze Pokemon Red/Blue screens.
This helps Claude better understand the game state.
"""

import numpy as np
from PIL import Image
import cv2
import os
import time

class PokemonScreenAnalyzer:
    def __init__(self):
        """Initialize the screen analyzer with known game regions"""
        # Define regions of interest in the screen for analysis
        self.regions = {
            "dialogue_box": (112, 112, 144, 32),  # (y, h, x, w) - bottom text area
            "menu_region": (40, 80, 80, 70),      # (y, h, x, w) - typical menu location
        }
        
        # Color thresholds for detecting specific elements
        self.white_threshold = 240  # For detecting white text/UI elements
        self.black_threshold = 30   # For detecting black text/UI elements
        
    def detect_dialogue(self, screen_array):
        """Detect if a dialogue box is present at the bottom of the screen"""
        y, h, x, w = self.regions["dialogue_box"]
        dialogue_region = screen_array[y:y+h, x:x+w]
        
        # Check for alternating black and white pixels (typical for text boxes)
        # Calculate standard deviation of pixel values - high std dev indicates text
        std_dev = np.std(dialogue_region)
        
        # Check for white border pattern at the top of the region
        top_row = dialogue_region[0:2, :]
        white_border_pixels = np.sum(top_row > self.white_threshold)
        
        has_text_box = std_dev > 50 and white_border_pixels > (w * 0.7)
        confidence = min(100, max(0, int((std_dev - 40) * 2))) if white_border_pixels > (w * 0.7) else 0
        
        return {
            "detected": has_text_box,
            "confidence": confidence,
            "details": f"Std dev: {std_dev:.1f}, White border: {white_border_pixels}/{w*2}"
        }
        
    def detect_menu(self, screen_array):
        """Detect if a menu is open on the screen"""
        y, h, x, w = self.regions["menu_region"]
        menu_region = screen_array[y:y+h, x:x+w]
        
        # Look for rectangular white regions with black text
        white_pixels = np.sum(menu_region > self.white_threshold)
        black_pixels = np.sum(menu_region < self.black_threshold)
        
        # Menus typically have white backgrounds with black text
        total_pixels = h * w
        white_percentage = (white_pixels / total_pixels) * 100
        black_percentage = (black_pixels / total_pixels) * 100
        
        # Check if percentages match expected menu patterns
        # Menus typically have 60-80% white with 10-20% black text
        is_menu = (white_percentage > 50 and black_percentage > 5)
        confidence = min(100, max(0, int(white_percentage - 40))) if is_menu else 0
        
        return {
            "detected": is_menu,
            "confidence": confidence,
            "details": f"White: {white_percentage:.1f}%, Black: {black_percentage:.1f}%"
        }
        
    def detect_battle(self, screen_array):
        """Detect if the player is in a battle - disabled"""
        # Battle detection removed
        return {
            "detected": False,
            "confidence": 0,
            "details": "Battle detection disabled"
        }
        
    def detect_world_map(self, screen_array, dialogue_result):
        """Detect if the player is on the world map (overworld)"""
        # World map is assumed when no dialogue, no menu, and no battle
        # Check for characteristic outdoor/town patterns or indoor patterns
        
        # Calculate color distribution - outdoor areas typically have more greens
        mean_colors = np.mean(screen_array, axis=(0, 1))
        
        # Check for tilemap patterns (grid-like structures)
        # This is a simplified approach - real detection would be more complex
        horizontal_edges = cv2.Sobel(screen_array, cv2.CV_64F, 1, 0, ksize=3)
        vertical_edges = cv2.Sobel(screen_array, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(horizontal_edges**2 + vertical_edges**2)
        edge_mean = np.mean(edge_magnitude)
        
        # Grid-like structures have strong regular edges
        is_grid_like = edge_mean > 15
        
        # No dialogue suggests world map navigation
        is_world_map = not dialogue_result["detected"] and is_grid_like
        confidence = min(100, max(0, int(edge_mean * 2))) if is_world_map else 0
        
        green_bias = (mean_colors[1] > mean_colors[0]) and (mean_colors[1] > mean_colors[2])
        environment_type = "outdoor" if green_bias else "indoor"
        
        return {
            "detected": is_world_map,
            "confidence": confidence,
            "environment": environment_type,
            "details": f"Edge mean: {edge_mean:.1f}, Green bias: {green_bias}"
        }
    
    def detect_pyboy_splash(self, screen_array):
        """Detect if we're on the PyBoy splash screen"""
        # The PyBoy splash screen typically has a dark background with white text
        # Check the center region of the screen
        height, width = screen_array.shape[:2]
        center_y = height // 2
        center_x = width // 2
        region = screen_array[center_y-20:center_y+20, center_x-40:center_x+40]
        
        # Calculate the ratio of white pixels (text) to total pixels
        white_pixels = np.sum(region > self.white_threshold)
        total_pixels = region.shape[0] * region.shape[1]
        white_ratio = white_pixels / total_pixels
        
        # The PyBoy splash screen typically has a low ratio of white pixels
        # (just the text) against a dark background
        is_splash = white_ratio < 0.1
        
        return {
            "detected": is_splash,
            "confidence": 100 if is_splash else 0,
            "details": f"White pixel ratio: {white_ratio:.2f}"
        }
    
    def analyze_screen(self, screen_array):
        """Analyze the screen and determine the game context"""
        # First check if we're on the PyBoy splash screen
        splash_result = self.detect_pyboy_splash(screen_array)
        if splash_result["detected"]:
            return {
                "most_likely_state": "splash",
                "confidences": {
                    "splash": 100,
                    "dialogue": 0,
                    "menu": 0,
                    "world_map": 0
                },
                "splash": splash_result,
                "dialogue": {"detected": False, "confidence": 0, "details": ""},
                "menu": {"detected": False, "confidence": 0, "details": ""},
                "world_map": {"detected": False, "confidence": 0, "details": ""}
            }
        
        # Run all detectors
        dialogue_result = self.detect_dialogue(screen_array)
        menu_result = self.detect_menu(screen_array)
        world_map_result = self.detect_world_map(screen_array, dialogue_result)
        
        # Determine the most likely game state based on detector confidences
        state_confidences = {
            "dialogue": dialogue_result["confidence"],
            "menu": menu_result["confidence"],
            "world_map": world_map_result["confidence"]
        }
        
        most_likely_state = max(state_confidences, key=state_confidences.get)
        
        # Return comprehensive analysis results
        return {
            "most_likely_state": most_likely_state,
            "confidences": state_confidences,
            "dialogue": dialogue_result,
            "menu": menu_result,
            "world_map": world_map_result
        }
    
    def get_screen_description(self, screen_array):
        """Generate a text description of the screen for Claude"""
        analysis = self.analyze_screen(screen_array)
        
        # Format the description based on analysis
        description = f"Game state analysis:\n"
        
        if analysis['most_likely_state'] == 'splash':
            description += "- Currently on PyBoy splash screen\n"
            description += f"- Splash screen details: {analysis['splash']['details']}\n"
        else:
            description += f"- Most likely state: {analysis['most_likely_state']} (confidence: {analysis['confidences'][analysis['most_likely_state']]}%)\n"
            
            # Add state-specific details
            if analysis['most_likely_state'] == 'dialogue':
                description += "- A dialogue box is open at the bottom of the screen\n"
                description += f"- Dialogue detection details: {analysis['dialogue']['details']}\n"
                
            elif analysis['most_likely_state'] == 'menu':
                description += "- A menu is open on the screen\n"
                description += f"- Menu detection details: {analysis['menu']['details']}\n"
                
            # Battle detection removed
                
            elif analysis['most_likely_state'] == 'world_map':
                environment = analysis['world_map']['environment']
                description += f"- You are navigating the world map ({environment} area)\n"
                description += f"- World map detection details: {analysis['world_map']['details']}\n"
        
        # Add confidence scores for all states
        description += "\nConfidence scores for all states:\n"
        for state, confidence in analysis['confidences'].items():
            description += f"- {state}: {confidence}%\n"
            
        return description

# Function to save a screen image for debugging
def save_screen_image(screen_array, filename="debug_screen.png"):
    """Save the screen array as an image file for debugging"""
    img = Image.fromarray(screen_array)
    img.save(filename)
    print(f"Saved screen image to {filename}")

# Function to demonstrate usage with a sample screen
def demo_with_sample(sample_image_path):
    """Demonstrate the analyzer with a sample image"""
    if not os.path.exists(sample_image_path):
        print(f"Sample image not found: {sample_image_path}")
        return
        
    # Load the sample image
    img = Image.open(sample_image_path)
    screen_array = np.array(img)
    
    # Create analyzer and get description
    analyzer = PokemonScreenAnalyzer()
    description = analyzer.get_screen_description(screen_array)
    
    print("Screen Analysis Results:")
    print(description)

if __name__ == "__main__":
    # If a sample image is provided as an argument, use it for demonstration
    import sys
    
    if len(sys.argv) > 1:
        sample_image_path = sys.argv[1]
        demo_with_sample(sample_image_path)
    else:
        print("Please provide a sample Pokemon screen image as an argument.")
        print("Example: python pokemon_screen_analyzer.py sample_screen.png")