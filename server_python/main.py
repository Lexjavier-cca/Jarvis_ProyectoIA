"""
Asistente Inteligente Distribuido - Servidor Central (con interfaz web móvil)
Ejecuta: python main.py
"""

# ============================================================================
# IMPORTS
# ============================================================================
import asyncio
import threading
import uvicorn
import webbrowser
import urllib.parse
import os
import time
import json
import tempfile
import wave
import pygame
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from core.wakeword import WakeWordDetector
from core.stt import SpeechToText, transcribe_audio_bytes
from core.tts import TextToSpeech
from core.nlp import IntentClassifier
from windows.controller import WindowsController
from memory.db import DBManager
from websocket.manager import ws_manager

# ============================================================================
# CONFIGURACION
# ============================================================================
ESP32_IP = "192.168.137.138"          # CAMBIA POR LA IP DE TU ESP32
ESP32_PORT = 8765
main_event_loop = None
pending_confirmation = None  # {"action": "shutdown"} o None

app = FastAPI(title="Jarvis Server", version="5.0")

# ============================================================================
# MAPEO DE INTENCIONES A ARCHIVOS DE AUDIO (MICROSD)
# ============================================================================
INTENT_TO_AUDIO = {
    "saludo": "001.mp3",
    "agradecimiento": "002.mp3",
    "apagar_pc": "003.mp3",
    "fallback": "004.mp3",
    "bajar_volumen": "005.mp3",
    "subir_volumen": "006.mp3",
    "buscar_web": "007.mp3",
    "cambiar_volumen": "008.mp3",
    "despedida": "009.mp3",
    "interaccion": "010.mp3",
    "reiniciar_pc": "011.mp3",
    "reproducir_audio": "012.mp3",
    "abrir_programa": "013.mp3",
    "default": "004.mp3"
}

MUSIC_FOLDER = "MUSIC"

# ============================================================================
# INICIALIZACION DE MODULOS
# ============================================================================
print("Inicializando modulos...")
wakeword = WakeWordDetector(keyword="jarvis")
stt = SpeechToText()
tts = TextToSpeech(voice="es-AR-TomasNeural", use_rvc=False)
nlp = IntentClassifier(model_path="core/bert_intent_model")
controller = WindowsController()
db = DBManager()

