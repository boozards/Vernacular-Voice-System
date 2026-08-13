from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class LanguageCode(str, Enum):
    HINDI = "hi-IN"
    TAMIL = "ta-IN"
    TELUGU = "te-IN"
    BENGALI = "bn-IN"
    MARATHI = "mr-IN"
    KANNADA = "kn-IN"
    MALAYALAM = "ml-IN"
    GUJARATI = "gu-IN"
    ENGLISH = "en-IN"


class IntentType(str, Enum):
    PRODUCT_SEARCH = "PRODUCT_SEARCH"
    PRODUCT_DETAIL = "PRODUCT_DETAIL"
    ADD_TO_CART = "ADD_TO_CART"
    COMPARE = "COMPARE"
    CHECKOUT = "CHECKOUT"
    ORDER_STATUS = "ORDER_STATUS"
    CANCEL_RETURN = "CANCEL_RETURN"
    REORDER = "REORDER"
    UNKNOWN = "UNKNOWN"


class ConversationState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    SEARCHING = "SEARCHING"
    RESPONDING = "RESPONDING"
    AWAITING_INPUT = "AWAITING_INPUT"
    CHECKOUT = "CHECKOUT"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"


class Product(BaseModel):
    product_id: str
    title: Dict[str, str] = Field(default_factory=dict)  # {"en": "Nike...", "hi": "..."}
    description: Dict[str, str] = Field(default_factory=dict)
    category: List[str] = Field(default_factory=list)
    brand: str
    price: float
    mrp: float
    discount_pct: int = 0
    sizes: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    rating: float = 4.5
    review_count: int = 100
    in_stock: bool = True
    image_url: str = ""
    embedding: Optional[List[float]] = None

    def get_title(self, lang: str = "hi-IN") -> str:
        lang_short = lang.split("-")[0]
        return self.title.get(lang_short) or self.title.get("en") or self.brand


class CartItem(BaseModel):
    product_id: str
    title: str
    quantity: int = 1
    price: float
    size: Optional[str] = None
    color: Optional[str] = None


class SearchQueryFilters(BaseModel):
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    brands: List[str] = Field(default_factory=list)
    sizes: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    in_stock_only: bool = True


class SearchRequest(BaseModel):
    query: str
    filters: SearchQueryFilters = Field(default_factory=SearchQueryFilters)
    language: str = "hi-IN"
    limit: int = 5


class SearchResponse(BaseModel):
    products: List[Product]
    total_count: int
    applied_filters: Dict[str, Any] = Field(default_factory=dict)


class EntityExtraction(BaseModel):
    category: Optional[str] = None
    brands: List[str] = Field(default_factory=list)
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: int = 1
    item_index: Optional[int] = None  # 1 for first item, 2 for second, etc.
    payment_method: Optional[str] = "COD"  # COD or UPI


class IntentResult(BaseModel):
    intent: IntentType
    confidence: float = 0.95
    entities: EntityExtraction = Field(default_factory=EntityExtraction)
    reasoning: Optional[str] = None


class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SessionState(BaseModel):
    session_id: str
    user_phone: str
    language: str = "hi-IN"
    state: ConversationState = ConversationState.IDLE
    turn_count: int = 0
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    conversation_summary: Optional[str] = None
    cart: List[CartItem] = Field(default_factory=list)
    last_search_results: List[Product] = Field(default_factory=list)
    active_filters: Dict[str, Any] = Field(default_factory=dict)
    delivery_address: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class STTRequest(BaseModel):
    audio_s3_key: Optional[str] = None
    audio_bytes_base64: Optional[str] = None
    expected_language: Optional[str] = None


class STTResponse(BaseModel):
    transcript: str
    detected_language: str
    confidence: float
    duration_ms: float


class TTSRequest(BaseModel):
    text: str
    language: str = "hi-IN"
    use_cache: bool = True


class TTSResponse(BaseModel):
    audio_url: str
    audio_bytes_base64: Optional[str] = None
    duration_ms: float
    cached: bool
    characters_used: int


class OrderCreateRequest(BaseModel):
    user_phone: str
    cart_items: List[CartItem]
    payment_method: str = "COD"  # 'COD' or 'UPI'
    delivery_address: Optional[Dict[str, Any]] = None


class OrderResponse(BaseModel):
    id: str
    user_phone: str
    items: List[CartItem]
    subtotal: float
    gst: float
    delivery_fee: float
    total: float
    payment_method: str
    payment_status: str
    delivery_address: Dict[str, Any]
    status: str
    payment_link: Optional[str] = None
    created_at: str


class SimulateRequest(BaseModel):
    user_phone: str = "+919876543210"
    text_input: Optional[str] = None
    audio_bytes_base64: Optional[str] = None
    language: Optional[str] = "hi-IN"


class SimulateResponse(BaseModel):
    session_id: str
    transcribed_text: str
    detected_language: str
    extracted_intent: str
    response_text: str
    audio_url: str
    audio_bytes_base64: Optional[str] = None
    latency_ms: float
    cart: List[CartItem]
    search_results_count: int
