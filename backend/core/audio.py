import speech_recognition as sr
import threading
import asyncio
import os
import time
from backend.modules.tts_provider import tts_provider
from backend.modules.voice_manager import voice_manager


class AudioEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

        self.speak_thread = None
        self.is_speaking = False
        self._speak_lock = threading.Lock()

        # Callbacks for UI updates — set by server.py
        self.on_status_change = None

    # ─────────────────────────────────────────────
    #  Neural TTS
    # ─────────────────────────────────────────────

    def _speak_async_worker(self, text: str):
        """Internal TTS worker — handles generation and playback."""
        try:
            # Create a new event loop for this thread to handle edge-tts async calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            with self._speak_lock:
                self.is_speaking = True

            if self.on_status_change:
                self.on_status_change("speaking", text[:60])

            print(f"THING: {text}")

            # 1. Generate high-quality audio file
            audio_file = loop.run_until_complete(tts_provider.generate_speech(text))
            
            # 2. Play the audio
            if audio_file:
                tts_provider.play_audio(audio_file)

        except Exception as e:
            print(f"[Audio] Neural TTS error: {e}")
        finally:
            with self._speak_lock:
                self.is_speaking = False
            if self.on_status_change:
                self.on_status_change("idle", "")
            loop.close()

    def speak(self, text: str, rate: int = 1):
        """Interrupt current speech and speak new text using Neural TTS."""
        if not text:
            return
            
        self.stop_speaking()
        
        self.speak_thread = threading.Thread(
            target=self._speak_async_worker, args=(text,), daemon=True
        )
        self.speak_thread.start()

    def stop_speaking(self):
        """Interrupts current playback gracefully."""
        try:
            tts_provider.stop()
            with self._speak_lock:
                self.is_speaking = False
            if self.on_status_change:
                self.on_status_change("idle", "")
        except Exception as e:
            print(f"[Audio] Stop error: {e}")

    # ─────────────────────────────────────────────
    #  STT
    # ─────────────────────────────────────────────

    def listen_for_command(self, timeout: int = 6) -> str:
        """
        Listens for a single voice command.
        Returns empty string on timeout or unrecognized audio.
        """
        try:
            if self.is_speaking:
                time.sleep(0.5)
                return ""
            
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)

                if self.on_status_change:
                    self.on_status_change("listening", "Listening...")

                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=10
                )

                if self.on_status_change:
                    self.on_status_change("processing", "Processing...")

                text = self.recognizer.recognize_google(audio).lower().strip()
                return text

        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"[Audio] STT error: {e}")
        finally:
            if self.on_status_change and not self.is_speaking:
                self.on_status_change("idle", "")

        return ""


# Global singleton
audio = AudioEngine()
