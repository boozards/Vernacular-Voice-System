import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from shared.config import settings
from shared.models import (
    IntentResult,
    IntentType,
    EntityExtraction,
    Product,
    CartItem,
    OrderResponse
)

logger = logging.getLogger("orchestrator.llm")

# Initialize OpenAI Client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


INTENT_EXTRACTION_SYSTEM_PROMPT = """
You are VoiceKart AI, an intelligent intent extractor for Vernacular Indian E-commerce voice interactions.
Supported Indian languages: Hindi (hi-IN), Tamil (ta-IN), Telugu (te-IN), Bengali (bn-IN), Marathi (mr-IN), Kannada (kn-IN), Malayalam (ml-IN), Gujarati (gu-IN), Hinglish, Tanglish.

Your job is to analyze the user's transcript, conversation context, and return a JSON object with:
1. intent: One of ["PRODUCT_SEARCH", "PRODUCT_DETAIL", "ADD_TO_CART", "COMPARE", "CHECKOUT", "ORDER_STATUS", "CANCEL_RETURN", "REORDER", "UNKNOWN"]
2. confidence: Float between 0.0 and 1.0
3. entities: JSON object containing:
   - category: e.g. "running_shoes", "saree", "kurti", "tea", "earphones"
   - brands: list of strings, e.g. ["Nike", "Adidas"]
   - max_price: float or null
   - min_price: float or null
   - size: e.g. "9", "M", "XL" or null
   - color: e.g. "red", "black" or null
   - quantity: int (default 1)
   - item_index: int or null (1 for first item, 2 for second item referenced in previous turn like "dusra wala" or "second one")
   - payment_method: "COD" or "UPI"

Context Rules:
- If user says "dusra wala cart mein daalo" -> intent is ADD_TO_CART, item_index is 2.
- If user says "pehla aur doosra mein kya fark hai" -> intent is COMPARE.
- If user says "order kar do COD se" -> intent is CHECKOUT, payment_method is COD.
- If user says "wapas karna hai" -> intent is CANCEL_RETURN.

Return ONLY valid JSON matching this schema:
{
  "intent": "PRODUCT_SEARCH",
  "confidence": 0.98,
  "entities": {
    "category": "running_shoes",
    "brands": ["Nike", "Adidas"],
    "max_price": 2000,
    "size": "9",
    "item_index": null,
    "payment_method": "COD"
  }
}
"""


RESPONSE_GEN_SYSTEM_PROMPT = """
You are VoiceKart's warm, friendly, market-vendor AI assistant speaking to a customer in India in native language ({language}).
Your tone must be conversational, trustworthy, respectful, helpful, and natural (like a warm local दुकानदार/shopkeeper).

Rules:
1. Speak in the EXACT language requested: {language}. Use natural conversational expressions (e.g. Hindi: "Ji bilkul sir! AAPKE liye 3 sabse badhiya options hain...").
2. Voice interface is linear, NOT visual! Never list more than 3 products.
3. For each product, mention key highlights clearly: Title, Brand, Price in INR ("sirf ₹1,899"), Discount if any, and Size/Color.
4. Always end your response with a friendly, interactive question to keep the shopping conversation going (e.g. "Aapko pehla wala pasand aaya ya doosra cart mein daalun?").
5. Do NOT use markdown tables or complex ASCII diagrams. Keep it pure spoken natural text!
"""


