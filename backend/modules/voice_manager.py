"""
voice_manager.py — THING Jarvis Upgrade
Manages voice selection, character mapping, and Hinglish preferences.
"""

from typing import Dict, Any

# Recommended Premium Neural Voices (Microsoft Edge TTS)
# en-IN: English (India) - Great for Hinglish
# en-US: English (US) - Classic Jarvis style
# hi-IN: Hindi (India) - Best for pure Hindi

VOICE_MODELS = {
    "male": {
        "en-IN": "en-IN-PrabhatNeural",
        "en-US": "en-US-GuyNeural",
        "en-GB": "en-GB-RyanNeural",
        "hi-IN": "hi-IN-MadhurNeural",
    },
    "female": {
        "en-IN": "en-IN-NeerjaNeural",
        "en-US": "en-US-AriaNeural",
        "en-GB": "en-GB-SoniaNeural",
        "hi-IN": "hi-IN-SwaraNeural",
    }
}

class VoiceManager:
    def __init__(self):
        # Default settings
        self.gender = "male"
        self.language = "en-IN"
        self.rate = "+0%"
        self.pitch = "+0Hz"
        self.volume = "+0%"
        self.load_preferences()

    def load_preferences(self):
        """Loads voice preferences from memory engine."""
        from backend.engine.memory_engine import memory
        prefs = memory.memory.get("voice_settings", {})
        self.gender = prefs.get("gender", "male")
        self.language = prefs.get("language", "en-IN")
        self.rate = prefs.get("rate", "+0%")
        self.pitch = prefs.get("pitch", "+0Hz")
        self.volume = prefs.get("volume", "+0%")

    def save_preferences(self):
        """Saves current settings to memory engine."""
        from backend.engine.memory_engine import memory
        memory.memory["voice_settings"] = {
            "gender": self.gender,
            "language": self.language,
            "rate": self.rate,
            "pitch": self.pitch,
            "volume": self.volume
        }
        memory.save_memory()

    def get_voice(self) -> str:
        """Returns the specific neural voice string."""
        return VOICE_MODELS.get(self.gender, VOICE_MODELS["male"]).get(self.language, "en-IN-PrabhatNeural")

    def update_settings(self, settings: Dict[str, Any]):
        """Updates settings from frontend."""
        if "gender" in settings: self.gender = settings["gender"]
        if "language" in settings: self.language = settings["language"]
        if "rate" in settings: self.rate = settings["rate"]
        if "pitch" in settings: self.pitch = settings["pitch"]
        if "volume" in settings: self.volume = settings["volume"]
        self.save_preferences()

# Singleton
voice_manager = VoiceManager()
