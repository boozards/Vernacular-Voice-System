import httpx
import asyncio
import random
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_catalog")

CATALOG_SERVICE_URL = "http://localhost:8005"

BRANDS = {
    "shoes": ["Nike", "Adidas", "Puma", "Bata", "Woodland", "Campus", "Sparx"],
    "ethnic": ["FabIndia", "Biba", "Manyavar", "W for Woman", "Aurelia", "Sabyasachi"],
    "electronics": ["boAt", "Noise", "Realme", "Xiaomi", "OnePlus", "JBL", "Samsung"],
    "groceries": ["Tata Tea", "Brooke Bond", "Fortune", "Amul", "Organic India", "Catch"],
    "kitchenware": ["Prestige", "Hawkins", "Milton", "Pigeon", "Wonderchef"]
}

CATEGORIES = [
    ("shoes", ["running", "sports", "casual", "sneakers"]),
    ("ethnic", ["saree", "kurti", "lehenga", "ethnic_wear"]),
    ("electronics", ["earphones", "smartwatch", "powerbank", "accessories"]),
    ("groceries", ["tea", "spices", "dry_fruits", "staples"]),
    ("kitchenware", ["cooker", "bottle", "pan", "kitchen"])
]

COLOR_LIST = ["black", "white", "blue", "red", "green", "pink", "maroon", "yellow", "grey"]
SIZE_LIST = {
    "shoes": ["6", "7", "8", "9", "10", "11"],
    "ethnic": ["S", "M", "L", "XL", "XXL", "Free Size"],
    "electronics": ["One Size"],
    "groceries": ["250g", "500g", "1kg", "2kg"],
    "kitchenware": ["1L", "2L", "3L", "5L"]
}

TITLE_TEMPLATES = {
    "shoes": [
        ("{brand} Revolution {num} Running Shoes", "{brand} रिवॉल्यूशन {num} स्पोर्ट्स जूते"),
        ("{brand} Speedstar {num} Breathable Sneakers", "{brand} स्पीडस्टार {num} रनिंग शूज़"),
        ("{brand} Comfort Walk Slip-on Shoes", "{brand} कम्फर्ट वॉक वॉकिंग शूज़"),
        ("{brand} Waterproof Trail Runner {num}", "{brand} वॉटरप्रूफ रनिंग शूज़"),
    ],
    "ethnic": [
        ("{brand} Kanjivaram Soft Silk Saree", "{brand} कांजीवरम सॉफ्ट सिल्क साड़ी"),
        ("{brand} Printed Cotton Straight Kurti", "{brand} कॉटन प्रिंटेड कुर्ती"),
        ("{brand} Traditional Designer Lehenga Choli", "{brand} डिज़ाइनर लहंगा चोली"),
        ("{brand} Bandhani Silk Dupatta Saree", "{brand} बांधनी सिल्क साड़ी"),
    ],
    "electronics": [
        ("{brand} Wireless Bluetooth Neckband Earphones", "{brand} वायरलेस ब्लूटूथ नेकबैंड"),
        ("{brand} Smart Watch with SpO2 & Heart Rate", "{brand} कॉलिंग स्मार्टवॉच"),
        ("{brand} Fast Charging Power Bank 10000mAh", "{brand} फास्ट चार्जिंग पावर बैंक"),
        ("{brand} Heavy Bass Earbuds with ANC", "{brand} नॉइज़ कैंसिलेशन इयरबड्स"),
    ],
    "groceries": [
        ("{brand} Premium Darjeeling Long Leaf Tea", "{brand} प्रीमियम दार्जिलिंग चाय patti"),
        ("{brand} Pure Cold Pressed Mustard Oil", "{brand} शुद्ध सरसों का तेल"),
        ("{brand} Organic Whole Cashew Nuts 500g", "{brand} ऑर्गेनिक काजू 500 ग्राम"),
        ("{brand} Royal Basmati Rice 5kg Pack", "{brand} रॉयल बासमती चावल"),
    ],
    "kitchenware": [
        ("{brand} Outer Lid Pressure Cooker 3 Litre", "{brand} 3 लीटर प्रेशर कुकर"),
        ("{brand} Insulated Stainless Steel Water Bottle", "{brand} वाटर बॉटल 1 लीटर"),
        ("{brand} Non-Stick Induction Base Frying Pan", "{brand} नॉन-स्टिक फ्राइंग पैन"),
        ("{brand} Stainless Steel Container Set 4 Pcs", "{brand} स्टील डिब्बा सेट"),
    ]
}


def generate_500_products() -> List[Dict[str, Any]]:
    products = []
    prod_counter = 1

    for i in range(500):
        cat_key, sub_cats = random.choice(CATEGORIES)
        brand = random.choice(BRANDS[cat_key])
        num = random.randint(1, 9)

        title_tpl_en, title_tpl_hi = random.choice(TITLE_TEMPLATES[cat_key])
        title_en = title_tpl_en.format(brand=brand, num=num)
        title_hi = title_tpl_hi.format(brand=brand, num=num)

        mrp = float(random.choice([499, 799, 999, 1499, 1999, 2499, 2999, 3999, 4999]))
        discount_pct = random.choice([10, 15, 20, 25, 30, 40, 50, 60])
        price = round(mrp * (1 - (discount_pct / 100)), 2)

        sizes = random.sample(SIZE_LIST[cat_key], min(3, len(SIZE_LIST[cat_key])))
        colors = random.sample(COLOR_LIST, min(2, len(COLOR_LIST)))
        rating = round(random.uniform(3.8, 4.9), 1)
        review_cnt = random.randint(50, 8500)

        product_id = f"SKU-{cat_key[:3].upper()}-{brand[:2].upper()}-{prod_counter:04d}"
        prod_counter += 1

        p = {
            "product_id": product_id,
            "title": {"en": title_en, "hi": title_hi},
            "description": {
                "en": f"High quality {title_en} designed for Indian consumers with premium material and durability.",
                "hi": f"भारतीय ग्राहकों के लिए टिकाऊ और आरामदायक {title_hi}।"
            },
            "category": [cat_key] + sub_cats,
            "brand": brand,
            "price": price,
            "mrp": mrp,
            "discount_pct": discount_pct,
            "sizes": sizes,
            "colors": colors,
            "rating": rating,
            "review_count": review_cnt,
            "in_stock": True,
            "image_url": f"https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80"
        }
        products.append(p)

    return products


async def seed_catalog():
    logger.info("Generating 500+ realistic products for Indian E-Commerce catalog...")
    products = generate_500_products()

    logger.info(f"Generated {len(products)} products. Indexing into Catalog Service ({CATALOG_SERVICE_URL})...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        indexed_count = 0
        for p in products:
            try:
                resp = await client.post(f"{CATALOG_SERVICE_URL}/index-product", json=p)
                if resp.status_code == 200:
                    indexed_count += 1
            except Exception as e:
                pass

    logger.info(f"Successfully seeded {indexed_count} products into Catalog Service!")


if __name__ == "__main__":
    asyncio.run(seed_catalog())
