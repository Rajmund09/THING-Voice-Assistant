"""
tts_provider.py — THING Jarvis Upgrade
Generates high-quality neural speech using Microsoft Edge TTS.
Includes a fast file-based caching system.
"""

import os
import asyncio
import hashlib
import edge_tts
import pygame
from backend.modules.voice_manager import voice_manager

CACHE_DIR = os.path.join("temp", "tts_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class TTSProvider:
    def __init__(self):
        pygame.mixer.init()
        self.lock = asyncio.Lock()

    def _get_cache_path(self, text: str, voice: str, rate: str) -> str:
        """Generates a unique filename for the given speech parameters."""
        hash_input = f"{text}|{voice}|{rate}"
        file_hash = hashlib.md5(hash_input.encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{file_hash}.mp3")

    async def generate_speech(self, text: str) -> str:
        """
        Generates an MP3 file for the given text.
        Returns the path to the generated file.
        """
        voice = voice_manager.get_voice()
        
        # Smart Speech Mode — Tone adjustment based on content
        base_rate = voice_manager.rate
        base_pitch = voice_manager.pitch
        
        current_rate = base_rate
        current_pitch = base_pitch
        
        # 1. Detect emotion/tone (Simple keyword based for speed)
        text_lower = text.lower()
        if any(w in text_lower for w in ["error", "failed", "sorry", "cannot", "unable"]):
            # Calm/Polite: Slower, slightly lower pitch
            current_rate = "-5%"
            current_pitch = "-1Hz"
        elif any(w in text_lower for w in ["yes", "done", "success", "confirmed", "perfect"]):
            # Energetic/Positive: Faster, slightly higher pitch
            current_rate = "+5%"
            current_pitch = "+1Hz"
        elif any(w in text_lower for w in ["!", "wow", "amazing", "great"]):
            # Exciting: Much faster
            current_rate = "+10%"
            current_pitch = "+2Hz"
        
        output_path = self._get_cache_path(text, voice, current_rate)
        
        if os.path.exists(output_path):
            return output_path

        # Add natural pauses for punctuation
        processed_text = text.replace(".", " . ").replace("!", " ! ").replace("?", " ? ")
        
        try:
            print(f"[TTS] Generating with voice: {voice}")
            communicate = edge_tts.Communicate(
                processed_text, 
                voice, 
                rate=current_rate, 
                volume=voice_manager.volume, 
                pitch=current_pitch
            )
            await communicate.save(output_path)
        except Exception as e:
            print(f"[TTS] Generation failed for {voice}: {e}")
            # Fallback to a safe English voice if Hindi fails
            if "hi-IN" in voice:
                print("[TTS] Falling back to en-IN-PrabhatNeural")
                communicate = edge_tts.Communicate(processed_text, "en-IN-PrabhatNeural")
                await communicate.save(output_path)
            else:
                return ""
        
        return output_path

    def play_audio(self, file_path: str):
        """Plays the generated MP3 file using pygame."""
        try:
            if not os.path.exists(file_path):
                return
                
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            print(f"[TTS] Playback error: {e}")

    def stop(self):
        """Stops current playback."""
        pygame.mixer.music.stop()

# Singleton
tts_provider = TTSProvider()
