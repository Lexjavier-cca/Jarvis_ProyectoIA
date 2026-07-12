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
            print(f"Conectado al ESP32 en {uri}")
            return True
        except Exception as e:
            print(f"Error conectando al ESP32: {e}")
            self.connected = False
            return False

    async def send_command(self, command):
        if not self.connected or not self.websocket:
            print("ESP32 no conectado")
            return False
        try:
            await self.websocket.send(json.dumps(command))
            print(f"Comando enviado: {command}")
            return True
        except Exception as e:
            print(f"Error enviando comando: {e}")
            self.connected = False
            return False

ws_manager = WebSocketManager()