import faster_whisper
import pyaudio
import numpy as np

class SpeechToText:
    def __init__(self, model_size="tiny"):
        self.model = faster_whisper.WhisperModel(model_size, device="cpu", compute_type="int8")
        self.audio = pyaudio.PyAudio()
        
    def listen_and_transcribe(self, duration=5.0):
        print("🎤 Escuchando... (habla ahora)")
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        frames = []
        for _ in range(0, int(16000 / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        segments, info = self.model.transcribe(audio_np, language="es", beam_size=5)
        text = " ".join([seg.text for seg in segments])
        if text.strip():
            return text.strip()
        return None
