"""
Jarvis Server - Main Entry Point (WebSocket + PCM)
Genera audio, lo envía al ESP32 por WebSocket y lo reproduce con normalización.
"""

import asyncio
import threading
import uvicorn
import webbrowser
import urllib.parse
import os
import time
import wave
import pygame
import numpy as np
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from websocket.manager import ws_manager
from dashboard.app import router as dashboard_router
from core.wakeword import WakeWordDetector
from core.stt import SpeechToText
from core.tts import TextToSpeech
from core.nlp import IntentClassifier
from windows.controller import WindowsController

# ========= CONFIGURACIÓN =========
ESP32_IP = "192.168.100.20"   # <--- CAMBIA POR LA IP DE TU ESP32
ESP32_PORT = 8765

main_event_loop = None

# ========= FASTAPI =========
app = FastAPI(title="Jarvis Assistant WebSocket", version="4.0")
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
app.include_router(dashboard_router)

# ========= INICIALIZAR MÓDULOS =========
print("🤖 Inicializando módulos...")
wakeword = WakeWordDetector(keyword="alexa")
stt = SpeechToText()
tts = TextToSpeech(voice="es-AR-TomasNeural", use_rvc=False, sample_rate=16000, apply_filter=True, filter_strength=0.6)
nlp = IntentClassifier(model_path="core/bert_intent_model")
controller = WindowsController()

system_status = {
    "wakeword": "idle",
    "stt": "idle",
    "nlp": "idle",
    "tts": "idle",
    "esp32": "disconnected",
    "mic": "off"
}

# ========= FUNCIÓN PARA REPRODUCIR LOCALMENTE (FALLBACK) =========
def play_audio_local(audio_bytes):
    """
    Guarda el audio PCM en un archivo WAV temporal y lo reproduce con pygame.
    Usa un nombre único para evitar conflictos.
    """
    import tempfile
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_filename = tmp.name
            with wave.open(temp_filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(16000)  # Debe coincidir con el TTS
                wf.writeframes(audio_bytes)
        
        # Reproducir con pygame
        pygame.mixer.init(frequency=16000, size=-8, channels=1)
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        # Limpiar
        pygame.mixer.music.unload()
        try:
            os.remove(temp_filename)
        except:
            pass
        print("✅ Audio reproducido localmente")
    except Exception as e:
        print(f"❌ Error reproduciendo localmente: {e}")

# ========= ENDPOINTS DE PRUEBA =========
@app.post("/api/test_audio")
async def test_audio():
    """Genera un pitido y lo envía al ESP32 (o local)"""
    duration = 0.5
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave_data = 128 + 100 * np.sin(2 * np.pi * 440 * t)
    audio_bytes = wave_data.astype(np.uint8).tobytes()
    
    if ws_manager.connected:
        asyncio.create_task(ws_manager.send_audio(audio_bytes))
        return JSONResponse({"status": "ok", "message": "Pitido enviado al ESP32"})
    else:
        threading.Thread(target=play_audio_local, args=(audio_bytes,), daemon=True).start()
        return JSONResponse({"status": "ok", "message": "Pitido reproducido localmente"})

@app.post("/api/restart_esp32")
async def restart_esp32():
    await ws_manager.send_command({"action": "restart"})
    return JSONResponse({"status": "ok", "message": "Comando enviado"})

# ========= BUCLE PRINCIPAL =========
async def main_loop():
    global system_status
    print("🚀 Iniciando Jarvis Server (WebSocket)...")
    print(f"🎯 Conectando al ESP32 en {ESP32_IP}:{ESP32_PORT}")
    
    # Intentar conectar al ESP32
    await ws_manager.connect(ESP32_IP, ESP32_PORT)
    system_status["esp32"] = "connecting"
    
    def wakeword_thread():
        system_status["wakeword"] = "listening"
        wakeword.start_listening(callback=on_wakeword_detected)
    
    thread = threading.Thread(target=wakeword_thread, daemon=True)
    thread.start()
    
    # Bucle de mantenimiento: reconectar si se cae
    while True:
        await asyncio.sleep(2)
        if ws_manager.connected:
            system_status["esp32"] = "connected"
        else:
            system_status["esp32"] = "disconnected"
            print("🔄 Intentando reconectar al ESP32...")
            await ws_manager.connect(ESP32_IP, ESP32_PORT)

# ========= CALLBACK =========
def on_wakeword_detected():
    global main_event_loop
    print("🔊 Wakeword detectado! Activando STT...")
    system_status["wakeword"] = "triggered"
    system_status["mic"] = "on"
    
    text = stt.listen_and_transcribe()
    if not text:
        system_status["wakeword"] = "listening"
        system_status["mic"] = "off"
        return
    
    print(f"📝 Transcripción: {text}")
    system_status["stt"] = "processing"
    intent = nlp.classify(text)
    system_status["nlp"] = "processing"
    
    if intent["type"] == "action":
        response = execute_action(intent)
    else:
        action = intent.get("action", "")
        if action == "saludo":
            response = "¡Hola! ¿Cómo puedo ayudarte?"
        elif action == "despedida":
            response = "¡Hasta luego! Que tengas un buen día."
        elif action == "agradecimiento":
            response = "¡De nada! Para eso estoy."
        elif action == "interaccion":
            response = "Puedo abrir programas, reproducir música, buscar en internet y controlar el sistema."
        else:
            response = nlp.query_ollama(text)
    
    system_status["nlp"] = "idle"
    
    if response:
        print(f"🗣️ Respondiendo: {response}")
        system_status["tts"] = "generating"
        audio_bytes = tts.generate_pcm(response)
        system_status["tts"] = "sending"
        print(f"📤 Enviando {len(audio_bytes)} bytes de audio al ESP32...")
        
        # Enviar por WebSocket (si está conectado)
        if main_event_loop is not None and ws_manager.connected:
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_audio(audio_bytes),
                main_event_loop
                
            )
        else:
            print("⚠️ ESP32 no conectado. Reproduciendo en la PC.")
            threading.Thread(target=play_audio_local, args=(audio_bytes,), daemon=True).start()
    
    system_status["wakeword"] = "listening"
    system_status["stt"] = "idle"
    system_status["mic"] = "off"
    system_status["tts"] = "idle"

