import os
import sys
import asyncio
import edge_tts
import time
import io
import numpy as np
from pydub import AudioSegment
from scipy import signal  # Necesario para filtros

# ========= CONFIGURACIÓN DE APPLIO (OPCIONAL) =========
USE_RVC = False  # Cambia a True si tienes Applio

if USE_RVC:
    APPLIO_PATH = r'C:\Applio\Applio'
    if APPLIO_PATH not in sys.path:
        sys.path.insert(0, APPLIO_PATH)
    os.chdir(APPLIO_PATH)
    os.environ['APPLIO_DIR'] = APPLIO_PATH
    try:
        from rvc.infer.infer import VoiceConverter
        RVC_AVAILABLE = True
    except ImportError:
        print("⚠️ Applio/RVC no disponible. Usando solo EdgeTTS.")
        RVC_AVAILABLE = False
        VoiceConverter = None
else:
    RVC_AVAILABLE = False
    VoiceConverter = None

class TextToSpeech:
    def __init__(self,
                 voice="es-AR-TomasNeural",
                 model_path=None,
                 index_path=None,
                 use_rvc=False,
                 sample_rate=16000,      # Puedes cambiarlo a 22050
                 apply_filter=True,      # Activa filtro de suavizado
                 filter_strength=0.5):   # Fuerza del filtro (0-1)
        """
        TTS con clonación de voz usando EdgeTTS + RVC (opcional).
        - voice: voz base de EdgeTTS
        - sample_rate: frecuencia de muestreo (16000 o 22050)
        - apply_filter: True para suavizar el audio
        - filter_strength: intensidad del filtro
        """
        self.voice = voice
        self.model_path = model_path
        self.index_path = index_path
        self.use_rvc = use_rvc and RVC_AVAILABLE and model_path is not None
        self.sample_rate = sample_rate
        self.apply_filter = apply_filter
        self.filter_strength = filter_strength

        if self.use_rvc and not os.path.exists(model_path):
            print(f"⚠️ Modelo RVC no encontrado en {model_path}. Usando EdgeTTS sin clonación.")
            self.use_rvc = False

        if self.use_rvc:
            print(f"✅ TTS con RVC activado. Modelo: {model_path}")
        else:
            print("ℹ️ TTS usando solo EdgeTTS (sin clonación de voz).")

    def _apply_smoothing(self, audio_array):
        """Aplica un filtro de paso bajo simple (promedio móvil) para suavizar el audio."""
        if not self.apply_filter or len(audio_array) < 3:
            return audio_array
        
        # Tamaño de la ventana (mayor = más suavizado)
        window_size = max(3, int(5 * self.filter_strength) + 1)
        if window_size % 2 == 0:
            window_size += 1
        
        # Promedio móvil
        kernel = np.ones(window_size) / window_size
        smoothed = np.convolve(audio_array, kernel, mode='same')
        return smoothed.astype(np.uint8)

    def _dither(self, audio_array, bits=8):
        """Aplica dithering para reducir el ruido de cuantificación."""
        # Convertir a float
        audio_float = audio_array.astype(np.float32)
        # Añadir ruido aleatorio pequeño (dither)
        noise = np.random.normal(0, 0.5, audio_float.shape)
        audio_dithered = audio_float + noise
        # Volver a 8-bit
        return np.clip(audio_dithered, 0, 255).astype(np.uint8)

    def generate_pcm(self, text):
        """
        Genera audio PCM (8-bit mono) para enviar al ESP32.
        Aplica suavizado y dithering para mejorar la calidad.
        """
        # 1. Generar audio base con EdgeTTS
        mp3_data = asyncio.run(self._generate_edge_tts(text))

        # 2. Si no usamos RVC, convertimos directamente a PCM
        if not self.use_rvc:
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            audio = audio.set_frame_rate(self.sample_rate).set_channels(1).set_sample_width(1)
            pcm_data = np.array(audio.get_array_of_samples(), dtype=np.uint8)
            
            # Aplicar suavizado y dithering
            if self.apply_filter:
                pcm_data = self._apply_smoothing(pcm_data)
            pcm_data = self._dither(pcm_data)
            return pcm_data.tobytes()

        # 3. Con RVC: guardar temporalmente, convertir y luego PCM
        temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = int(time.time() * 1000)
        temp_input = os.path.join(temp_dir, f"edgetts_{timestamp}.wav")
        temp_output = os.path.join(temp_dir, f"rvc_{timestamp}.wav")

        audio_base = AudioSegment.from_mp3(io.BytesIO(mp3_data))
        audio_base.export(temp_input, format="wav")

        try:
            self._apply_rvc(temp_input, temp_output)
        except Exception as e:
            print(f"❌ Error en RVC: {e}. Usando audio base sin clonación.")
            audio_fallback = AudioSegment.from_wav(temp_input)
            audio_fallback = audio_fallback.set_frame_rate(self.sample_rate).set_channels(1).set_sample_width(1)
            pcm_data = np.array(audio_fallback.get_array_of_samples(), dtype=np.uint8)
            os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            # Aplicar mejoras
            if self.apply_filter:
                pcm_data = self._apply_smoothing(pcm_data)
            pcm_data = self._dither(pcm_data)
            return pcm_data.tobytes()

        audio_rvc = AudioSegment.from_wav(temp_output)
        audio_rvc = audio_rvc.set_frame_rate(self.sample_rate).set_channels(1).set_sample_width(1)
        pcm_data = np.array(audio_rvc.get_array_of_samples(), dtype=np.uint8)

        os.remove(temp_input)
        if os.path.exists(temp_output):
            os.remove(temp_output)

        # Aplicar mejoras
        if self.apply_filter:
            pcm_data = self._apply_smoothing(pcm_data)
        pcm_data = self._dither(pcm_data)
        return pcm_data.tobytes()

    async def _generate_edge_tts(self, text):
        """Genera audio MP3 con EdgeTTS y devuelve los bytes."""
        communicate = edge_tts.Communicate(text, self.voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    def _apply_rvc(self, input_path, output_path):
        """Aplica la conversión RVC usando VoiceConverter de Applio."""
        if not RVC_AVAILABLE or VoiceConverter is None:
            raise ImportError("VoiceConverter no disponible. Instala Applio correctamente.")

        vc = VoiceConverter()
        vc.convert_audio(
            audio_input_path=input_path,
            audio_output_path=output_path,
            model_path=self.model_path,
            index_path=self.index_path if (self.index_path and os.path.exists(self.index_path)) else "",
            pitch=0,
            f0_method="rmvpe",
            index_rate=0.75,
            protect=0.33,
            hop_length=128,
            clean_audio=False,
            export_format="WAV",
            resample_sr=0,
            split_audio=False,
            f0_autotune=False,
            post_process=False,
            embedder_model="contentvec",
            clean_strength=0.5,
            volume_envelope=1.0,
        )