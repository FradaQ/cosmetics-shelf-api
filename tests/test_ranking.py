from app.models import (
    Confidence,
    ProductCandidate,
    ProductLookupRequest,
    ProductSource,
)
from app.services.ranking import RankingService


def test_ranking_prefers_official_strong_match() -> None:
    request = ProductLookupRequest(query="Lancome Genifique serum", brand="Lancome")
    open_candidate = ProductCandidate(
        id="open",
        englishName="Genifique Serum",
        brand="Lancome",
        source=ProductSource.open_beauty_facts,
        confidence=Confidence.low,
        matchReasons=["brand match", "name match"],
    )
    official_candidate = ProductCandidate(
        id="official",
        englishName="Advanced Genifique Face Serum",
        brand="Lancome",
        imageURL="https://example.com/image.jpg",
        productPageURL="https://www.lancome-usa.com/product",
        source=ProductSource.official_website,
        confidence=Confidence.low,
        matchReasons=["official domain", "brand match", "name match"],
    )

    ranked = RankingService().rank([open_candidate, official_candidate], request)

    assert ranked[0].id == "official"
    assert ranked[0].confidence == Confidence.high


def test_ranking_deduplicates_barcode() -> None:
    request = ProductLookupRequest(query="serum", brand="Lancome")
    weaker = ProductCandidate(
        id="weaker",
        englishName="Serum",
        brand="Lancome",
        barcode="123",
        source=ProductSource.open_beauty_facts,
        confidence=Confidence.low,
        matchReasons=["brand match"],
    )
    stronger = ProductCandidate(
        id="stronger",
        englishName="Serum",
        brand="Lancome",
        barcode="123",
        productPageURL="https://example.com/product",
        source=ProductSource.open_beauty_facts,
        confidence=Confidence.low,
        matchReasons=["brand match", "name match"],
    )

    ranked = RankingService().rank([weaker, stronger], request)

    assert len(ranked) == 1
    assert ranked[0].id == "stronger"


def test_ranking_filters_non_matching_brands_when_brand_is_requested() -> None:
    request = ProductLookupRequest(query="cleanser", brand="Lancome")
    lancome_candidate = ProductCandidate(
        id="lancome",
        englishName="Creme Radiance Cleanser",
        brand="Lancôme",
        source=ProductSource.open_beauty_facts,
        confidence=Confidence.low,
        matchReasons=["brand match", "name match"],
    )
    other_candidate = ProductCandidate(
        id="other",
        englishName="Gentle Cleanser",
        brand="Other Brand",
        source=ProductSource.open_beauty_facts,
        confidence=Confidence.low,
        matchReasons=["name match"],
    )

    ranked = RankingService().rank([other_candidate, lancome_candidate], request)

    assert [candidate.id for candidate in ranked] == ["lancome"]


def test_ranking_prefers_user_supplied_official_domain_over_open_beauty_facts() -> None:
    request = ProductLookupRequest(query="The Concentrate", brand="La Mer")
    open_candidate = ProductCandidate(
        id="open",
        englishName="Concentrate",
        brand="La Mer",
        imageURL="https://images.openbeautyfacts.org/product.jpg",
        source=ProductSource.open_beauty_facts,
        confidence=Confidence.low,
        matchReasons=["brand match", "name match"],
    )
    user_official_candidate = ProductCandidate(
        id="official-user",
        englishName="The Concentrate",
        brand="La Mer",
        imageURL="https://www.cremedelamer.com/media/product.jpg",
        productPageURL="https://www.cremedelamer.com/product/the-concentrate",
        source=ProductSource.official_website,
        confidence=Confidence.low,
        matchReasons=[
            "user supplied product page",
            "user supplied official image",
            "official domain",
            "brand match",
            "name match",
        ],
    )

    ranked = RankingService().rank([open_candidate, user_official_candidate], request)

    assert ranked[0].id == "official-user"
    assert ranked[0].confidence == Confidence.high
