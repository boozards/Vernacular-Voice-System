import wave
import struct
import math
import os


def generate_sample_wav(filename: str = "sample_hi_voice.wav", duration_sec: float = 2.0):
    """Generates a simple 16kHz mono synthetic tone WAV audio file for testing."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Generate 440 Hz sine wave tone
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            wav_file.writeframes(struct.pack("<h", val))
            
    print(f"Generated sample audio WAV file: {filename}")


if __name__ == "__main__":
    generate_sample_wav("tests/sample_audio.wav")
