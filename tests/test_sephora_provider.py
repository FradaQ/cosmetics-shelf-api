import httpx

from app.config import Settings
from app.models import ProductLookupRequest
from app.providers.sephora import SephoraRetailerProvider


async def test_sephora_provider_ignores_requests_without_fallback_enabled() -> None:
    provider = SephoraRetailerProvider(Settings())

    candidates = await provider.lookup(
        ProductLookupRequest(query="genifique serum", brand="Lancome")
    )

    assert candidates == []


async def test_sephora_provider_accepts_user_supplied_sephora_url() -> None:
    provider = SephoraRetailerProvider(Settings())
    request = ProductLookupRequest(
        query="genifique serum",
        brand="Lancome",
        allowRetailerFallback=True,
        preferredRetailers=["sephora"],
        retailerProductPageURL="https://www.sephora.com/product/advanced-genifique-face-serum",
        retailerImageURL="https://www.sephora.com/productimages/sku/s123-main-zoom.jpg",
        retailerProductName="Advanced Genifique Face Serum",
    )

    candidates = await provider.lookup(request)

    assert len(candidates) == 1
    assert candidates[0].source == "authorizedRetailer"
    assert candidates[0].brand == "Lancome"
    assert candidates[0].confidence == "medium"
    assert "authorized retailer fallback" in candidates[0].matchReasons
    assert "authorized retailer domain" in candidates[0].matchReasons


async def test_sephora_provider_rejects_user_supplied_non_sephora_url() -> None:
    provider = SephoraRetailerProvider(Settings())
    request = ProductLookupRequest(
        query="genifique serum",
        brand="Lancome",
        allowRetailerFallback=True,
        retailerProductPageURL="https://example.com/product",
        retailerImageURL="https://example.com/product.jpg",
    )

    candidates = await provider.lookup(request)

    assert candidates == []


async def test_sephora_provider_maps_search_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "products": [
                    {
                        "brandName": "Lancôme",
                        "displayName": "Advanced Génifique Face Serum",
                        "targetUrl": "/product/advanced-genifique-face-serum",
                        "heroImage": {
                            "url": "https://www.sephora.com/productimages/genifique.jpg"
                        },
                    }
                ]
            },
        )
    )
    client = httpx.AsyncClient(transport=transport)
    provider = SephoraRetailerProvider(Settings(), client=client)

    candidates = await provider.lookup(
        ProductLookupRequest(
            query="genifique serum",
            brand="Lancome",
            allowRetailerFallback=True,
            preferredRetailers=["sephora"],
        )
    )

    await client.aclose()

    assert len(candidates) == 1
    assert candidates[0].source == "authorizedRetailer"
    assert candidates[0].brand == "Lancôme"
    assert str(candidates[0].productPageURL) == (
        "https://www.sephora.com/product/advanced-genifique-face-serum"
    )
    assert "brand match" in candidates[0].matchReasons


async def test_sephora_provider_returns_empty_when_access_denied() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(403, text="Access Denied"))
    client = httpx.AsyncClient(transport=transport)
    provider = SephoraRetailerProvider(Settings(), client=client)

    candidates = await provider.lookup(
        ProductLookupRequest(
            query="genifique serum",
            brand="Lancome",
            allowRetailerFallback=True,
        )
    )

    await client.aclose()

    assert candidates == []
