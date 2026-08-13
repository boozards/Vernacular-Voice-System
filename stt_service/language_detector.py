import re
import logging
from typing import Tuple

logger = logging.getLogger("stt.language_detector")

INDIAN_LANG_MAP = {
    "hi": "hi-IN",
    "hindi": "hi-IN",
    "ta": "ta-IN",
    "tamil": "ta-IN",
    "te": "te-IN",
    "telugu": "te-IN",
    "bn": "bn-IN",
    "bengali": "bn-IN",
    "mr": "mr-IN",
    "marathi": "mr-IN",
    "kn": "kn-IN",
    "kannada": "kn-IN",
    "ml": "ml-IN",
    "malayalam": "ml-IN",
    "gu": "gu-IN",
    "gujarati": "gu-IN",
    "en": "en-IN",
    "english": "en-IN"
}

# Transliteration normalizations for common Hinglish / Tanglish phrases
NORMALIZATION_PATTERNS = [
    (r'\bchahiye\b', 'chahiye'),
    (r'\bdikhao\b', 'dikhao'),
    (r'\bkaattunga\b', 'kaattunga'),
    (r'\bvenum\b', 'venum'),
]


class LanguageDetector:
    def normalize_language_code(self, raw_lang: str, text: str) -> Tuple[str, float]:
        """Normalizes ISO language code to Indian dialect format with confidence score."""
        raw = raw_lang.lower().strip() if raw_lang else "hi"
        lang_code = INDIAN_LANG_MAP.get(raw, "hi-IN")

        # Heuristic detection for Hinglish / Tanglish code-mixing based on text script & keywords
        if any(w in text.lower() for w in ["bhai", "chahiye", "dikhao", "daalo", "andar", "saree"]):
            lang_code = "hi-IN"
        elif any(w in text.lower() for w in ["kaattunga", "rubaaykku", "ithula", "venum", "podu"]):
            lang_code = "ta-IN"

        confidence = 0.95 if raw_lang in INDIAN_LANG_MAP else 0.85
        return lang_code, confidence

    def post_process_transcript(self, text: str) -> str:
        """Normalizes transliteration patterns in transcribed text."""
        result = text
        for pattern, repl in NORMALIZATION_PATTERNS:
            result = re.sub(pattern, repl, result, flags=re.IGNORECASE)
        return result.strip()


language_detector = LanguageDetector()