system_status = {
    "wakeword": "idle",
    "stt": "idle",
    "nlp": "idle",
    "tts": "idle",
    "esp32": "disconnected",
    "mic": "off",
    "player": {"playing": False, "current": None, "volume": 50, "mode": "idle"},
    "cpu_usage": 0,
    "memory_usage": 0,
    "clients": 0
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def send_esp32_command_safe(command):
    """Envía un comando al ESP32 desde cualquier hilo usando el event loop."""
    global main_event_loop
    if main_event_loop is not None and ws_manager.connected:
        asyncio.run_coroutine_threadsafe(
            ws_manager.send_command(command),
            main_event_loop
        )
        return True
    return False

def play_audio_local(audio_bytes):
    """Reproduce localmente (fallback si el ESP32 no está conectado)."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_filename = tmp.name
            with wave.open(temp_filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(1)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
        pygame.mixer.init(frequency=16000, size=-8, channels=1)
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
        try:
            os.remove(temp_filename)
        except:
            pass
    except Exception as e:
        print(f"Error reproduciendo localmente: {e}")

# ============================================================================
# RUTAS DE LA API
# ============================================================================
@app.get("/")
async def root():
    return {"message": "Jarvis Server running. Use the Android app to connect."}

@app.get("/api/status")
async def get_status():
    system_status["cpu_usage"] = psutil.cpu_percent()
    system_status["memory_usage"] = psutil.virtual_memory().percent
    return system_status

@app.post("/api/command")
async def send_command(command: dict):
    if ws_manager.connected:
        asyncio.create_task(ws_manager.send_command(command))
        return JSONResponse({"status": "ok", "message": "Comando enviado"})
    else:
        return JSONResponse({"status": "error", "message": "ESP32 no conectado"}, status_code=503)

@app.post("/api/play_audio")
async def play_audio(data: dict):
    folder = data.get("folder", "AUDIO")
    file = data.get("file")
    if not file:
        return JSONResponse({"status": "error", "message": "Falta el nombre del archivo"}, status_code=400)
    if ws_manager.connected:
        command = {"action": "PLAY_AUDIO", "folder": folder, "file": file}
        asyncio.create_task(ws_manager.send_command(command))
        return JSONResponse({"status": "ok", "message": f"Reproduciendo {file}"})
    else:
        return JSONResponse({"status": "error", "message": "ESP32 no conectado"}, status_code=503)

@app.post("/api/music")
async def music_control(data: dict):
    if not ws_manager.connected:
        return JSONResponse({"status": "error", "message": "ESP32 no conectado"}, status_code=503)
    action = data.get("action")
    if action == "play":
        file = data.get("file", "001.mp3")
        command = {"action": "PLAY_AUDIO", "folder": MUSIC_FOLDER, "file": file}
    elif action == "pause":
        command = {"action": "MUSIC_PAUSE"}
    elif action == "stop":
        command = {"action": "MUSIC_STOP"}
    elif action == "next":
        command = {"action": "MUSIC_NEXT"}
    elif action == "volume":
        vol = data.get("volume", 50)
        command = {"action": "MUSIC_VOLUME", "volume": vol}
    else:
        return JSONResponse({"status": "error", "message": "Acción desconocida"}, status_code=400)
    asyncio.create_task(ws_manager.send_command(command))
    return JSONResponse({"status": "ok", "message": f"Comando {action} enviado"})

# ============================================================================
# WEBSOCKET PARA EL ESP32
# ============================================================================
@app.websocket("/ws/esp32")
async def websocket_esp32(websocket: WebSocket):
    await websocket.accept()
    print("ESP32 conectado por WebSocket")
    ws_manager.websocket = websocket
    ws_manager.connected = True
    system_status["esp32"] = "connected"
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "player_status":
                    system_status["player"]["playing"] = msg.get("playing", False)
                    system_status["player"]["current"] = msg.get("current", None)
                    system_status["player"]["mode"] = msg.get("mode", "idle")
                elif msg.get("type") == "volume_changed":
                    system_status["player"]["volume"] = msg.get("volume", 50)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        print("ESP32 desconectado")
        ws_manager.connected = False
        system_status["esp32"] = "disconnected"
        ws_manager.websocket = None

# ============================================================================
# WEBSOCKET PARA CLIENTES (CELULAR)
# ============================================================================
@app.websocket("/ws/client")
async def websocket_client(websocket: WebSocket):
    await websocket.accept()
    system_status["clients"] += 1
    print(f"Cliente web conectado (total: {system_status['clients']})")

    await websocket.send_text(json.dumps({"type": "connected", "message": "Conectado al servidor Jarvis"}))

    audio_buffer = bytearray()
    sample_rate = 16000
    bytes_per_sample = 2
    is_recording = False
    is_processing = False

    async def send_ping():
        while True:
            await asyncio.sleep(10)
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
            except:
                break

    ping_task = asyncio.create_task(send_ping())

    try:
        while True:
            try:
                raw = await websocket.receive()
            except Exception as e:
                print(f"Error al recibir: {e}")
                break

            if raw["type"] == "websocket.disconnect":
                print("Cliente desconectado (mensaje de desconexión)")
                break

            if raw["type"] != "websocket.receive":
                continue

            text_data = raw.get("text")
            if text_data:
                try:
                    msg = json.loads(text_data)
                    print(f"Mensaje JSON: {msg}")

                    if msg.get("type") == "command":
                        command = msg.get("data", {})
                        if ws_manager.connected:
                            await ws_manager.send_command(command)
                        await websocket.send_text(json.dumps({
                            "type": "command_response",
                            "status": "sent" if ws_manager.connected else "esp32_disconnected"
                        }))

                    elif msg.get("type") == "start_recording":
                        audio_buffer.clear()
                        is_recording = True
                        is_processing = False
                        await websocket.send_text(json.dumps({"type": "recording_started"}))
                        print("Inicio de grabación desde cliente")

                    elif msg.get("type") == "stop_recording":
                        is_recording = False
                        if len(audio_buffer) > 0:
                            is_processing = True
                            audio_bytes = bytes(audio_buffer)
                            audio_buffer.clear()
                            asyncio.create_task(process_audio_command(websocket, audio_bytes, sample_rate))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "No se recibió audio"
                            }))
                        print("Fin de grabación desde cliente")

                    elif msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))

                    else:
                        print(f"Tipo de mensaje desconocido: {msg.get('type')}")

                    continue
                except json.JSONDecodeError as e:
                    print(f"Error decodificando JSON: {e}")
                    continue

            bytes_data = raw.get("bytes")
            if bytes_data:
                if is_recording and not is_processing:
                    audio_buffer.extend(bytes_data)
                    max_buffer = sample_rate * bytes_per_sample * 10
                    if len(audio_buffer) > max_buffer:
                        audio_buffer = audio_buffer[-max_buffer:]
                else:
                    pass

    except WebSocketDisconnect:
        print("Cliente web desconectado (WebSocketDisconnect)")
    except Exception as e:
        print(f"Error en WebSocket cliente: {e}")
    finally:
        ping_task.cancel()
        system_status["clients"] -= 1
        print(f"Cliente web desconectado (total restante: {system_status['clients']})")
        audio_buffer.clear()

# ============================================================================
# PROCESAMIENTO DE AUDIO (con confirmación de apagado)
# ============================================================================
async def process_audio_command(websocket, audio_bytes, sample_rate):
    global pending_confirmation
    try:
        text = transcribe_audio_bytes(audio_bytes, sample_rate)
        if not text:
            await websocket.send_text(json.dumps({
                "type": "transcription",
                "text": "",
                "error": "No se pudo transcribir el audio"
            }))
            return

        print(f"Transcripción desde web: {text}")
        await websocket.send_text(json.dumps({
            "type": "transcription",
            "text": text
        }))
        frases_habilidad = [
            'que sabes hacer', 'qué sabes hacer', 
            'que puedes hacer', 'qué puedes hacer',
            'tus habilidades', 'que haces', 'qué haces',
            'para que sirves', 'para qué sirves'
        ]
        if any(frase in text.lower() for frase in frases_habilidad):
            print("🎯 Detectado 'qué sabes hacer' → forzando acción listar_habilidades")
            # Creamos un intent falso
            intent_falso = {
                "type": "action",
                "action": "listar_habilidades",
                "params": {},
                "intent_name": "listar_habilidades"
            }
            response_text = execute_action(intent_falso)
            await websocket.send_text(json.dumps({
                "type": "response",
                "text": response_text,
                "intent": "listar_habilidades"
            }))
            return  # Salimos, no procesamos más

        # === VERIFICAR CONFIRMACIÓN PENDIENTE ===
        if pending_confirmation:
            if pending_confirmation.get("action") == "shutdown":
                # Comprobar si el usuario confirma
                if any(word in text.lower() for word in ["sí", "si", "apaga", "confirmo", "acepto", "ok"]):
                    controller.shutdown()
                    response_text = "Apagando el equipo en 5 segundos."
                    pending_confirmation = None
                    # Reproducir audio de confirmación
                    audio_file = INTENT_TO_AUDIO.get("fallback")
                    if audio_file and ws_manager.connected:
                        send_esp32_command_safe({
                            "action": "PLAY_AUDIO",
                            "folder": "AUDIO",
                            "file": audio_file
                        })
                elif any(word in text.lower() for word in ["no", "cancelar", "detener"]):
                    response_text = "Apagado cancelado."
                    pending_confirmation = None
                else:
                    response_text = "No entendí tu respuesta. ¿Apago el equipo? Di 'Sí' o 'No'."
                    # No limpiar pending_confirmation para seguir esperando
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "text": response_text,
                    "intent": "confirmacion"
                }))
                return  # Salimos sin procesar más

        # === CONTINUAR CON EL FLUJO NORMAL ===
        intent = nlp.classify(text)
        intent_name = intent.get("intent_name", "fallback")

        if intent["type"] == "action":
            response_text = execute_action(intent)
        else:
            response_text = nlp.get_response(intent_name)
            audio_file = INTENT_TO_AUDIO.get(intent_name)
            if audio_file and ws_manager.connected:
                send_esp32_command_safe({
                    "action": "PLAY_AUDIO",
                    "folder": "AUDIO",
                    "file": audio_file
                })

        await websocket.send_text(json.dumps({
            "type": "response",
            "text": response_text,
            "intent": intent_name
        }))

        try:
            db.add_history(text, response_text, intent_name)
        except:
            pass

    except Exception as e:
        print(f"Error procesando audio: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))

# ============================================================================
# BUCLE PRINCIPAL
# ============================================================================
async def main_loop():
    global system_status, main_event_loop
    main_event_loop = asyncio.get_running_loop()
    print("Iniciando servidor Jarvis...")
    print("Servidor Jarvis corriendo. Conéctate con la app de Android.")
    await ws_manager.connect(ESP32_IP, ESP32_PORT)

    def wakeword_thread():
        system_status["wakeword"] = "listening"
        wakeword.start_listening(callback=on_wakeword_detected)

    thread = threading.Thread(target=wakeword_thread, daemon=True)
    thread.start()

    while True:
        await asyncio.sleep(2)
        if not ws_manager.connected:
            system_status["esp32"] = "disconnected"
            await ws_manager.connect(ESP32_IP, ESP32_PORT)
        else:
            system_status["esp32"] = "connected"

# ============================================================================
# CALLBACK DEL WAKEWORD (con confirmación de apagado)
# ============================================================================
def on_wakeword_detected():
    global main_event_loop, pending_confirmation
    print("Wakeword detectado. Activando STT...")
    system_status["wakeword"] = "triggered"
    system_status["mic"] = "on"

    text = stt.listen_and_transcribe()
    if not text:
        system_status["wakeword"] = "listening"
        system_status["mic"] = "off"
        return

    print(f"Transcripcion: {text}")
    frases_habilidad = [
        'que sabes hacer', 'qué sabes hacer', 
        'que puedes hacer', 'qué puedes hacer',
        'tus habilidades', 'que haces', 'qué haces',
        'para que sirves', 'para qué sirves'
    ]
    if any(frase in text.lower() for frase in frases_habilidad):
        print("🎯 Detectado 'qué sabes hacer' → forzando acción listar_habilidades")
        intent_falso = {
            "type": "action",
            "action": "listar_habilidades",
            "params": {},
            "intent_name": "listar_habilidades"
        }
        response_text = execute_action(intent_falso)
        print(f"Respondiendo: {response_text}")
        # No reproducimos audio aquí porque ya lo hará execute_action
        system_status["wakeword"] = "listening"
        system_status["stt"] = "idle"
        system_status["mic"] = "off"
        return  # Salimos
    system_status["stt"] = "processing"

    # === VERIFICAR CONFIRMACIÓN PENDIENTE ===
    if pending_confirmation:
        if pending_confirmation.get("action") == "shutdown":
            if any(word in text.lower() for word in ["sí", "si", "apaga", "confirmo", "acepto", "ok"]):
                controller.shutdown()
                response_text = "Apagando el equipo en 5 segundos."
                pending_confirmation = None
                audio_file = INTENT_TO_AUDIO.get("fallback")
                if audio_file and ws_manager.connected:
                    send_esp32_command_safe({
                        "action": "PLAY_AUDIO",
                        "folder": "AUDIO",
                        "file": audio_file
                    })
            elif any(word in text.lower() for word in ["no", "cancelar", "detener"]):
                response_text = "Apagado cancelado."
                pending_confirmation = None
            else:
                response_text = "No entendí tu respuesta. ¿Apago el equipo? Di 'Sí' o 'No'."
            print(f"Respondiendo: {response_text}")
            system_status["wakeword"] = "listening"
            system_status["stt"] = "idle"
            system_status["mic"] = "off"
            return

    # === CONTINUAR CON EL FLUJO NORMAL ===
    intent = nlp.classify(text)
    intent_name = intent.get("intent_name", "fallback")
    system_status["nlp"] = "processing"

    if intent["type"] == "action":
        response_text = execute_action(intent)
    else:
        response_text = nlp.get_response(intent_name)
        audio_file = INTENT_TO_AUDIO.get(intent_name)
        if audio_file and ws_manager.connected:
            send_esp32_command_safe({
                "action": "PLAY_AUDIO",
                "folder": "AUDIO",
                "file": audio_file
            })

    system_status["nlp"] = "idle"

    if response_text:
        print(f"Respondiendo: {response_text}")

    system_status["wakeword"] = "listening"
    system_status["stt"] = "idle"
    system_status["mic"] = "off"
    system_status["tts"] = "idle"

# ============================================================================
# EJECUCION DE ACCIONES (con close_app y confirmación de apagado)
# ============================================================================
def execute_action(intent):
    global main_event_loop, pending_confirmation
    action = intent["action"]
    params = intent.get("params", {})
    print(f"⚡ Ejecutando acción: {action} con parámetros {params}")
    # ========== NUEVA ACCIÓN: LISTAR HABILIDADES ==========
    if action == "listar_habilidades":
        # Audio que quieres reproducir (debe estar en la carpeta AUDIO del ESP32)
        audio_file = "010.mp3"   # Cambia por el nombre de tu archivo
        # También puedes enviar un texto de respuesta
        mensaje = "Reproduciendo mis habilidades..."
        # Reproducir el audio en el ESP32
        if ws_manager.connected:
            send_esp32_command_safe({
                "action": "PLAY_AUDIO",
                "folder": "AUDIO",   # Asegúrate de que la carpeta existe en la SD
                "file": audio_file
            })
        else:
            # Fallback: si no hay ESP32, podrías reproducir localmente o con TTS
            print("ESP32 no conectado, no se pudo reproducir el audio.")
        return mensaje
    # =====================================================
 
    # ========== FUNCIÓN AUXILIAR PARA REPRODUCIR AUDIO DE CONFIRMACIÓN ==========
    def reproducir_audio_confirmacion(file):
        if ws_manager.connected and file:
            send_esp32_command_safe({
                "action": "PLAY_AUDIO",
                "folder": "AUDIO",
                "file": file
            })
 
    # ========== ACCIONES ==========
    if action == "open_app":
        app_name = params.get("app", "")
        app_action = params.get("app_action", "open")
        print(f"📂 Acción sobre aplicación: {app_action} {app_name}")
        if app_action == "close":
            if controller.close_app(app_name):
                return f"Cerrando {app_name}"
            else:
                return f"No pude cerrar {app_name}"
        else:
            if controller.open_app(app_name):
                reproducir_audio_confirmacion("013.mp3")  # Abrir programa
                return f"Abriendo {app_name}"
            else:
                return f"No pude encontrar {app_name}"
 
    elif action == "close_app":
        app_name = params.get("app", "")
        controller.close_app(app_name)
        return f"Cerrando {app_name}"
 
    elif action == "volume_up":
        controller.volume_up()
        if ws_manager.connected:
            send_esp32_command_safe({"action": "MUSIC_VOLUME", "volume": 25})
        reproducir_audio_confirmacion("006.mp3")  # Subir volumen
        return "Subiendo volumen"
 
    elif action == "volume_down":
        controller.volume_down()
        if ws_manager.connected:
            send_esp32_command_safe({"action": "MUSIC_VOLUME", "volume": 15})
        reproducir_audio_confirmacion("005.mp3")  # Bajar volumen
        return "Bajando volumen"
 
    elif action == "set_volume":
        level = params.get("level", 50)
        if ws_manager.connected:
            send_esp32_command_safe({"action": "MUSIC_VOLUME", "volume": level})
        reproducir_audio_confirmacion("008.mp3")  # Cambiar volumen
        return f"Volumen ajustado al {level}%"
 
    elif action == "search_web":
        consulta = params.get("consulta", "busqueda")
        query = urllib.parse.quote(consulta)
        webbrowser.open(f"https://www.google.com/search?q={query}")
        reproducir_audio_confirmacion("007.mp3")  # Buscar web
        return f"Buscando '{consulta}' en Google"
 
    elif action == "shutdown":
        print("⚠️ Comando de apagado recibido. Pidiendo confirmación...")
        pending_confirmation = {"action": "shutdown"}
        # No reproducir audio aún, esperar confirmación
        return "¿Seguro que quieres apagar el equipo? Di 'Sí, apaga' para confirmar."
 
    elif action == "restart":
        controller.restart()
        reproducir_audio_confirmacion("011.mp3")  # Reiniciar PC
        return "Reiniciando el equipo en 5 segundos"
 
    elif action == "music":
        query = params.get("query", "").strip()
        print(f"🎵 Búsqueda musical: '{query}'")
        # Si contiene "spotify", abrir Spotify directamente
        if "spotify" in query.lower():
            webbrowser.open("https://open.spotify.com")
            return "Abriendo Spotify"
        if not query:
            song = db.get_random_song()
            if song:
                print(f"🎵 Canción aleatoria: {song['filename']} - {song['title']}")
                if ws_manager.connected:
                    send_esp32_command_safe({
                        "action": "PLAY_AUDIO",
                        "folder": MUSIC_FOLDER,
                        "file": song['filename']
                    })
                return f"Reproduciendo '{song['title']}' de {song['artist']}"
            else:
                return "No tengo canciones en la biblioteca."
        results = db.search_songs(query)
        print(f"🔍 Resultados: {len(results)} canciones encontradas")
        if results:
            song = results[0]
            print(f"🎵 Reproduciendo: {song['filename']} - {song['title']}")
            if ws_manager.connected:
                send_esp32_command_safe({
                    "action": "PLAY_AUDIO",
                    "folder": MUSIC_FOLDER,
                    "file": song['filename']
                })
            return f"Reproduciendo '{song['title']}' de {song['artist']}"
        else:
            webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(query)}")
            return f"No encontré '{query}' en mi biblioteca. Abriendo Spotify para buscarlo."
 
    else:
        return f"No se como ejecutar {action}"

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main_loop())

    def run_uvicorn():
        uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")

    thread = threading.Thread(target=run_uvicorn, daemon=True)
    thread.start()

    print("Presiona Ctrl+C para salir")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Cerrando...")
    finally:
        loop.close()