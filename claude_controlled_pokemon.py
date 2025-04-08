#!/usr/bin/env python3
"""
AI-controlled Pokemon gameplay using enhanced emulator.
This script uses the OpenAI API to make gameplay decisions.
"""

import os
import time
import sys
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import requests
import json
import dotenv
from enhanced_ai import PokemonAI
import openai  # Changed from anthropic to openai

# Load environment variables from .env file
dotenv.load_dotenv()

# Configure ROM paths
ORIGINAL_ROM = os.environ.get("ORIGINAL_ROM", "Pokemon Red.gb")
COLOR_ROM = os.environ.get("COLOR_ROM", "Pokemon Red Color.gb")

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GPT_MODEL = os.environ.get("GPT_MODEL", "gpt-4o")
print(f"*** DEBUG: Loaded GPT_MODEL as: {GPT_MODEL} ***")

class AIControlledPokemon:
    def __init__(self, ai_instance):
        """Initialize with a PokemonAI instance"""
        self.ai = ai_instance
        self.prev_screen = None
        self.last_decision = None  # Store last decision from AI
        self.decision_history = []  # Store multiple past decisions
        self.retry_count = 0  # Track retry attempts
        self.max_retries = 3  # Maximum number of retries
        self.base_delay = 2  # Base delay in seconds
        self.system_prompt = """
You are controlling a character in Pokemon Red. You have access to the current game state through RAM values and a screen capture.
Your task is to decide the best next action based on the game state.

You will receive a history of your previous decisions. Use this context to make more informed decisions, avoid repeating failed strategies, and build upon successful ones. Each decision should consider what worked or didn't work in previous attempts.

IMPORTANT: Always check the screen image carefully for:
1. Walls, trees, water, or other obstacles that block movement
2. Interactive elements like bookshelves, NPCs, or items
3. The player character (in red) and their surroundings
4. Any visual cues that indicate you can't move in a particular direction

Analyze the game state and determine what's happening:
1. What is the player's current position and direction?
2. What is the current menu or dialogue state?
3. What is the overall game state?
4. Are there any obstacles or interactive elements nearby?

Based on your analysis, choose ONE of the following actions:
- up: Move up (check if blocked by obstacles)
- down: Move down (check if blocked by obstacles)
- left: Move left (check if blocked by obstacles)
- right: Move right (check if blocked by obstacles)
- a: Select/Confirm (A button) - Use for interacting with items/NPCs
- b: Back/Cancel (B button)
- start: Open menu (Start button)
- select: Secondary menu (Select button)
- wait: Do nothing for this frame

Special handling for game states:
- If in dialogue, use 'a' to advance text
- If in menu, navigate using direction keys and 'a' to select
- If on world map, use direction keys to move
- If blocked by obstacles, find an alternative path
- If near interactive elements, consider using 'a' to interact

RESPONSE FORMAT:
You MUST follow this EXACT format:

Current Analysis:
[Your analysis of the current game state]

Decision:
[Your reasoning for the chosen action]

Selected Action: [action]

CRITICAL:
1. The "Selected Action:" line MUST be the last line of your response
2. It MUST be followed by a single action, e.g., "Selected Action: up"
3. Each action must be exactly one of: up, down, left, right, a, b, start, select, wait
4. The format must be "Selected Action: action" - the space after the colon is required
5. Do not add any explanations or text after the selected action line

Example response:
Current Analysis:
The player is in dialogue with Professor Oak. The text box shows "Welcome to the world of POKEMON!" and needs to be advanced.

Decision:
Since we're in dialogue, I need to press the A button to advance the text and continue with Professor Oak's introduction.

Selected Action: a

FAILURE TO FOLLOW THIS FORMAT WILL RESULT IN INCORRECT GAME CONTROL.
"""

    def _screen_to_base64(self, screen_array):
        """Convert screen numpy array to base64 string for API"""
        img = Image.fromarray(screen_array)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _detect_screen_change(self, current_screen):
        """Detect if the screen has changed significantly from the previous screen"""
        if self.prev_screen is None:
            self.prev_screen = current_screen
            return True
            
        # Calculate the mean absolute difference between current and previous screens
        diff = np.abs(current_screen.astype(np.float32) - self.prev_screen.astype(np.float32))
        mean_diff = np.mean(diff)
        
        # Update previous screen
        self.prev_screen = current_screen
        
        # If mean difference is above threshold, consider it a significant change
        return mean_diff > 10.0  # Threshold value may need tuning
    
    def _extract_action_from_response(self, response_text):
        """Extract a valid action from GPT's response text"""
        valid_actions = ["up", "down", "left", "right", "a", "b", "start", "select", "wait"]
        
        # Convert to lowercase for case-insensitive matching
        response_lower = response_text.lower()
        
        # First try to look for a more structured format like "action: up" or "chosen action: up"
        action_indicators = ["action:", "chosen action:", "selected action:", "recommended action:"]
        
        for indicator in action_indicators:
            if indicator in response_lower:
                # Find the line with the indicator
                for line in response_lower.split('\n'):
                    if indicator in line:
                        # Extract everything after the indicator
                        action_part = line.split(indicator)[1].strip()
                        # Check if any valid action is in this part
                        for action in valid_actions:
                            if action in action_part.split():
                                print(f"Found structured action format: {indicator} {action}")
                                return action
        
        # Try to find any valid action mentioned in the response
        for action in valid_actions:
            if action in response_lower:
                print(f"GPT's analysis:\n{response_text[:200]}...\n")
                print(f"Selected action: {action}")
                return action
                
        # If no valid action found, default to wait
        print(f"GPT's analysis (no clear action):\n{response_text[:200]}...\n")
        print("Defaulting to 'wait'")
        return "wait"
    
    def _get_decision_history_context(self):
        """Get the decision history context"""
        if not self.decision_history or len(self.decision_history) == 0:
            if not self.last_decision:
                return "No previous decisions.\n"
            return f"Last: {self.last_decision}\n"
            
        # Format the last 3 decisions (or all if fewer)
        history_context = "Decision History:\n"
        recent_decisions = self.decision_history[-3:] if len(self.decision_history) > 3 else self.decision_history
        
        for i, decision in enumerate(recent_decisions):
            index = len(self.decision_history) - len(recent_decisions) + i + 1
            # Use a shortened version for brevity
            if i < len(recent_decisions) - 1:  # For older decisions
                decision_summary = decision.split('\n')[0] if '\n' in decision else decision
                history_context += f"{index}: {decision_summary}\n"
            else:  # For the most recent decision, include more context
                decision_paragraphs = decision.split('\n\n')
                decision_summary = decision_paragraphs[0] if decision_paragraphs else decision
                history_context += f"{index} (Most Recent): {decision_summary}\n"
                
        return history_context
    
    def call_ai_api(self, game_state):
        """Call OpenAI API to get the next action"""
        if not OPENAI_API_KEY:
            print("Error: OPENAI_API_KEY environment variable not set")
            return "wait"
            
        try:
            # Initialize the OpenAI client
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            # Get decision history context
            history_context = self._get_decision_history_context()
            
            # Get current screen and convert to base64
            screen = self.ai.get_screen()
            screen_base64 = self._screen_to_base64(screen)
            
            # Print debug info about the request
            print(f"Sending request to OpenAI API with model: {GPT_MODEL}")
            print(f"Decision history length: {len(self.decision_history)}")
            print(f"History context:\n{history_context}")
            
            # Create the message using the client with game state, last decision, and screen image
            message = client.chat.completions.create(
                model=GPT_MODEL,
                max_tokens=150,
                temperature=1,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": f"{history_context}\nState:\n{game_state}"
                            },
                            {
                                "type": "image_url",
                                "image_url": f"data:image/png;base64,{screen_base64}"
                            }
                        ]
                    }
                ]
            )
            
            # Extract the response
            response_text = message.choices[0].message.content
            
            # Process the response to extract the action
            action = self._extract_action_from_response(response_text)
            
            # Store the full response in decision history (up to 10 decisions)
            if response_text:
                self.last_decision = response_text
                self.decision_history.append(response_text)
                if len(self.decision_history) > 10:
                    self.decision_history.pop(0)  # Remove oldest decision
            
            # Reset retry count on successful call
            self.retry_count = 0
            
            return action
            
        except Exception as e:
            error_str = str(e)
            if "rate_limit_exceeded" in error_str or "server_error" in error_str:
                self.retry_count += 1
                if self.retry_count <= self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.base_delay * (2 ** (self.retry_count - 1))
                    print(f"OpenAI API error (attempt {self.retry_count}/{self.max_retries}), waiting {delay} seconds...")
                    time.sleep(delay)
                    return self.call_ai_api(game_state)  # Retry with backoff
                else:
                    print("Max retries reached, defaulting to wait")
                    return "wait"
            print(f"API Error: {error_str}")
            return "wait"  # Default to waiting if there's an error
    
    def run_gameplay_loop(self, max_steps=100, step_delay=1.0):
        """Run the main gameplay loop with AI making decisions"""
        print("\n===== AI-Controlled Pokemon Gameplay =====")
        print("AI will analyze screen captures and make gameplay decisions")
        print(f"Running for up to {max_steps} steps with {step_delay}s delay between steps")
        print("Press CTRL+C to exit\n")
        
        for step in range(max_steps):
            try:
                print(f"\nStep {step+1}/{max_steps}:")
                
                # Get current screen
                screen = self.ai.get_screen()
                
                # Ask AI for next action
                action = self.call_ai_api(screen)
                
                # Execute the action
                if action != "wait":
                    self.ai.press_button(action, duration=0.2)
                
                # Wait between steps
                time.sleep(step_delay)
                
            except KeyboardInterrupt:
                print("\nGameplay interrupted by user")
                break
        
        print("\nGameplay session complete")

