from app.models import BatchLookupRequest, ProductCategory
from app.providers.batch_rules import BatchRuleProvider


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

