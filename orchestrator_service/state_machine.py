import logging
from shared.models import ConversationState

logger = logging.getLogger("orchestrator.state_machine")

# Allowed transitions matrix
VALID_TRANSITIONS = {
    ConversationState.IDLE: [ConversationState.LISTENING],
    ConversationState.LISTENING: [ConversationState.UNDERSTANDING],
    ConversationState.UNDERSTANDING: [ConversationState.SEARCHING, ConversationState.RESPONDING, ConversationState.CHECKOUT],
    ConversationState.SEARCHING: [ConversationState.RESPONDING],
    ConversationState.RESPONDING: [ConversationState.AWAITING_INPUT],
    ConversationState.AWAITING_INPUT: [ConversationState.LISTENING, ConversationState.CHECKOUT, ConversationState.IDLE],
    ConversationState.CHECKOUT: [ConversationState.ORDER_CONFIRMED, ConversationState.AWAITING_INPUT],
    ConversationState.ORDER_CONFIRMED: [ConversationState.IDLE, ConversationState.AWAITING_INPUT]
}


def transition_state(current_state: ConversationState, target_state: ConversationState) -> ConversationState:
    """Validates and executes state machine transition."""
    allowed = VALID_TRANSITIONS.get(current_state, [])
    if target_state in allowed or target_state == current_state:
        logger.info(f"State transition: {current_state.value} -> {target_state.value}")
        return target_state
    
    logger.warning(f"Invalid state transition attempted: {current_state.value} -> {target_state.value}. Forcing {target_state.value}")
    return target_state
