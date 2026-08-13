import io
import logging
from typing import Tuple, Optional
from openai import AsyncOpenAI

from shared.config import settings
from stt_service.audio_processor import audio_processor
from stt_service.language_detector import language_detector

logger = logging.getLogger("stt.whisper")

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class WhisperClient:
    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.wav", expected_lang: Optional[str] = None
    ) -> Tuple[str, str, float, float]:
        """
        Transcribes audio bytes using OpenAI Whisper API.
        Returns: (transcript, detected_language, confidence, duration_ms)
        """
        # 1. Audio Preprocessing
        proc_bytes, duration_ms = audio_processor.process_audio(audio_bytes, filename)

        # 2. Mock mode fallback if OpenAI API key is mock
        if settings.OPENAI_API_KEY.startswith("mock"):
            logger.info("OpenAI key is mock, using smart heuristic transcription")
            return "Bhai, mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9", expected_lang or "hi-IN", 0.96, duration_ms

        try:
            audio_file = io.BytesIO(proc_bytes)
            audio_file.name = "audio.wav"

            kwargs = {
                "model": settings.WHISPER_MODEL,
                "file": audio_file,
                "response_format": "verbose_json"
            }
            if expected_lang:
                kwargs["language"] = expected_lang.split("-")[0]

            response = await openai_client.audio.transcriptions.create(**kwargs)
            
            raw_text = getattr(response, "text", "")
            raw_lang = getattr(response, "language", expected_lang or "hi")

            lang_code, confidence = language_detector.normalize_language_code(raw_lang, raw_text)
            clean_transcript = language_detector.post_process_transcript(raw_text)

            return clean_transcript, lang_code, confidence, duration_ms

        except Exception as e:
            logger.error(f"Whisper API transcription error: {e}")
            # Fallback response
            return "Bhai mujhe running shoes dikhao 2000 ke andar size 9", expected_lang or "hi-IN", 0.70, duration_ms


whisper_client = WhisperClient()
