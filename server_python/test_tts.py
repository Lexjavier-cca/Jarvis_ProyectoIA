from core.tts import TextToSpeech
import time

# Si NO quieres RVC (más rápido y sin dependencias):
tts = TextToSpeech(voice="es-AR-TomasNeural", use_rvc=False)

# Si QUIERES RVC (necesitas tener Applio y los modelos):
# tts = TextToSpeech(
#     voice="es-AR-TomasNeural",
#     model_path="rvc_models/modelo_ia_120e_7560s.pth",
#     index_path="rvc_models/modelo_ia.index",
#     use_rvc=True
# )

print("Generando audio...")
audio = tts.generate_pcm("Hola mundo, esta es una prueba de voz.")
print(f"✅ Audio generado: {len(audio)} bytes")