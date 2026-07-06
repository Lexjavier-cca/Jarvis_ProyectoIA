"""
TEST DE LOOPBACK A ESP32 (VERSIÓN MEJORADA)
- Busca automáticamente el dispositivo de loopback
- Permite selección manual
- Captura audio y lo envía por WebSocket al ESP32
"""

import asyncio
import numpy as np
import sounddevice as sd
import websockets
import time
import sys

# ========= CONFIGURACIÓN =========
ESP32_IP = "192.168.100.18"
ESP32_PORT = 8765
DURATION = 5.0
SAMPLE_RATE = 16000
CHUNK_SIZE = 256

# ========= FUNCIÓN PARA ENCONTRAR LOOPBACK =========
def find_loopback_device():
    """Busca un dispositivo de loopback por nombre."""
    devices = sd.query_devices()
    input_devices = []
    
    print("\n🎤 Dispositivos de ENTRADA disponibles:")
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devices.append((i, dev))
            print(f"  [{i}] {dev['name']} (canales: {dev['max_input_channels']})")
    
    # Buscar loopback por nombres comunes
    keywords = ['loopback', 'mezcla', 'stereo mix', 'what u hear', 'capturar', 'stream']
    for idx, dev in input_devices:
        name_lower = dev['name'].lower()
        for keyword in keywords:
            if keyword in name_lower:
                print(f"\n✅ Loopback encontrado: [{idx}] {dev['name']}")
                return idx
    
    # Si no se encuentra, preguntar al usuario
    print("\n⚠️ No se encontró loopback automáticamente.")
    print("Selecciona el índice del dispositivo que quieras usar (o '0' para usar el predeterminado):")
    try:
        choice = int(input("Índice: "))
        if choice == 0:
            return None  # Usar dispositivo predeterminado
        return choice
    except:
        print("❌ Selección inválida. Usando dispositivo predeterminado.")
        return None

# ========= CAPTURAR Y ENVIAR =========
async def capture_and_send():
    # Encontrar loopback
    device_idx = find_loopback_device()
    
    if device_idx is None:
        print("🎤 Usando dispositivo predeterminado de entrada.")
    else:
        print(f"🎤 Usando dispositivo: {sd.query_devices(device_idx)['name']}")
    
    print(f"\n🎧 Capturando audio del sistema durante {DURATION} segundos...")
    print("🔊 REPRODUCE ALGO EN TU PC (música, video, etc.)")
    print("⏳ Grabando...")
    
    try:
        # Capturar audio
        audio_data = sd.rec(
            int(DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16',
            device=device_idx
        )
        sd.wait()
        
        # Verificar que se capturó algo
        if np.max(np.abs(audio_data)) < 10:
            print("⚠️ El audio capturado es muy bajo o silencioso. ¿Estás reproduciendo algo?")
        
        # Convertir a 8-bit PCM
        audio_int16 = np.squeeze(audio_data)
        audio_int8 = ((audio_int16.astype(np.float32) / 32768.0) * 127 + 128).clip(0, 255).astype(np.uint8)
        
        print(f"✅ Audio capturado: {len(audio_int8)} bytes")
        
        # Conectar al ESP32
        uri = f"ws://{ESP32_IP}:{ESP32_PORT}"
        print(f"🔗 Conectando a {uri}...")
        
        async with websockets.connect(uri, timeout=5) as websocket:
            print("✅ Conectado al ESP32")
            
            # Enviar en fragmentos
            print(f"📤 Enviando {len(audio_int8)} bytes en fragmentos de {CHUNK_SIZE}...")
            total_enviado = 0
            for i in range(0, len(audio_int8), CHUNK_SIZE):
                chunk = audio_int8[i:i+CHUNK_SIZE].tobytes()
                await websocket.send(chunk)
                await asyncio.sleep(0.02)
                total_enviado += len(chunk)
                if i % (CHUNK_SIZE * 10) == 0:  # Mostrar progreso cada 10 chunks
                    print(f"  📤 Enviado {total_enviado}/{len(audio_int8)} bytes")
            
            print(f"✅ Audio enviado completamente ({total_enviado} bytes)")
            
    except sd.PortAudioError as e:
        print(f"❌ Error de audio: {e}")
        print("\n🔧 Sugerencias:")
        print("  1. Asegúrate de que el dispositivo de loopback esté habilitado en Windows.")
        print("  2. Ve al mezclador de Realtek HD Audio y activa 'Mezcla estéreo'.")
        print("  3. Prueba con otro dispositivo de entrada (ej. el micrófono).")
    except Exception as e:
        print(f"❌ Error: {e}")

# ========= EJECUTAR =========
if __name__ == "__main__":
    print("=" * 60)
    print("🔊 TEST DE LOOPBACK A ESP32 (V2)")
    print("=" * 60)
    asyncio.run(capture_and_send())