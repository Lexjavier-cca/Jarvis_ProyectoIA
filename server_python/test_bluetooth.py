import wave
import numpy as np
import os

# Generar un pitido de 440 Hz
duration = 1.0
sample_rate = 44100
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
wave_data = 127 + 100 * np.sin(2 * np.pi * 440 * t)
audio_bytes = wave_data.astype(np.uint8).tobytes()

# Guardar como WAV
with wave.open("test_pitido.wav", "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(1)  # 8-bit
    wf.setframerate(sample_rate)
    wf.writeframes(audio_bytes)

# Reproducir (sonará en el dispositivo Bluetooth predeterminado)
os.startfile("test_pitido.wav")
print("🔊 Pitido reproducido. ¿Se escuchó en el ESP32?")