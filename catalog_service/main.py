import logging
from fastapi import FastAPI, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.config import settings
from shared.logging import setup_logger
from shared.middleware import CorrelationAndMetricsMiddleware
from shared.models import SearchRequest, SearchResponse, Product
from catalog_service.es_client import es_catalog_client
from catalog_service.search_engine import catalog_search_engine

setup_logger("catalog_service", settings.LOG_LEVEL)
logger = logging.getLogger("catalog_service")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await es_catalog_client.connect()
    yield

app = FastAPI(
    title="VoiceKart Product Catalog Service",
    description="Elasticsearch-backed multilingual product search service with vernacular query mapping",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationAndMetricsMiddleware, service_name="catalog_service")




@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "catalog_service",
        "elasticsearch": "connected" if es_catalog_client.es else "fallback_mode",
        "env": settings.ENV
    }


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        products, total = await catalog_search_engine.search_products(
            query=req.query,
            filters=req.filters,
            limit=req.limit
        )
        return SearchResponse(
            products=products,
            total_count=total,
            applied_filters=req.filters.model_dump()
        )
    except Exception as e:
        logger.error(f"Catalog search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Catalog search error: {str(e)}"
        )


@app.post("/index-product")
async def index_product(product: Product):
    indexed_es = await es_catalog_client.index_product(product)
    catalog_search_engine.add_products([product])
    return {"status": "indexed", "elasticsearch": indexed_es}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("catalog_service.main:app", host="0.0.0.0", port=8005, reload=True)
