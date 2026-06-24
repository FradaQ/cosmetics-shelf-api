from app.models import ProductCategory


_CATEGORY_KEYWORDS = {
    ProductCategory.skincare: (
        "serum",
        "cream",
        "cleanser",
        "toner",
        "moisturizer",
        "sunscreen",
        "spf",
        "essence",
        "mask",
        "lotion",
    ),
    ProductCategory.makeup: (
        "lipstick",
        "foundation",
        "mascara",
        "concealer",
        "blush",
        "powder",
        "palette",
        "eyeliner",
    ),
    ProductCategory.fragrance: (
        "parfum",
        "perfume",
        "eau de parfum",
        "eau de toilette",
        "fragrance",
        "cologne",
    ),
    ProductCategory.hair_body: (
        "shampoo",
        "conditioner",
        "body wash",
        "body lotion",
        "hair",
        "deodorant",
    ),
}


def guess_category(*values: str) -> ProductCategory:
    text = " ".join(value for value in values if value).lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return ProductCategory.unknown

