import logging
from typing import List, Dict, Any, Optional
from elasticsearch import AsyncElasticsearch

from shared.config import settings
from shared.models import Product, SearchQueryFilters

logger = logging.getLogger("catalog.es_client")

VERNACULAR_SYNONYMS = [
    "juta, joota, shoes, sneakers => shoes",
    "chappal, sandals, slippers, flipflops => sandals",
    "kapda, kapde, clothes, clothing, dress => clothing",
    "chai, patti, tea, darjeeling => tea",
    "sari, saree, sela => saree",
    "phone, mobile, smartphone => mobile"
]


class ElasticsearchCatalogClient:
    def __init__(self):
        self.es = None
        self.index_name = settings.ELASTICSEARCH_INDEX

    async def connect(self):
        try:
            self.es = AsyncElasticsearch(
                settings.ELASTICSEARCH_HOST,
                basic_auth=(settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD) if settings.ELASTICSEARCH_USER else None,
                verify_certs=False
            )
            if not await self.es.indices.exists(index=self.index_name):
                await self.create_index()
        except Exception as e:
            logger.warning(f"Elasticsearch connection deferred/failed: {e}")
            self.es = None

    async def create_index(self):
        mapping = {
            "settings": {
                "analysis": {
                    "filter": {
                        "vernacular_synonyms": {
                            "type": "synonym",
                            "synonyms": VERNACULAR_SYNONYMS
                        }
                    },
                    "analyzer": {
                        "vernacular_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "vernacular_synonyms"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "product_id": {"type": "keyword"},
                    "title": {
                        "properties": {
                            "en": {"type": "text", "analyzer": "vernacular_analyzer"},
                            "hi": {"type": "text", "analyzer": "standard"}
                        }
                    },
                    "brand": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "price": {"type": "float"},
                    "mrp": {"type": "float"},
                    "discount_pct": {"type": "integer"},
                    "sizes": {"type": "keyword"},
                    "colors": {"type": "keyword"},
                    "rating": {"type": "float"},
                    "in_stock": {"type": "boolean"}
                }
            }
        }
        try:
            await self.es.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Elasticsearch index '{self.index_name}' created successfully")
        except Exception as e:
            logger.error(f"Failed creating ES index: {e}")

    async def index_product(self, product: Product) -> bool:
        if not self.es:
            return False
        try:
            await self.es.index(
                index=self.index_name,
                id=product.product_id,
                document=product.model_dump(exclude_none=True)
            )
            return True
        except Exception as e:
            logger.error(f"Error indexing product {product.product_id}: {e}")
            return False

    async def search(self, query: str, filters: SearchQueryFilters, limit: int = 5) -> List[Product]:
        if not self.es:
            return []

        must_clauses: List[Dict[str, Any]] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title.en^3", "title.hi^3", "category^2", "brand^2"],
                    "fuzziness": "AUTO"
                }
            }
        ]
        filter_clauses: List[Dict[str, Any]] = [{"term": {"in_stock": True}}]

        if filters.price_max:
            filter_clauses.append({"range": {"price": {"lte": filters.price_max}}})
        if filters.price_min:
            filter_clauses.append({"range": {"price": {"gte": filters.price_min}}})
        if filters.brands:
            filter_clauses.append({"terms": {"brand": filters.brands}})
        if filters.sizes:
            filter_clauses.append({"terms": {"sizes": filters.sizes}})

        body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "size": limit
        }

        try:
            res = await self.es.search(index=self.index_name, body=body)
            hits = res["hits"]["hits"]
            return [Product(**hit["_source"]) for hit in hits]
        except Exception as e:
            logger.error(f"ES search error: {e}")
            return []


es_catalog_client = ElasticsearchCatalogClient()
