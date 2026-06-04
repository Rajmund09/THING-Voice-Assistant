import json
import os
from typing import Dict, Any, List

class MemoryEngine:
    def __init__(self, memory_file="memory.json"):
        self.memory_file = memory_file
        # Sandboxed stores
        self.memory: Dict[str, Any] = {
            "preferences": {},
            "chat_history": [],      # For casual talk
            "command_history": [],   # For action tracking
            "context": {}            # App/System state
        }
        self.load_memory()

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    # Merge data ensuring keys exist
                    for key in self.memory.keys():
                        if key in data:
                            self.memory[key] = data[key]
            except Exception as e:
                print(f"Error loading memory: {e}")

    def save_memory(self):
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def add_chat(self, speaker: str, text: str):
        self.memory["chat_history"].append({"speaker": speaker, "text": text})
        if len(self.memory["chat_history"]) > 10: # Keep it short to avoid contamination
            self.memory["chat_history"] = self.memory["chat_history"][-10:]
        
        # Extract preferences if it's the user speaking
        if speaker == "user":
            from backend.engine.context_memory import extract_preferences
            new_prefs = extract_preferences(text)
            if new_prefs:
                self.memory["preferences"].update(new_prefs)
                print(f"[Memory] Updated preferences: {new_prefs}")
                
        self.save_memory()

    def add_command(self, command: str, result: str):
        self.memory["command_history"].append({"cmd": command, "res": result})
        if len(self.memory["command_history"]) > 10:
            self.memory["command_history"] = self.memory["command_history"][-10:]
        self.save_memory()

    def update_context(self, key: str, value: Any):
        self.memory["context"][key] = value
        self.save_memory()

    def get_context(self) -> Dict[str, Any]:
        return self.memory.get("context", {})

    def get_chat_history(self) -> List[Dict[str, str]]:
        return self.memory.get("chat_history", [])

    def clear_context(self):
        self.memory["context"] = {}
        self.save_memory()

# Global memory instance
memory = MemoryEngine()
