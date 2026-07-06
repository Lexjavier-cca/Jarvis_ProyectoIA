import pvporcupine
import pyaudio
import struct
import threading
import time

class WakeWordDetector:
    def __init__(self, keyword="alexa", sensitivity=0.5):
        """
        keywords disponibles: 'alexa', 'jarvis', 'computer', 'hey google', 'porcupine'
        (versión 1.9.5 no requiere access_key)
        """
        # Crear el detector con la palabra clave
        self.porcupine = pvporcupine.create(
            keywords=[keyword],
            sensitivities=[sensitivity]
        )
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.callback = None
        self.keyword = keyword

    def start_listening(self, callback):
        self.callback = callback
        self.running = True

        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.porcupine.sample_rate,
            input=True,
            frames_per_buffer=self.porcupine.frame_length,
            stream_callback=self._audio_callback
        )
        self.stream.start_stream()

        while self.running:
            time.sleep(0.1)

    def _audio_callback(self, in_data, frame_count, time_info, status):
        pcm = struct.unpack_from("h" * frame_count, in_data)
        keyword_index = self.porcupine.process(pcm)
        if keyword_index >= 0:
            print(f"🔊 Wakeword '{self.keyword}' detectado!")
            if self.callback:
                threading.Thread(target=self.callback, daemon=True).start()
        return (in_data, pyaudio.paContinue)

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.porcupine:
            self.porcupine.delete()
        self.audio.terminate()