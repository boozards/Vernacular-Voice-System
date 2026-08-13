import io
import logging
from gtts import gTTS

logger = logging.getLogger("tts.fallback")

# Language code mapping for gTTS
GTTS_LANG_MAP = {
    "hi-IN": "hi",
    "ta-IN": "ta",
    "te-IN": "te",
    "bn-IN": "bn",
    "mr-IN": "mr",
    "kn-IN": "kn",
    "ml-IN": "ml",
    "gu-IN": "gu",
    "en-IN": "en"
}


class FallbackTTSEngine:
    async def synthesize_fallback(self, text: str, language: str = "hi-IN") -> bytes:
        """Synthesizes text using gTTS fallback engine into MP3/OGG bytes."""
        lang_code = GTTS_LANG_MAP.get(language, "hi")
        logger.info(f"Using Fallback gTTS Engine for lang {language} (code: {lang_code})")
        
        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.read()
        except Exception as e:
            logger.error(f"gTTS fallback failed: {e}, returning dummy audio frame")
            # Return minimal silent MP3 audio header as emergency buffer
            return b'\xFF\xFB\x90\xC4\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


fallback_tts = FallbackTTSEngine()
