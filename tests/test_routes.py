from fastapi.testclient import TestClient

from app.main import create_app
from app.models import (
    Confidence,
    ProductCandidate,
    ProductLookupRequest,
    ProductLookupResponse,
    ProductSource,
)
from app.routes import get_product_lookup_service


class FakeProductLookupService:
    async def lookup(self, request: ProductLookupRequest) -> ProductLookupResponse:
        return ProductLookupResponse(
            candidates=[
                ProductCandidate(
                    id="fake-id",
                    englishName="Advanced Genifique Face Serum",
                    brand=request.brand,
                    source=ProductSource.official_website,
                    confidence=Confidence.high,
                    matchReasons=["official domain", "brand match", "name match"],
                )
            ]
        )


def test_health() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"]


def test_product_lookup_endpoint_returns_candidates() -> None:
    app = create_app()
    app.dependency_overrides[get_product_lookup_service] = lambda: FakeProductLookupService()
    client = TestClient(app)

    response = client.post(
        "/v1/product-lookup",
        json={
            "query": "Lancome Genifique serum",
            "brand": "Lancome",
            "barcode": "",
            "locale": "en-US",
            "preferredLanguage": "en",
        },
    )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["source"] == "officialWebsite"
    assert response.json()["candidates"][0]["confidence"] == "high"


def test_product_lookup_requires_query_or_barcode() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/product-lookup",
        json={
            "query": "",
            "brand": "Lancome",
            "barcode": "",
            "locale": "en-US",
            "preferredLanguage": "en",
        },
    )

    assert response.status_code == 422


def test_batch_lookup_unsupported_endpoint() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/batch-lookup",
        json={
            "brand": "Lancome",
            "batchCode": "40X600",
            "category": "skincare",
        },
    )

    assert response.status_code == 200
    assert response.json()["result"] == "no_result"
    assert response.json()["source"] == "unsupported"

