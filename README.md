# Jarvis - Asistente Inteligente Local

Este proyecto es un asistente de voz que funciona completamente en tu hogar, sin necesidad de conexión a internet para procesar tus comandos. Puedes hablarle y el sistema:

- Te responde con voz.
- Controla tu computadora (abrir programas, ajustar volumen, apagar, reiniciar).
- Reproduce música desde una tarjeta microSD.
- Controla un ESP32 que puede encender luces u otros dispositivos.

---

## ¿Cómo funciona el sistema?

El sistema se divide en tres partes que trabajan juntas:

### 1. El servidor central (tu laptop)

Aquí corre un programa con inteligencia artificial. Escucha tu voz, la convierte en texto, entiende lo que quieres y decide qué acción tomar. También se encarga de comunicarse con el ESP32 y de generar respuestas de voz si es necesario.

### 2. El ESP32 con el reproductor de audio (DFPlayer Mini)

El ESP32 es un pequeño microcontrolador que se conecta a tu WiFi. Recibe órdenes del servidor y actúa en el mundo real: puede encender un LED o, más importante, controlar un reproductor de audio que tiene una tarjeta microSD con todos los sonidos y canciones.

### 3. La aplicación de control (Android o navegador)

Puedes usar tu celular para hablarle o darle comandos manuales. La comunicación es por WiFi, así que no necesitas cables.

---

## Arquitectura física del sistema

El sistema físico está compuesto por una batería externa, un ESP32, un módulo DFPlayer Mini, una tarjeta microSD y una bocina.

La alimentación del sistema es completamente portátil mediante un portapilas con 3 pilas AA de 1.5 V (4.5 V en total), por lo que no necesita permanecer conectado mediante un cable USB durante su funcionamiento.

El ESP32 se comunica con el DFPlayer Mini utilizando comunicación serial UART (TX/RX). El DFPlayer Mini es el encargado de leer los archivos MP3 almacenados en la tarjeta microSD y reproducirlos directamente en la bocina.

### Diagrama de conexión
                    Caja de pilas
               (3 pilas AA = 4.5 V)
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
   ESP32 (VIN)               DFPlayer (VCC)

        │                           │
        └────────── GND ─────────────┘
                    │
                    ▼

ESP32                         DFPlayer Mini

GPIO17 (TX) ---------------> RX

GPIO16 (RX) <--------------- TX

                    │
                    ▼

                Tarjeta microSD

             ├── 01
             ├── 02
             └── 03

                    │
                    ▼

SPK+ -----------------------> Bocina (+)

SPK- -----------------------> Bocina (-)


### Conexiones detalladas

| ESP32 | DFPlayer Mini |
|-------|---------------|
| GPIO17 (TX) | RX |
| GPIO16 (RX) | TX |
| VIN (5V) | VCC |
| GND | GND |

| DFPlayer Mini | Bocina |
|---------------|--------|
| SPK+ | + |
| SPK- | - |

---

## Componentes del sistema y su función

| Componente | Función |
|------------|---------|
| **BERT** | Modelo de inteligencia artificial que clasifica la intención de lo que dices. Por ejemplo, si dices "Abre Chrome", BERT reconoce que quieres abrir un programa. |
| **Whisper** | Modelo que convierte tu voz en texto. Escucha lo que dices y lo escribe. |
| **Edge TTS** | Sistema que genera la voz de respuesta cuando el asistente necesita hablar. |
| **FastAPI** | Servidor web que maneja todas las peticiones y la comunicación entre el celular y el ESP32. |
| **WebSocket** | Canal de comunicación en tiempo real que mantiene la conexión con el ESP32 para enviar comandos. |
| **SQLite** | Base de datos ligera que guarda el historial de comandos y la lista de canciones. |
| **DFPlayer Mini** | Reproductor de audio que lee los archivos MP3 desde la microSD y los reproduce por un altavoz. |

---

## ¿Qué puede hacer?

