from app.config import Settings
from app.models import ProductLookupRequest
from app.providers.official_search import OfficialSearchProvider
from app.providers.page_metadata import parse_page_metadata


def test_parse_json_ld_product_before_open_graph() -> None:
    html = """
    <html>
      <head>
        <meta property="og:title" content="Fallback OG Title">
        <meta property="og:image" content="https://example.com/og.jpg">
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Advanced Genifique Face Serum",
            "brand": {"@type": "Brand", "name": "Lancome"},
            "image": "https://example.com/product.jpg",
            "url": "https://www.lancome-usa.com/product"
          }
        </script>
      </head>
      <body></body>
    </html>
    """

    metadata = parse_page_metadata(html)

    assert metadata.product_name == "Advanced Genifique Face Serum"
    assert metadata.brand == "Lancome"
    assert metadata.image_url == "https://example.com/product.jpg"
    assert metadata.canonical_url == "https://www.lancome-usa.com/product"


def test_official_provider_maps_page_to_candidate() -> None:
    provider = OfficialSearchProvider(Settings())
    request = ProductLookupRequest(
        query="Lancome Genifique serum",
        brand="Lancome",
        locale="en-US",
        preferredLanguage="en",
    )
    html = """
    <html>
      <head>
        <title>Advanced Genifique Face Serum</title>
        <meta property="og:image" content="https://example.com/product.jpg">
        <meta property="og:url" content="https://www.lancome-usa.com/product">
      </head>
    </html>
    """

    candidate = provider.candidate_from_page(
        "https://www.lancome-usa.com/product", html, request
    )

    assert candidate.source == "officialWebsite"
    assert candidate.brand == "Lancome"
    assert candidate.englishName == "Advanced Genifique Face Serum"
    assert "official domain" in candidate.matchReasons
    assert "name match" in candidate.matchReasons


def test_known_official_domain_mapping() -> None:
    provider = OfficialSearchProvider(Settings())

    assert "lancome-usa.com" in provider.preferred_domains_for_brand("Lancome")
    assert "cremedelamer.com" in provider.preferred_domains_for_brand("La Mer")
    assert "tatcha.com" in provider.preferred_domains_for_brand("Tatcha")
    assert "theordinary.com" in provider.preferred_domains_for_brand("The Ordinary")


async def test_official_provider_uses_user_supplied_known_official_product_page() -> None:
    provider = OfficialSearchProvider(Settings())
    request = ProductLookupRequest(
        query="The Concentrate",
        brand="La Mer",
        officialProductPageURL="https://www.cremedelamer.com/product/the-concentrate",
        officialImageURL="https://www.cremedelamer.com/media/the-concentrate.jpg",
        officialName="The Concentrate",
    )

    candidates = await provider.lookup(request)

    assert len(candidates) == 1
    assert candidates[0].source == "officialWebsite"
    assert candidates[0].confidence == "high"
    assert candidates[0].brand == "La Mer"
    assert candidates[0].englishName == "The Concentrate"
    assert "official domain" in candidates[0].matchReasons
    assert "user supplied official image" in candidates[0].matchReasons


async def test_official_provider_marks_user_supplied_unknown_domain_as_unverified() -> None:
    provider = OfficialSearchProvider(Settings())
    request = ProductLookupRequest(
        query="Mystery Serum",
        brand="Lancome",
        officialProductPageURL="https://example.com/mystery-serum",
        officialImageURL="https://example.com/mystery-serum.jpg",
    )

    candidates = await provider.lookup(request)

    assert len(candidates) == 1
    assert candidates[0].source == "userProvided"
    assert candidates[0].confidence == "medium"
    assert "official domain not verified" in candidates[0].matchReasons


async def test_official_provider_maps_shopify_suggest_products() -> None:
    provider = OfficialSearchProvider(Settings())

    async def fake_shopify_suggest(domain, search_query, request):
        assert domain == "tatcha.com"
        assert search_query == "cleanser"
        return [
            provider._candidate_from_shopify_product(
                domain,
                {
                    "title": "The Rice Wash",
                    "url": "/products/rice-wash-soft-cream-cleanser?_pos=1",
                    "featured_image": {
                        "url": "https://cdn.shopify.com/product.jpg",
                    },
                },
                request,
            )
        ]

    provider._lookup_shopify_suggest = fake_shopify_suggest
    request = ProductLookupRequest(query="tatcha cleanser", brand="Tatcha")

    candidates = await provider.lookup(request)

    assert len(candidates) == 1
    assert candidates[0].source == "officialWebsite"
    assert candidates[0].englishName == "The Rice Wash"
    assert str(candidates[0].imageURL) == "https://cdn.shopify.com/product.jpg"
    assert str(candidates[0].productPageURL) == (
        "https://tatcha.com/products/rice-wash-soft-cream-cleanser"
    )
    assert "official site search" in candidates[0].matchReasons
    assert "official image" in candidates[0].matchReasons
