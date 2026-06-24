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

