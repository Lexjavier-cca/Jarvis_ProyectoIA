/*
  ESP32 - REPRODUCTOR DE PCM POR WEBSOCKET (con normalización)
  - Recibe audio PCM (8-bit, mono, 16000 Hz) por WebSocket.
  - Normaliza el audio para usar todo el rango del DAC (0-255).
  - Reproduce por GPIO25 (DAC interno).
*/

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <driver/dac.h>

// ========= CONFIGURACIÓN =========
#define SAMPLE_RATE 16000           // Debe coincidir con el TTS de Python
#define MAX_AUDIO_BUFFER 65536        // 32 KB (suficiente para ~2 segundos a 16 kHz)

const char* AP_SSID = "Jarvis-Config";
const char* AP_PASS = "12345678";
const int WEBSOCKET_PORT = 8765;

// ========= OBJETOS GLOBALES =========
WebSocketsServer webSocket = WebSocketsServer(WEBSOCKET_PORT);
Preferences preferences;

// Buffer de audio recibido
uint8_t audioBuffer[MAX_AUDIO_BUFFER];
volatile uint32_t bufferLength = 0;
volatile bool playRequested = false;
volatile bool isPlaying = false;

// ========= FUNCIÓN PARA REPRODUCIR PCM CON NORMALIZACIÓN =========
void playRawPCM(uint8_t* data, uint32_t len) {
  if (len == 0) return;

  Serial.printf("🔊 Reproduciendo %d bytes de PCM...\n", len);

  // 1. Calcular mínimo y máximo (para normalizar)
  uint8_t minVal = 255;
  uint8_t maxVal = 0;
  for (uint32_t i = 0; i < len; i++) {
    if (data[i] < minVal) minVal = data[i];
    if (data[i] > maxVal) maxVal = data[i];
  }

  if (maxVal - minVal == 0) {
    Serial.println("⚠️ Audio sin variación (silencio)");
    return;
  }

  float scale = 255.0 / (maxVal - minVal);
  uint8_t offset = minVal;
  Serial.printf("📊 Normalizando: min=%d, max=%d, factor=%.2f\n", minVal, maxVal, scale);

  // 2. Habilitar DAC
  dac_output_enable(DAC_CHANNEL_1);

  // 3. Reproducir con normalización
  uint32_t us_per_sample = 1000000 / SAMPLE_RATE;
  uint32_t start = micros();

  for (uint32_t i = 0; i < len; i++) {
    uint8_t sample = (uint8_t)((data[i] - offset) * scale);
    dac_output_voltage(DAC_CHANNEL_1, sample);
    delayMicroseconds(us_per_sample);

    // Mantener el WebSocket vivo durante la reproducción (cada 100 muestras)
    if (i % 100 == 0) {
      webSocket.loop();
    }
  }

  // Silencio al finalizar
  dac_output_voltage(DAC_CHANNEL_1, 128);

  uint32_t elapsed = micros() - start;
  Serial.printf("✅ Reproducción completada en %.2f segundos\n", elapsed / 1000000.0);
}

// ========= EVENTOS WEBSOCKET =========
void onWebSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_TEXT: {
      // Recibir comandos JSON
      StaticJsonDocument<200> doc;
      DeserializationError error = deserializeJson(doc, payload, length);
      if (!error) {
        if (doc.containsKey("action")) {
          String action = doc["action"];

          if (action == "start") {
            // Reiniciar buffer antes de recibir nuevo audio
            bufferLength = 0;
            playRequested = false;
            Serial.println("📥 Iniciando recepción de audio...");
            webSocket.sendTXT(num, "{\"status\":\"ready\"}");
          }
          else if (action == "play") {
            // Recibida la orden de reproducir
            if (bufferLength > 0) {
              playRequested = true;
              Serial.printf("🎵 Orden de reproducción recibida (%d bytes)\n", bufferLength);
              webSocket.sendTXT(num, "{\"status\":\"playing\"}");
            } else {
              webSocket.sendTXT(num, "{\"status\":\"error\",\"msg\":\"No audio received\"}");
            }
          }
          else if (action == "ping") {
            webSocket.sendTXT(num, "{\"status\":\"pong\",\"rssi\":" + String(WiFi.RSSI()) + "}");
          }
          else if (action == "status") {
            webSocket.sendTXT(num, "{\"status\":\"ok\",\"free_heap\":" + String(ESP.getFreeHeap()) + "}");
          }
        }
      }
      break;
    }
    case WStype_BIN: {
      // Recibir audio PCM (8-bit, mono)
      if (bufferLength + length <= MAX_AUDIO_BUFFER) {
        memcpy(audioBuffer + bufferLength, payload, length);
        bufferLength += length;
        // Enviar confirmación de progreso (opcional)
        // webSocket.sendTXT(num, "{\"progress\":\"" + String(bufferLength) + "\"}");
      } else {
        Serial.println("⚠️ Buffer de audio lleno. Ignorando datos.");
      }
      break;
    }
    case WStype_CONNECTED:
      Serial.printf("✅ Cliente #%u conectado\n", num);
      bufferLength = 0;
      isPlaying = false;
      break;
    case WStype_DISCONNECTED:
      Serial.printf("❌ Cliente #%u desconectado\n", num);
      break;
  }
}

// ========= CONFIGURACIÓN WIFI =========
void connectToWiFi(const char* ssid, const char* pass) {
  WiFi.begin(ssid, pass);
  Serial.print("📶 Conectando a WiFi");
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500);
    Serial.print(".");
    tries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Conectado! IP: " + WiFi.localIP().toString());
    webSocket.begin();
    webSocket.onEvent(onWebSocketEvent);
    Serial.printf("🌐 WebSocket server en puerto %d\n", WEBSOCKET_PORT);
  } else {
    Serial.println("\n❌ Falló WiFi. Iniciando AP...");
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.println("📡 AP creado. IP: 192.168.4.1");
  }
}

// ========= SETUP =========
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== JARVIS ESP32 - PCM RECEIVER (con normalización) ===");

  // Leer credenciales WiFi guardadas
  preferences.begin("wifi", true);
  String ssid = preferences.getString("ssid", "");
  String pass = preferences.getString("pass", "");
  preferences.end();

  if (ssid.length() > 0 && pass.length() > 0) {
    connectToWiFi(ssid.c_str(), pass.c_str());
  } else {
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.println("📡 AP creado. IP: 192.168.4.1");
    Serial.println("📶 Conéctate a 'Jarvis-Config' y abre http://192.168.4.1");
    // Aquí podrías añadir un servidor web para configurar WiFi, pero ya lo tienes en el código anterior.
    // Para simplificar, usaremos el AP sin configuración web (puedes añadirla si quieres).
    // Por ahora, solo nos conectamos si hay credenciales guardadas.
  }
}

// ========= LOOP =========
void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    webSocket.loop();
  }

  // Si se solicitó reproducción y no se está reproduciendo
  if (playRequested && !isPlaying) {
    isPlaying = true;
    playRequested = false;
    playRawPCM(audioBuffer, bufferLength);
    bufferLength = 0;
    isPlaying = false;
  }

  delay(1);
}