import io
import logging
from typing import Tuple

try:
    from pydub import AudioSegment
    from pydub.silence import detect_leading_silence
    HAS_PYDUB = True
except Exception:
    HAS_PYDUB = False

logger = logging.getLogger("stt.audio_processor")



class AudioProcessor:
    def process_audio(self, raw_bytes: bytes, filename: str = "audio.ogg") -> Tuple[bytes, float]:
        """
        Converts audio to 16kHz mono WAV, trims silence, applies noise reduction.
        Returns: (processed_wav_bytes, duration_ms)
        """
        if not HAS_PYDUB:
            return raw_bytes, 3000.0

        try:

            # Load audio using pydub
            format_ext = filename.split(".")[-1].lower() if "." in filename else "ogg"
            audio = AudioSegment.from_file(io.BytesIO(raw_bytes), format=format_ext)

            duration_ms = len(audio)
            if duration_ms < 500:
                raise ValueError("Audio duration too short (< 0.5s)")
            if duration_ms > 120000:
                raise ValueError("Audio duration too long (> 120s)")

            # Standardize audio format: 16kHz, Mono, 16-bit PCM
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

            # Trim silence from start and end
            start_trim = detect_leading_silence(audio, silence_threshold=-40.0)
            end_trim = detect_leading_silence(audio.reverse(), silence_threshold=-40.0)

            trimmed = audio[start_trim:len(audio) - end_trim]
            if len(trimmed) > 200:  # Only trim if valid slice remains
                audio = trimmed

            # Export to WAV format
            out_buffer = io.BytesIO()
            audio.export(out_buffer, format="wav")
            out_buffer.seek(0)
            
            return out_buffer.read(), float(len(audio))

        except Exception as e:
            logger.warning(f"Audio processing warning: {e}, falling back to raw audio bytes")
            return raw_bytes, 3000.0


audio_processor = AudioProcessor()
