import asyncio
import websockets
import json

class WebSocketManager:
    def __init__(self):
        self.websocket = None
        self.connected = False

    async def connect(self, esp_ip, port=8765):
        try:
            uri = f"ws://{esp_ip}:{port}"
            self.websocket = await websockets.connect(uri)
            self.connected = True
            print(f"✅ Conectado al ESP32 en {uri}")
            return True
        except Exception as e:
            print(f"❌ Error conectando al ESP32: {e}")
            self.connected = False
            return False

    async def send_audio(self, audio_bytes):
        if not self.connected or not self.websocket:
         return False

        try:
            # 1. Enviar comando "start"
            await self.websocket.send(json.dumps({"action": "start"}))
            await asyncio.sleep(0.05)  # Esperar un poco

            # 2. Enviar fragmentos de 128 bytes con pausa de 20 ms
            chunk_size = 128
            total = len(audio_bytes)
            print(f"📤 Enviando {total} bytes de audio en fragmentos de {chunk_size}...")
            for i in range(0, total, chunk_size):
                chunk = audio_bytes[i:i+chunk_size]
                await self.websocket.send(chunk)
                await asyncio.sleep(0.02)  # 20 ms

            # 3. Enviar comando "play"
            await self.websocket.send(json.dumps({"action": "play"}))
            print("✅ Audio enviado y orden de reproducción enviada")
            return True

        except Exception as e:
            print(f"❌ Error enviando audio: {e}")
            self.connected = False
            return False

    async def send_command(self, command):
        if not self.connected or not self.websocket:
            return False
        try:
            await self.websocket.send(json.dumps(command))
            return True
        except:
            return False

ws_manager = WebSocketManager()