# ========= ACCIONES =========
def execute_action(intent):
    action = intent["action"]
    params = intent.get("params", {})
    
    if action == "open_app":
        app_name = params.get("app", "")
        if controller.open_app(app_name):
            return f"Abriendo {app_name}"
        else:
            return f"No pude encontrar {app_name}"
    elif action == "close_app":
        app_name = params.get("app", "")
        controller.close_app(app_name)
        return f"Cerrando {app_name}"
    elif action == "volume_up":
        controller.volume_up()
        return "Subiendo volumen"
    elif action == "volume_down":
        controller.volume_down()
        return "Bajando volumen"
    elif action == "set_volume":
        level = params.get("level", 50)
        return f"Volumen ajustado al {level}% (en desarrollo)"
    elif action == "search_web":
        consulta = params.get("consulta", "búsqueda")
        query = urllib.parse.quote(consulta)
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"Buscando '{consulta}' en Google"
    elif action == "shutdown":
        controller.shutdown()
        return "Apagando el equipo en 5 segundos"
    elif action == "restart":
        controller.restart()
        return "Reiniciando el equipo en 5 segundos"
    elif action == "music":
        query = params.get("query", "música")
        webbrowser.open(f"https://open.spotify.com/search/{query.replace(' ', '%20')}")
        return f"Buscando '{query}' en Spotify"
    else:
        return f"No sé cómo ejecutar {action}"

# ========= PUNTO DE ENTRADA =========
if __name__ == "__main__":
    # Crear event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_event_loop = loop
    loop.create_task(main_loop())
    
    # Ejecutar uvicorn en hilo separado
    def run_uvicorn():
        uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")
    
    thread = threading.Thread(target=run_uvicorn, daemon=True)
    thread.start()
    
    print("🌐 Servidor web en http://localhost:8000")
    print("⏳ Presiona Ctrl+C para salir")
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("🛑 Cerrando...")
    finally:
        loop.close()