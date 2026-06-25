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


class RetailerOnlyProvider:
    async def lookup(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        return [
            ProductCandidate(
                id="retailer",
                englishName="Advanced Genifique Face Serum",
                brand="Lancome",
                imageURL="https://www.sephora.com/productimages/genifique.jpg",
                productPageURL="https://www.sephora.com/product/advanced-genifique-face-serum",
                source=ProductSource.authorized_retailer,
                confidence=Confidence.medium,
                matchReasons=[
                    "authorized retailer fallback",
                    "authorized retailer domain",
                    "brand match",
                    "name match",
                ],
            )
        ]


async def test_product_lookup_service_uses_retailer_fallback_when_official_empty() -> None:
    service = ProductLookupService(
        providers=[RetailerOnlyProvider()],
        ranking_service=RankingService(),
    )

    response = await service.lookup(
        ProductLookupRequest(
            query="genifique serum",
            brand="Lancome",
            allowRetailerFallback=True,
        )
    )

    assert [candidate.id for candidate in response.candidates] == ["retailer"]


async def test_product_lookup_service_omits_retailer_when_fallback_disabled() -> None:
    service = ProductLookupService(
        providers=[RetailerOnlyProvider()],
        ranking_service=RankingService(),
    )

    response = await service.lookup(
        ProductLookupRequest(query="genifique serum", brand="Lancome")
    )

    assert response.candidates == []
