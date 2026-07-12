import faster_whisper
import pyaudio
import numpy as np
from faster_whisper import WhisperModel

# ============================================================
# MODELO COMPARTIDO (para evitar recargar)
# ============================================================
_whisper_model = None

def get_whisper_model(model_size="base"):  # Cambiado a "base" para mejor precisión
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _whisper_model

# ============================================================
# TRANSCRIBIR DESDE BYTES (para clientes web)
# ============================================================
def transcribe_audio_bytes(audio_bytes, sample_rate=16000):
    """
    Transcribe audio desde bytes (16-bit PCM, mono) usando Faster Whisper.
    Forzado a español para evitar confusiones con italiano/portugués.
    """
    if not audio_bytes:
        return None
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    model = get_whisper_model()
    segments, info = model.transcribe(
        audio_np,
        language="es",          # Forzar español
        task="transcribe",
        beam_size=5,
        best_of=5,
        temperature=0.0
    )
    text = " ".join([seg.text for seg in segments])
    return text.strip() if text else None

# ============================================================
# CLASE PARA MICRÓFONO LOCAL (laptop)
# ============================================================
class SpeechToText:
    def __init__(self, model_size="base"):  # Cambiado a "base"
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
        segments, info = self.model.transcribe(
            audio_np,
            language="es",
            task="transcribe",
            beam_size=5
        )
        text = " ".join([seg.text for seg in segments])
        if text.strip():
            return text.strip()
        return None