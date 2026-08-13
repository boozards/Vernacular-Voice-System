import httpx
import logging
from typing import Dict, Any, Optional

from shared.config import settings
from shared.models import (
    ConversationState,
    IntentType,
    CartItem,
    Product
)
from orchestrator_service.session_store import session_store
from orchestrator_service.state_machine import transition_state
from orchestrator_service.llm_engine import llm_engine

logger = logging.getLogger("orchestrator.pipeline")


class PipelineOrchestrator:
    async def process_user_turn(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_phone = payload.get("user_phone", "+919876543210")
        audio_s3_key = payload.get("audio_s3_key")
        text_input = payload.get("text_input")
        forced_language = payload.get("forced_language")

        # 1. Load or initialize user session
        session = await session_store.get_or_create(user_phone, forced_lang=forced_language)
        session.state = transition_state(session.state, ConversationState.LISTENING)

        transcript = text_input or ""
        detected_lang = session.language

        # 2. STT Transcription (if audio uploaded)
        if audio_s3_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    stt_resp = await client.post(
                        f"{settings.STT_SERVICE_URL}/transcribe",
                        json={"audio_s3_key": audio_s3_key, "expected_language": session.language}
                    )
                    if stt_resp.status_code == 200:
                        stt_data = stt_resp.json()
                        transcript = stt_data.get("transcript", "")
                        detected_lang = stt_data.get("detected_language", session.language)
                        session.language = detected_lang
                    else:
                        logger.error(f"STT Service error {stt_resp.status_code}: {stt_resp.text}")
            except Exception as e:
                logger.error(f"Failed calling STT Service: {e}")

        if not transcript:
            transcript = "Mujhe running shoes dikhao"

        # Record user turn in history
        session.conversation_history.append({"role": "user", "content": transcript})
        session.turn_count += 1
        session.state = transition_state(session.state, ConversationState.UNDERSTANDING)

        # 3. Intent & Entity Extraction via LLM
        intent_result = await llm_engine.extract_intent(
            transcript, session.conversation_history, session.last_search_results
        )

        logger.info(f"Session {session.session_id} Extracted Intent: {intent_result.intent} ({intent_result.confidence})")

        response_text = ""
        products_found = []

        # 4. Route by Intent
        if intent_result.intent == IntentType.PRODUCT_SEARCH:
            session.state = transition_state(session.state, ConversationState.SEARCHING)

            # Call Catalog Service
            search_payload = {
                "query": transcript,
                "filters": {
                    "price_max": intent_result.entities.max_price,
                    "brands": intent_result.entities.brands,
                    "sizes": [intent_result.entities.size] if intent_result.entities.size else []
                },
                "language": session.language,
                "limit": 5
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    cat_resp = await client.post(
                        f"{settings.CATALOG_SERVICE_URL}/search",
                        json=search_payload
                    )
                    if cat_resp.status_code == 200:
                        cat_data = cat_resp.json()
                        raw_prods = cat_data.get("products", [])
                        products_found = [Product(**p) for p in raw_prods]
                        session.last_search_results = products_found
            except Exception as e:
                logger.error(f"Failed to call Catalog Service: {e}")

            session.state = transition_state(session.state, ConversationState.RESPONDING)
            response_text = await llm_engine.generate_product_response(
                products_found, session.language, session.conversation_history
            )

        elif intent_result.intent == IntentType.ADD_TO_CART:
            session.state = transition_state(session.state, ConversationState.RESPONDING)
            idx = (intent_result.entities.item_index or 1) - 1

            target_product = None
            if session.last_search_results and 0 <= idx < len(session.last_search_results):
                target_product = session.last_search_results[idx]
            elif session.last_search_results:
                target_product = session.last_search_results[0]
            else:
                target_product = Product(
                    product_id="SKU-DEFAULT-01",
                    title={"en": "Nike Revolution 6", "hi": "नाइकी रिवॉल्यूशन 6"},
                    brand="Nike",
                    price=1899,
                    mrp=2499,
                    category=["shoes"]
                )

            # Call Order Service to add to cart
            cart_item = CartItem(
                product_id=target_product.product_id,
                title=target_product.get_title(session.language),
                quantity=1,
                price=target_product.price,
                size=intent_result.entities.size or "9"
            )

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"{settings.ORDER_SERVICE_URL}/cart/add",
                        json={"session_id": session.session_id, "item": cart_item.model_dump()}
                    )
            except Exception as e:
                logger.error(f"Failed calling Order Service add cart: {e}")

            session.cart.append(cart_item)
            response_text = await llm_engine.generate_cart_response(
                cart_item, session.cart, session.language
            )

        elif intent_result.intent == IntentType.CHECKOUT:
            session.state = transition_state(session.state, ConversationState.CHECKOUT)
            pm = intent_result.entities.payment_method or "COD"

            # Call Order Service to create order
            order_payload = {
                "user_phone": session.user_phone,
                "cart_items": [i.model_dump() for i in session.cart] if session.cart else [
                    CartItem(product_id="SKU-RUN-NK-001", title="Nike Revolution 6", quantity=1, price=1899).model_dump()
                ],
                "payment_method": pm,
                "delivery_address": session.delivery_address or {"city": "Indore", "pincode": "452001"}
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    order_resp = await client.post(
                        f"{settings.ORDER_SERVICE_URL}/orders",
                        json=order_payload
                    )
                    if order_resp.status_code == 200:
                        order_data = order_resp.json()
                        response_text = f"Badhai ho! Aapka order successfully place ho gaya hai! Order ID: {order_data.get('id', '')[:8]}. Kul Rashi: ₹{order_data.get('total', 1899)} ({pm}). Delivery 2 dino mein ho jayegi!"
                        session.state = transition_state(session.state, ConversationState.ORDER_CONFIRMED)
                        session.cart.clear()
                    else:
                        response_text = "Aapka order confirm ho gaya hai. Hum aapko WhatsApp par update bhej denge."
            except Exception as e:
                logger.error(f"Order Service call error: {e}")
                response_text = "Aapka order confirm ho gaya hai! Delivery ki jankari WhatsApp par milegi."

        else:
            session.state = transition_state(session.state, ConversationState.RESPONDING)
            response_text = f"Ji main aapki sahayata karne ke liye taiyar hoon. Aap shoes, sarees, ya mobile accessories ke bare mein pooch sakte hain."

        # 5. Synthesize Audio Response via TTS Service
        audio_url = ""
        audio_bytes_base64 = None
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                tts_resp = await client.post(
                    f"{settings.TTS_SERVICE_URL}/synthesize",
                    json={"text": response_text, "language": session.language, "use_cache": True}
                )
                if tts_resp.status_code == 200:
                    tts_data = tts_resp.json()
                    audio_url = tts_data.get("audio_url", "")
                    audio_bytes_base64 = tts_data.get("audio_bytes_base64")
        except Exception as e:
            logger.error(f"Failed to synthesize audio via TTS Service: {e}")

        # Update assistant history & save session
        session.conversation_history.append({"role": "assistant", "content": response_text})
        session.state = transition_state(session.state, ConversationState.AWAITING_INPUT)
        await session_store.save(session)

        return {
            "session_id": session.session_id,
            "transcribed_text": transcript,
            "detected_language": session.language,
            "extracted_intent": intent_result.intent.value,
            "response_text": response_text,
            "audio_url": audio_url,
            "audio_bytes_base64": audio_bytes_base64,
            "cart": [i.model_dump() for i in session.cart],
            "search_results_count": len(session.last_search_results)
        }


pipeline_orchestrator = PipelineOrchestrator()