class LLMEngine:
    async def extract_intent(
        self,
        transcript: str,
        history: List[Dict[str, str]],
        last_results: List[Product]
    ) -> IntentResult:
        """Extracts intent and entities using LLM with fallback rule parser for robustness."""
        if settings.OPENAI_API_KEY.startswith("mock"):
            return self._fallback_rule_intent_extractor(transcript)

        messages = [
            {"role": "system", "content": INTENT_EXTRACTION_SYSTEM_PROMPT},
        ]
        
        # Add context from history
        for turn in history[-4:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        
        messages.append({"role": "user", "content": f"Transcript: {transcript}"})

        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content
            parsed = json.loads(raw_content)

            intent_str = parsed.get("intent", "UNKNOWN")
            confidence = parsed.get("confidence", 0.9)
            ent_data = parsed.get("entities", {})

            return IntentResult(
                intent=IntentType(intent_str) if intent_str in IntentType.__members__ else IntentType.UNKNOWN,
                confidence=confidence,
                entities=EntityExtraction(**ent_data)
            )

        except Exception as e:
            logger.error(f"LLM intent extraction failed: {e}, using rule fallback")
            return self._fallback_rule_intent_extractor(transcript)

    def _fallback_rule_intent_extractor(self, text: str) -> IntentResult:
        """Rule-based heuristic parser for fallback and test execution."""
        t = text.lower()
        entities = EntityExtraction()

        # Check Checkout
        if any(w in t for w in ["order", "buy", "khareed", "cod", "checkout", "le lo", "bhejo"]):
            if "cod" in t:
                entities.payment_method = "COD"
            elif "upi" in t or "online" in t:
                entities.payment_method = "UPI"
            return IntentResult(intent=IntentType.CHECKOUT, confidence=0.9, entities=entities)

        # Check Add to Cart
        if any(w in t for w in ["cart", "daalo", "add", "rakho", "le lo"]):
            if "dusra" in t or "doosra" in t or "second" in t or "2" in t:
                entities.item_index = 2
            elif "pehla" in t or "first" in t or "1" in t:
                entities.item_index = 1
            elif "teesra" in t or "third" in t or "3" in t:
                entities.item_index = 3
            return IntentResult(intent=IntentType.ADD_TO_CART, confidence=0.9, entities=entities)

        # Check Order Status
        if any(w in t for w in ["status", "kahan tak aaya", "delivery kab", "track"]):
            return IntentResult(intent=IntentType.ORDER_STATUS, confidence=0.9, entities=entities)

        # Check Cancel / Return
        if any(w in t for w in ["cancel", "wapas", "return", "radd"]):
            return IntentResult(intent=IntentType.CANCEL_RETURN, confidence=0.9, entities=entities)

        # Check Compare
        if any(w in t for w in ["fark", "compare", "dono mein", "vithyaasam"]):
            return IntentResult(intent=IntentType.COMPARE, confidence=0.9, entities=entities)

        # Product Search Entity Extraction
        if "nike" in t:
            entities.brands.append("Nike")
        if "adidas" in t:
            entities.brands.append("Adidas")
        if "puma" in t:
            entities.brands.append("Puma")
            
        if "shoe" in t or "juta" in t or "chappal" in t:
            entities.category = "shoes"
        elif "saree" in t or "sela" in t:
            entities.category = "saree"
        elif "kurti" in t or "kurta" in t:
            entities.category = "kurti"

        if "2000" in t:
            entities.max_price = 2000.0
        elif "500" in t:
            entities.max_price = 500.0
        elif "1000" in t:
            entities.max_price = 1000.0

        if "9" in t:
            entities.size = "9"
        elif "8" in t:
            entities.size = "8"

        if "dusra" in t or "doosra" in t or "second" in t:
            entities.item_index = 2

        return IntentResult(intent=IntentType.PRODUCT_SEARCH, confidence=0.85, entities=entities)

    async def generate_product_response(
        self, products: List[Product], language: str, history: List[Dict[str, str]]
    ) -> str:
        """Generates conversational shopkeeper response for product search results."""
        if not products:
            if "ta" in language:
                return "Mannichidunga, neenga ketta product stock la illai. Vera edhaavadhu kaattattuma?"
            return "Maaf kijiyega, aapke budget mein abhi yeh product available nahi hai. Kya main koi aur option dikhaun?"

        if settings.OPENAI_API_KEY.startswith("mock"):
            return self._fallback_product_response(products, language)

        prompt = f"Target Language: {language}\nUser context: Product Search\n\nTop Products Found:\n"
        for i, p in enumerate(products[:3], 1):
            title = p.get_title(language)
            prompt += f"{i}. {title} by {p.brand} - Price ₹{p.price} (MRP ₹{p.mrp}, {p.discount_pct}% OFF). Sizes: {', '.join(p.sizes)}\n"

        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": RESPONSE_GEN_SYSTEM_PROMPT.format(language=language)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return self._fallback_product_response(products, language)

    def _fallback_product_response(self, products: List[Product], language: str) -> str:
        """Rule fallback product response."""
        p_list = products[:3]
        if "ta" in language:
            res = f"Aha! Naan ungalukku {len(p_list)} nalla options kandupidichirukken.\n"
            for i, p in enumerate(p_list, 1):
                res += f"Option {i}: {p.get_title('ta-IN')}, aivavu ₹{p.price}.\n"
            res += "Edhu ungalukku pidichirukku? Cart la podattuma?"
            return res

        res = f"Ji bilkul! Maine aapke liye {len(p_list)} sabse badhiya options dhundhe hain:\n"
        for i, p in enumerate(p_list, 1):
            res += f"Pehla option {i}: {p.get_title('hi-IN')}, daam sirf {int(p.price)} rupaye.\n"
        res += "Kya main inme se koi aapke cart mein daal doon ya dusra wala dekhna chahenge?"
        return res

    async def generate_cart_response(
        self, item: CartItem, total_cart: List[CartItem], language: str
    ) -> str:
        """Generates response after adding item to cart."""
        cart_count = sum(i.quantity for i in total_cart)
        cart_total = sum(i.price * i.quantity for i in total_cart)

        if "ta" in language:
            return f"Super! {item.title} cart la sethachu. Unga cart la motham {cart_count} items irukku, total ₹{cart_total}. Order place panna Readiness ah?"

        return f"Wah! {item.title} aapke cart mein daal diya gaya hai. Abhi cart mein total {cart_count} items hain, kul daam ₹{cart_total} rupaye. Kya abhi order confirmation kar dein (COD ya UPI)?"

    async def generate_order_response(self, order: OrderResponse, language: str) -> str:
        """Generates order confirmation response."""
        if "ta" in language:
            return f"Vazhthukkal! Unga order successfully confirm aayiduchu. Order ID: {order.id[:8]}. Total ₹{order.total} ({order.payment_method}). Delivery 2-3 naalaikulla aayidum!"

        return f"Bhut bhut badhai ho! Aapka order confirm ho gaya hai. Order ID: {order.id[:8]}. Kul daam: ₹{order.total} rupaye ({order.payment_method}). Delivery agle 2 se 3 din mein ho jayegi."


llm_engine = LLMEngine()
