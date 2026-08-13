import logging
from typing import List, Tuple, Dict, Any
from shared.models import Product, SearchQueryFilters
from catalog_service.es_client import es_catalog_client

logger = logging.getLogger("catalog.search_engine")

# In-memory fallback product catalog for zero-dependency local execution
FALLBACK_PRODUCTS: List[Product] = [
    Product(
        product_id="SKU-RUN-NK-001",
        title={"en": "Nike Revolution 6 Running Shoes", "hi": "नाइकी रिवॉल्यूशन 6 रनिंग शूज़"},
        description={"en": "Lightweight breathable running shoes", "hi": "हल्के और आरामदायक रनिंग जूते"},
        category=["shoes", "running", "sports"],
        brand="Nike",
        price=1899.0,
        mrp=2499.0,
        discount_pct=24,
        sizes=["7", "8", "9", "10"],
        colors=["black", "blue"],
        rating=4.5,
        review_count=1250,
        in_stock=True,
        image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff"
    ),
    Product(
        product_id="SKU-RUN-AD-002",
        title={"en": "Adidas Galaxy 6 Running Shoes", "hi": "एडीडास गैलेक्सी 6 रनिंग शूज़"},
        description={"en": "Cushioned mesh sports shoes", "hi": "सॉफ्ट और मजबूत स्पोर्ट्स शूज़"},
        category=["shoes", "running", "sports"],
        brand="Adidas",
        price=1999.0,
        mrp=2999.0,
        discount_pct=33,
        sizes=["8", "9", "10"],
        colors=["white", "black"],
        rating=4.4,
        review_count=890,
        in_stock=True,
        image_url="https://images.unsplash.com/photo-1520256862855-398228c41684"
    ),
    Product(
        product_id="SKU-ETH-SR-003",
        title={"en": "Kanjivaram Soft Silk Saree (Red)", "hi": "कांजीवरम सॉफ्ट सिल्क साड़ी (लाल)"},
        description={"en": "Traditional woven zari border saree", "hi": "ट्रेडिशनल ज़री बॉर्डर वाली लाल सिल्क साड़ी"},
        category=["saree", "ethnic", "clothing"],
        brand="FabIndia",
        price=499.0,
        mrp=1299.0,
        discount_pct=61,
        sizes=["Free Size"],
        colors=["red"],
        rating=4.6,
        review_count=3200,
        in_stock=True,
        image_url="https://images.unsplash.com/photo-1610030469983-98e550d6193c"
    ),
    Product(
        product_id="SKU-TEA-DJ-004",
        title={"en": "Tata Tea Gold Darjeeling Tea 500g", "hi": "टाटा टी गोल्ड दार्जिलिंग चाय 500g"},
        description={"en": "Rich aroma premium black tea", "hi": "कड़क स्वाद और सुगंध वाली चाय patti"},
        category=["groceries", "tea"],
        brand="Tata Tea",
        price=320.0,
        mrp=380.0,
        discount_pct=15,
        sizes=["500g"],
        colors=[],
        rating=4.8,
        review_count=5400,
        in_stock=True,
        image_url="https://images.unsplash.com/photo-1576092768241-dec231879fc3"
    ),
    Product(
        product_id="SKU-ACC-BT-005",
        title={"en": "boAt Rockerz 255 Pro+ Bluetooth Neckband", "hi": "बोट रॉकर्ज 255 प्रो+ ब्लूटूथ नेकबैंड"},
        description={"en": "40H battery playback with ASAP charge", "hi": "दारुण साउंड और लंबी बैटरी लाइफ वाला इयरफोन"},
        category=["electronics", "earphones", "accessories"],
        brand="boAt",
        price=1299.0,
        mrp=2990.0,
        discount_pct=56,
        sizes=["One Size"],
        colors=["black", "blue", "red"],
        rating=4.3,
        review_count=15400,
        in_stock=True,
        image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e"
    )
]


class CatalogSearchEngine:
    def __init__(self):
        self.in_memory_catalog: List[Product] = list(FALLBACK_PRODUCTS)

    def add_products(self, products: List[Product]):
        self.in_memory_catalog.extend(products)

    async def search_products(
        self, query: str, filters: SearchQueryFilters, limit: int = 5
    ) -> Tuple[List[Product], int]:
        """Performs search via ES if available, otherwise uses in-memory query filter engine."""
        es_results = await es_catalog_client.search(query, filters, limit)
        if es_results:
            return es_results, len(es_results)

        # Fallback In-Memory Filtering
        q_lower = query.lower()
        matched = []

        for p in self.in_memory_catalog:
            title_en = p.title.get("en", "").lower()
            title_hi = p.title.get("hi", "").lower()
            cat_str = " ".join(p.category).lower()
            brand_str = p.brand.lower()

            # Vernacular Synonym Matching
            is_match = False
            if any(term in title_en or term in title_hi or term in cat_str or term in brand_str for term in q_lower.split()):
                is_match = True
            elif "shoe" in q_lower or "juta" in q_lower or "chappal" in q_lower:
                is_match = "shoes" in p.category or "saree" not in p.category
            elif "saree" in q_lower or "sela" in q_lower:
                is_match = "saree" in p.category
            elif "chai" in q_lower or "tea" in q_lower:
                is_match = "tea" in p.category
            elif "earphone" in q_lower or "bluetooth" in q_lower:
                is_match = "earphones" in p.category or "electronics" in p.category

            # Apply Filters
            if is_match:
                if filters.price_max and p.price > filters.price_max:
                    continue
                if filters.price_min and p.price < filters.price_min:
                    continue
                if filters.brands and p.brand not in filters.brands:
                    continue
                if filters.sizes and not any(s in p.sizes for s in filters.sizes):
                    continue
                
                matched.append(p)

        if not matched and self.in_memory_catalog:
            matched = self.in_memory_catalog[:limit]

        return matched[:limit], len(matched)


catalog_search_engine = CatalogSearchEngine()
