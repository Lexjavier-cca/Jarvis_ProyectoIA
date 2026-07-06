import asyncio
import websockets

async def test_ws():
    try:
        uri = "ws://192.168.100.18:8765"
        print(f"🔄 Conectando a {uri}...")
        async with websockets.connect(uri, timeout=5) as websocket:
            await websocket.send('{"action":"ping"}')
            response = await websocket.recv()
            print(f"✅ Respuesta del ESP32: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())