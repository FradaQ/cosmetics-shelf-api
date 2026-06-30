from datetime import date

from app.models import BatchLookupRequest, ProductCategory
from app.providers.batch_rules import BatchRule, BatchRuleProvider


def test_unsupported_batch_code_returns_no_result() -> None:
    provider = BatchRuleProvider()

    response = provider.lookup(
        BatchLookupRequest(
            brand="Lancome",
            batchCode="40X600",
            category=ProductCategory.skincare,
        )
    )

    assert response.result == "no_result"
    assert response.manufactureDate is None
    assert response.expiryDate is None
    assert response.source == "unsupported"
    assert "manual" in response.message.lower()
    assert response.suggestedExternalLookup is not None
    assert response.suggestedExternalLookup.name == "CheckFresh"
    assert str(response.suggestedExternalLookup.url) == "https://www.checkfresh.com/"


def test_unmatched_supported_rule_returns_external_lookup_suggestion() -> None:
    provider = BatchRuleProvider()
    provider.rules["example"] = BatchRule(
        brand_key="example",
        description="Test rule.",
        parser=lambda batch_code: date(2024, 1, 1) if batch_code == "A1" else None,
    )

    response = provider.lookup(
        BatchLookupRequest(
            brand="Example",
            batchCode="NOPE",
            category=ProductCategory.skincare,
        )
    )

    assert response.result == "no_result"
    assert response.source == "localRule"
    assert response.suggestedExternalLookup is not None
    assert response.suggestedExternalLookup.name == "CheckFresh"


def test_found_batch_rule_omits_external_lookup_suggestion() -> None:
    provider = BatchRuleProvider()
    provider.rules["example"] = BatchRule(
        brand_key="example",
        description="Test rule.",
        parser=lambda batch_code: date(2024, 1, 1),
    )

    response = provider.lookup(
        BatchLookupRequest(
            brand="Example",
            batchCode="A1",
            category=ProductCategory.skincare,
        )
    )

    assert response.result == "found"
    assert response.manufactureDate == "2024-01-01"
    assert response.expiryDate == "2027-01-01"
    assert response.suggestedExternalLookup is None
