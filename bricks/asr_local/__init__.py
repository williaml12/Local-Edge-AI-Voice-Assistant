import io
import os
import wave
import time
import requests
import numpy as np
import sounddevice as sd

# The service name from brick_compose.yaml is used as the hostname
ASR_SERVICE_URL = "http://whisper-asr:9000/asr"
MODEL_SIZE = os.getenv("ASR_MODEL", "base")


def transcribe_from_mic(duration_seconds=7.0, samplerate=16000):
    """
    Records audio from the default microphone, sends it to the
    containerized Whisper ASR service, and returns the transcription.
    """
    print(f"[ASR Brick] Recording for {duration_seconds} seconds...")

    # Record audio (Whisper expects 16kHz mono float32)
    recording = sd.rec(
        int(duration_seconds * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    print("[ASR Brick] Recording finished. Sending to ASR service...")

    # Convert numpy array to WAV bytes in memory
    audio_data = recording.flatten()
    audio_int16 = (audio_data * 32767).astype(np.int16)

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(samplerate)
        wav_file.writeframes(audio_int16.tobytes())
    wav_buffer.seek(0)

    # Send to ASR service
    try:
        response = requests.post(
            ASR_SERVICE_URL,
            params={"output": "json", "language": "en"},
            files={"audio_file": ("audio.wav", wav_buffer, "audio/wav")},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        transcription = result.get("text", "").strip()
        print(f"[ASR Brick] Transcription: '{transcription}'")
        return transcription
    except requests.exceptions.RequestException as e:
        print(f"[ASR Brick] Error communicating with ASR service: {e}")
        return ""