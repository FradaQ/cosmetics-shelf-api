from app.models import (
    Confidence,
    ProductCandidate,
    ProductLookupRequest,
    ProductSource,
)
from app.services.product_lookup import ProductLookupService
from app.services.ranking import RankingService


class MixedProvider:
    async def lookup(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        return [
            ProductCandidate(
                id="official",
                englishName="The Rice Wash",
                brand="Tatcha",
                imageURL="https://cdn.shopify.com/product.jpg",
                productPageURL="https://tatcha.com/products/rice-wash-soft-cream-cleanser",
                source=ProductSource.official_website,
                confidence=Confidence.high,
                matchReasons=[
                    "official site search",
                    "official domain",
                    "brand match",
                    "name match",
                    "official image",
                ],
            ),
            ProductCandidate(
                id="unverified",
                englishName="The Rice Wash",
                brand="Tatcha",
                imageURL="https://example.com/product.jpg",
                productPageURL="https://example.com/product",
                source=ProductSource.user_provided,
                confidence=Confidence.medium,
                matchReasons=["official domain not verified"],
            ),
            ProductCandidate(
                id="open",
                englishName="The Rice Wash",
                brand="Tatcha",
                imageURL="https://images.openbeautyfacts.org/product.jpg",
                source=ProductSource.open_beauty_facts,
                confidence=Confidence.medium,
                matchReasons=["Open Beauty Facts result"],
            ),
        ]


async def test_product_lookup_service_returns_only_official_website_candidates() -> None:
    service = ProductLookupService(
        providers=[MixedProvider()],
        ranking_service=RankingService(),
    )

    response = await service.lookup(
        ProductLookupRequest(query="tatcha cleanser", brand="Tatcha")
    )

    assert [candidate.id for candidate in response.candidates] == ["official"]