- **Conversar**: Saluda, despídete, agradece o pregunta qué puede hacer.
- **Abrir y cerrar programas**: Di "Abrir Chrome" o "Cerrar Word".
- **Controlar volumen**: "Sube el volumen", "Baja el volumen" o "Pon el volumen al 50".
- **Reproducir música**: "Pon Oasis", "Reproduce Wonderwall" o "Pon música aleatoria". Si no tiene la canción en la microSD, abrirá Spotify para que la busques.
- **Buscar en internet**: "Busca inteligencia artificial" abrirá Google con esa búsqueda.
- **Controlar la PC**: "Apaga la PC" (pedirá confirmación) o "Reinicia el equipo".

---

## ¿Qué necesitas?

- Una laptop con Windows (o Linux) y Python 3.10 instalado.
- Un ESP32 (cualquier placa con WiFi).
- Un módulo DFPlayer Mini y una tarjeta microSD con los audios.
- Un altavoz o parlante pequeño para escuchar la voz.
- (Opcional) Un celular Android para usar la app de control.

---

## Cómo empezar

### 1. Prepara el ESP32
- Conéctalo a tu PC y sube el firmware que está en la carpeta `esp32_firmware` usando el Arduino IDE.
- Cuando lo enciendas, se creará una red WiFi llamada `Jarvis-Config`. Conéctate desde tu celular o PC, ve a `http://192.168.4.1` y escribe los datos de tu WiFi para que el ESP32 se conecte a tu red.

### 2. Prepara la microSD
- Formatea la microSD en FAT32.
- Crea dos carpetas: `01` y `02`.
- En `01`, pon los audios de respuesta (saludo, gracias, etc.) con nombres `001.mp3`, `002.mp3`, ...
- En `02`, pon tus canciones con nombres `001.mp3`, `002.mp3`, ... (puedes tener hasta 105 canciones).
- Inserta la microSD en el DFPlayer Mini y conéctalo al ESP32 siguiendo el diagrama de conexiones.

### 3. Enciende el servidor en tu laptop
- Abre una terminal en la carpeta `server_python`.
- Crea un entorno virtual: `python -m venv venv` y actívalo.
- Instala las dependencias: `pip install -r requirements.txt`.
- Ejecuta: `python main.py`.
- Verás un mensaje indicando que el servidor está corriendo.

### 4. Usa la app de Android
- Abre el proyecto en Android Studio y ejecútalo en tu celular.
- Cuando abras la app, verás un campo para escribir la IP de tu laptop (la que aparece en la terminal al iniciar el servidor). Escríbela y pulsa "Conectar".
- Una vez conectado, ya puedes hablarle o usar los botones de control.

### 5. ¡Habla!
- Di **"Jarvis"** para activarlo, luego di tu comando. Por ejemplo: "Jarvis, abre Chrome" o "Jarvis, pon Oasis".
- Si solo dices "Jarvis" y te quedas callado, te saludará.

---

## Si no usas la app de Android

Puedes usar el micrófono de tu laptop directamente. El sistema está configurado para escuchar la palabra "Jarvis" desde el micrófono de la PC. También puedes probar el sistema por comandos de texto desde la página web que se abre en `http://localhost:8000` (aunque la interfaz web es básica, la app es más completa).

---

## Notas importantes

- La primera vez que hablas, el sistema tarda un poco en cargar los modelos de inteligencia artificial. Después va más rápido.
- Asegúrate de que tu laptop y el ESP32 estén en la misma red WiFi.
- Los audios de la microSD deben estar en formato MP3, mono o estéreo, 44.1 kHz, 128 kbps o similar.

---

## Créditos

Proyecto desarrollado como trabajo universitario. Tecnologías utilizadas:

- **Python** con FastAPI para el servidor.
- **Whisper** para reconocimiento de voz.
- **BERT** para clasificación de intenciones.
- **Edge TTS** para síntesis de voz.
- **ESP32** y **DFPlayer Mini** para el hardware.
- **Android Studio** para la aplicación móvil.

---

## ¿Preguntas?

Este proyecto está pensado para que puedas entenderlo y mejorarlo. Si quieres añadir más canciones, solo agrégalas a la carpeta `02` con el nombre correspondiente y actualiza la base de datos en `server_python/memory/db.py`. También puedes agregar más comandos o ampliarlo con sensores.

¡Disfruta y dale vida a tu propio Jarvis!