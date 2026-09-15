"""Audio capture and transcription for voice intent without timeout limits.
Supports click-to-start and click-to-stop manual toggle recording using sounddevice.
"""

import threading
from typing import Optional, List
import numpy as np
import speech_recognition as sr
import sounddevice as sd


class VoiceRecorder:
    """
    Continuous voice recorder that records until explicitly stopped by the user.
    Uses sounddevice.InputStream for non-blocking, reliable Windows audio capture.
    """
    def __init__(self, samplerate: int = 16000):
        self.samplerate = samplerate
        self.stream: Optional[sd.InputStream] = None
        self.is_recording = False
        self.audio_chunks: List[np.ndarray] = []
        self._lock = threading.Lock()

    def start_recording(self) -> bool:
        with self._lock:
            if self.is_recording:
                return True
            self.audio_chunks = []
            self.is_recording = True

            def callback(indata, frames, time_info, status):
                if status:
                    pass
                if self.is_recording:
                    self.audio_chunks.append(indata.copy())

            try:
                self.stream = sd.InputStream(
                    samplerate=self.samplerate,
                    channels=1,
                    dtype="int16",
                    callback=callback
                )
                self.stream.start()
                print("[Voice] Manual recording started (speak freely, click stop when done)...")
                return True
            except Exception as e:
                print(f"[Voice] Could not start audio stream: {e}")
                self.is_recording = False
                self.stream = None
                return False

    def stop_and_transcribe(self) -> Optional[str]:
        with self._lock:
            if not self.is_recording:
                return None
            self.is_recording = False
            stream_to_close = self.stream
            self.stream = None

        if stream_to_close:
            try:
                stream_to_close.stop()
                stream_to_close.close()
            except Exception as e:
                print(f"[Voice] Error closing stream: {e}")

        if not self.audio_chunks:
            print("[Voice] No audio chunks captured.")
            return None

        # Stitch all recorded PCM slices together
        full_audio = np.concatenate(self.audio_chunks, axis=0)
        duration_sec = len(full_audio) / self.samplerate
        print(f"[Voice] Recording stopped. Total duration: {duration_sec:.2f} seconds.")

        max_amplitude = int(np.max(np.abs(full_audio))) if len(full_audio) > 0 else 0
        print(f"[Voice] Peak amplitude: {max_amplitude}")

        if max_amplitude < 20:
            print("[Voice] Microphone recorded silence or muted.")
            return None

        # Normalize gain if speech was quiet
        if 0 < max_amplitude < 15000:
            gain = min(15000 / max_amplitude, 10.0)
            boosted = np.clip(full_audio.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
            audio_bytes = boosted.tobytes()
        else:
            audio_bytes = full_audio.tobytes()

        recognizer = sr.Recognizer()
        audio_data = sr.AudioData(audio_bytes, self.samplerate, 2)

        try:
            print("[Voice] Transcribing speech with Google Speech API...")
            text = recognizer.recognize_google(audio_data)
            text = text.strip() if text else None
            print(f"[Voice] Transcribed text: '{text}'")
            return text
        except sr.UnknownValueError:
            print("[Voice] Speech was unclear or could not be recognized.")
            return None
        except sr.RequestError as e:
            print(f"[Voice] Speech API network error: {e}")
            return None
        except Exception as e:
            print(f"[Voice] Transcription error: {e}")
            return None


# Global singleton instance for easy import
global_recorder = VoiceRecorder()


def record_and_transcribe(duration_seconds: float = 3.5, samplerate: int = 16000) -> Optional[str]:
    """Legacy helper function with fixed duration fallback."""
    recorder = VoiceRecorder(samplerate=samplerate)
    recorder.start_recording()
    import time
    time.sleep(duration_seconds)
    return recorder.stop_and_transcribe()
