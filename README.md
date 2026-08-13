# 🎙️ VoiceKart: Vernacular Voice Commerce Engine

**VoiceKart** is a production-hardened Vernacular Voice Commerce engine designed for Tier-2/3 Indian city users. It enables users to discover, compare, and purchase e-commerce products entirely through voice conversations in 8 Indian native languages (**Hindi, Tamil, Telugu, Bengali, Marathi, Kannada, Malayalam, Gujarati**), code-mixing (Hinglish/Tanglish), with zero typing or screen literacy required.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VOICEKART ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐      ┌──────────────┐      ┌──────────────────────────┐ │
│  │ WhatsApp │─────▶│   Gateway    │─────▶│ Conversation Orchestrator│ │
│  │ Business │◀─────│   Service    │◀─────│   (State Machine + LLM)  │ │
│  │   API    │      │  (FastAPI)   │      │        (FastAPI)         │ │
│  └──────────┘      └──────────────┘      └────────┬─────────────────┘ │
│                                                   │                   │
│          ┌────────────────────────────────────────┴────────┐          │
│          │                                                 │          │
│    ┌─────▼────┐     ┌────▼─────┐      ┌──────────┐   ┌─────▼────┐ │
│    │ STT      │     │ TTS      │      │ Product  │   │ Order    │ │
│    │ Service  │     │ Service  │      │ Catalog  │   │ Service  │ │
│    │(Whisper) │     │(11Labs)  │      │ Service  │   │(FastAPI) │ │
│    └──────────┘     └──────────┘      └────┬─────┘   └──────────┘ │
│                                            │                      │
│                                       ┌────▼─────┐                │
│                                       │Elastic   │                │
│                                       │Search DB │                │
│                                       └──────────┘                │
│                                                                     │
│ Cross-Cutting: Redis (sessions + cache) | PostgreSQL (orders)       │
│ MinIO/S3 (audio) | Prometheus + Grafana                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Microservices Breakdown

| Service Name | Port | Primary Responsibility |
|--------------|------|------------------------|
| **Gateway Service** | `8001` | WhatsApp Cloud API Webhook handler, HMAC verification, message deduplication, and `/simulate` API for testing without WhatsApp. |
| **Conversation Orchestrator** | `8002` | State Machine transitions, LLM intent extraction (`PRODUCT_SEARCH`, `ADD_TO_CART`, `CHECKOUT`, etc.), session management, response generation. |
| **TTS Service** | `8003` | ElevenLabs API v1 integration, streaming synthesis, voice mapping across 8 Indian languages, Redis caching (7-day TTL), gTTS fallback. |
| **STT Service** | `8004` | OpenAI Whisper transcription (`whisper-1`), audio preprocessing (FFmpeg 16kHz mono, pydub silence trimming), Indian language detection. |
| **Catalog Service** | `8005` | Elasticsearch 8.x search engine with vernacular synonym mapping ("juta" → shoes, "chappal" → sandals), BM25 + vector matching, in-memory fallback. |
| **Order Service** | `8006` | PostgreSQL cart management, order creation, GST calculation, Razorpay UPI payment link generation & COD, proactive voice notifications. |

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local scripts/tests)
- FFmpeg (for local audio processing)

### 1. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. Launch All Microservices & Infrastructure
Use `docker-compose` or `make`:
```bash
make dev
# OR
docker-compose up --build
```

### 3. Seed Catalog with 500+ Realistic Products
Run the catalog seeding script:
```bash
make seed-catalog
# OR
python scripts/seed_catalog.py
```

---

## 🧪 Testing Without WhatsApp (The `/simulate` REST Endpoint)

To test the entire end-to-end voice commerce engine without requiring a WhatsApp Business API account:

### Text Input Query (Hindi/Hinglish):
```bash
curl -X POST http://localhost:8001/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "user_phone": "+919876543210",
    "text_input": "Bhai, mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9",
    "language": "hi-IN"
  }'
```

### Example Simulation Output:
```json
{
  "session_id": "sess_3210_1723500000",
  "transcribed_text": "Bhai, mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9",
  "detected_language": "hi-IN",
  "extracted_intent": "PRODUCT_SEARCH",
  "response_text": "Ji bilkul! Maine aapke liye 3 sabse badhiya options dhundhe hain:\n1. Nike Revolution 6 Running Shoes, daam sirf ₹1,899 rupaye.\n2. Adidas Galaxy 6 Running Shoes, daam sirf ₹1,999 rupaye.\nKya main inme se koi aapke cart mein daal doon?",
  "audio_url": "http://localhost:9000/voicekart-audio/audio/abc-123.mp3",
  "latency_ms": 1420.5,
  "cart": [],
  "search_results_count": 2
}
```

---

## 📊 Observability & Monitoring

Prometheus metrics are exposed across all services at `/metrics`:
- `voicekart_e2e_response_latency_seconds`: End-to-end response latency distribution.
- `voicekart_elevenlabs_quota_remaining_pct`: Gauge monitoring ElevenLabs character quota.
- `voicekart_fallback_tts_activations_total`: Counter tracking gTTS fallback activations.
- `voicekart_http_requests_total`: Request counter tagged by service, status code, and endpoint.

Access Prometheus & Grafana:
- **Prometheus UI**: `http://localhost:9090`
- **Grafana Dashboard**: Import `monitoring/grafana_dashboard.json` into Grafana.

---

## 🧪 Running Automated Tests

Run the full Pytest unit and integration test suite:
```bash
make test
```
# Vernacular-Voice-System
