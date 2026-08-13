import pytest
from shared.models import ConversationState, IntentType
from orchestrator_service.state_machine import transition_state
from orchestrator_service.llm_engine import llm_engine


def test_state_machine_valid_transitions():
    assert transition_state(ConversationState.IDLE, ConversationState.LISTENING) == ConversationState.LISTENING
    assert transition_state(ConversationState.LISTENING, ConversationState.UNDERSTANDING) == ConversationState.UNDERSTANDING
    assert transition_state(ConversationState.UNDERSTANDING, ConversationState.SEARCHING) == ConversationState.SEARCHING
    assert transition_state(ConversationState.SEARCHING, ConversationState.RESPONDING) == ConversationState.RESPONDING
    assert transition_state(ConversationState.RESPONDING, ConversationState.AWAITING_INPUT) == ConversationState.AWAITING_INPUT
    assert transition_state(ConversationState.AWAITING_INPUT, ConversationState.CHECKOUT) == ConversationState.CHECKOUT
    assert transition_state(ConversationState.CHECKOUT, ConversationState.ORDER_CONFIRMED) == ConversationState.ORDER_CONFIRMED


@pytest.mark.asyncio
async def test_rule_based_intent_extraction_search():
    text = "running shoes dikhao Nike 2000 ke andar size 9"
    res = await llm_engine.extract_intent(text, [], [])
    assert res.intent == IntentType.PRODUCT_SEARCH
    assert "Nike" in res.entities.brands
    assert res.entities.max_price == 2000.0
    assert res.entities.size == "9"


@pytest.mark.asyncio
async def test_rule_based_intent_extraction_add_cart():
    text = "dusra wala cart mein daalo"
    res = await llm_engine.extract_intent(text, [], [])
    assert res.intent == IntentType.ADD_TO_CART
    assert res.entities.item_index == 2


@pytest.mark.asyncio
async def test_rule_based_intent_extraction_checkout():
    text = "order kar do COD chahiye"
    res = await llm_engine.extract_intent(text, [], [])
    assert res.intent == IntentType.CHECKOUT
    assert res.entities.payment_method == "COD"
