"""
Test de audio: Captura lo que suena en la PC y lo envía al ESP32
Requisitos: pip install pyaudio numpy websockets
"""

import pyaudio
import numpy as np
import asyncio
import websockets
import time
import wave

# ========= CONFIGURACIÓN =========
ESP32_IP = "192.168.100.18"
ESP32_PORT = 8765
SAMPLE_RATE = 22050  # Debe coincidir con el firmware del ESP32
CHUNK = 512          # Tamaño del buffer de captura
DURATION = 5         # Segundos de captura

# ========= CAPTURAR AUDIO DEL SISTEMA (LOOPBACK) =========
def capture_system_audio(duration=5, sample_rate=22050):
    """
    Captura el audio que está sonando en la PC (loopback).
    En Windows, se necesita el dispositivo "Stereo Mix" o "Cable de audio virtual".
    """
    p = pyaudio.PyAudio()
    
    # Listar dispositivos disponibles
    print("🎤 Dispositivos de audio disponibles:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"  [{i}] {info['name']} (maxInputChannels={info['maxInputChannels']})")
    
    # Encontrar dispositivo de loopback (Windows: Stereo Mix, Cable Input, etc.)
    device_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info['name'].lower()
        if 'stereo mix' in name or 'loopback' in name or 'cable' in name:
            device_index = i
            print(f"✅ Usando dispositivo: {info['name']}")
            break
    
    if device_index is None:
        print("⚠️ No se encontró dispositivo de loopback. Usando micrófono por defecto.")
        device_index = p.get_default_input_device_info()['index']
    
    # Abrir stream para capturar
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK
    )
    
    print(f"🎧 Capturando audio del sistema durante {duration} segundos...")
    frames = []
    for _ in range(0, int(sample_rate / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Convertir a bytes y guardar WAV (opcional)
    audio_data = b''.join(frames)
    
    # Guardar como WAV para depuración
    with wave.open("captura_sistema.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)
    print("💾 Audio guardado como 'captura_sistema.wav'")
    
    # Convertir de 16-bit a 8-bit PCM (para el ESP32)
    audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
    audio_int8 = ((audio_int16 / 256) + 128).astype(np.uint8)
    return audio_int8.tobytes()

# ========= ENVIAR AL ESP32 POR WEBSOCKET =========
async def send_to_esp32(audio_bytes):
    print(f"📤 Enviando {len(audio_bytes)} bytes al ESP32...")
    uri = f"ws://{ESP32_IP}:{ESP32_PORT}"
    
    try:
        async with websockets.connect(uri, timeout=10) as websocket:
            print("✅ Conectado al ESP32")
            
            # Enviar en fragmentos de 256 bytes con pausa de 30ms
            chunk_size = 256
            total = len(audio_bytes)
            for i in range(0, total, chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.03)
            
            print("✅ Audio enviado completamente")
            
            # Esperar 2 segundos para que el ESP32 reproduzca
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"❌ Error: {e}")

# ========= PROBAR CON BLUETOOTH =========
def play_on_bluetooth(audio_bytes):
    """Reproduce el audio capturado por el altavoz Bluetooth."""
    import sounddevice as sd
    import numpy as np
    
    # Convertir 8-bit a float32
    audio_float = (np.frombuffer(audio_bytes, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    
    print("🔊 Reproduciendo por Bluetooth...")
    sd.play(audio_float, samplerate=22050)
    sd.wait()
    print("✅ Reproducción completada")

# ========= MENÚ PRINCIPAL =========
def main():
    print("="*60)
    print("🔊 TEST DE CAPTURA Y ENVÍO DE AUDIO")
    print("="*60)
    print("1. Capturar audio del sistema y enviar por WebSocket al ESP32")
    print("2. Capturar audio del sistema y reproducir por Bluetooth local")
    print("3. Solo capturar y guardar WAV (sin enviar)")
    
    option = input("Selecciona una opción (1/2/3): ").strip()
    
    # Capturar audio
    audio_bytes = capture_system_audio(duration=5, sample_rate=22050)
    
    if option == "1":
        print("\n📡 Enviando por WebSocket al ESP32...")
        asyncio.run(send_to_esp32(audio_bytes))
        
    elif option == "2":
        print("\n🔊 Reproduciendo por Bluetooth en la PC...")
        try:
            play_on_bluetooth(audio_bytes)
        except ImportError:
            print("❌ sounddevice no instalado. Ejecuta: pip install sounddevice")
        except Exception as e:
            print(f"❌ Error al reproducir: {e}")
            
    else:
        print("\n✅ Audio guardado como 'captura_sistema.wav'. Revisa el archivo.")

if __name__ == "__main__":
    main()