def main():
    # Determine which ROM to use
    use_color = os.path.exists(COLOR_ROM)
    rom_path = COLOR_ROM if use_color else ORIGINAL_ROM
    
    print(f"Using ROM: {rom_path}")
    
    # Check for OpenAI API key
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY environment variable not set.")
        print("Please set it before running this script.")
        print("Example: export OPENAI_API_KEY=your-api-key-here")
        return
    
    # Check for saved state
    load_state = False
    state_path = f"{rom_path}.state"
    if os.path.exists(state_path):
        choice = input(f"Found save state at {state_path}. Load it? (y/n) [default=n]: ").strip().lower()
        load_state = choice == 'y'
    
    # Initialize the Pokemon AI
    ai = PokemonAI(rom_path, use_color=use_color, load_saved_state=load_state)
    
    # Start the game
    if not ai.start_game():
        print("Failed to start the game")
        return
    
    try:
        # Only press START if we're not loading a saved state
        if not load_state:
            time.sleep(1)
            print("Pressing START to begin game...")
            ai.press_button('start', duration=0.5)
            time.sleep(2)
        
        # Create and run the AI-controlled gameplay
        ai_player = AIControlledPokemon(ai)
        ai_player.run_gameplay_loop(max_steps=50, step_delay=2.0)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        ai.stop()
        print("Game stopped and progress saved")

if __name__ == "__main__":
    main()