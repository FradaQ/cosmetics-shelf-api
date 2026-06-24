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
    assert "theordinary.com" in provider.preferred_domains_for_brand("The Ordinary")

