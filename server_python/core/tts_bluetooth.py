import asyncio
import edge_tts
import io
import pydub
import numpy as np
import sounddevice as sd  # pip install sounddevice

class TextToSpeechBluetooth:
    def __init__(self, voice="es-AR-TomasNeural", device_index=None):
        self.voice = voice
        self.device_index = device_index  # Índice del dispositivo Bluetooth en la PC
        
    def generate_and_play(self, text):
        # 1. Generar audio con EdgeTTS
        print(f"🗣️ Generando audio para: {text}")
        mp3_data = asyncio.run(self._generate_edge_tts(text))
        
        # 2. Convertir a numpy array (float32, 16 kHz, mono)
        audio = pydub.AudioSegment.from_mp3(io.BytesIO(mp3_data))
        audio = audio.set_frame_rate(44100).set_channels(2)  # Bluetooth A2DP espera estéreo
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        samples = samples / 32768.0  # Normalizar a -1 a 1
        
        # 3. Reproducir por Bluetooth
        print("🔊 Reproduciendo por Bluetooth...")
        sd.play(samples, samplerate=44100, device=self.device_index)
        sd.wait()  # Esperar a que termine
        print("✅ Reproducción completada")
    
    async def _generate_edge_tts(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data