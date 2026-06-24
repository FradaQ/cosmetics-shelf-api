from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.models import (
    BatchLookupRequest,
    BatchLookupResponse,
    HealthResponse,
    ProductLookupRequest,
    ProductLookupResponse,
)
from app.providers import BatchRuleProvider, OfficialSearchProvider, OpenBeautyFactsProvider
from app.services.product_lookup import ProductLookupProviderError, ProductLookupService
from app.services.ranking import RankingService


router = APIRouter()


def get_product_lookup_service(
    settings: Settings = Depends(get_settings),
) -> ProductLookupService:
    return ProductLookupService(
        providers=[
            OpenBeautyFactsProvider(settings=settings),
            OfficialSearchProvider(settings=settings),
        ],
        ranking_service=RankingService(),
    )


def get_batch_rule_provider() -> BatchRuleProvider:
    return BatchRuleProvider()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)


@router.post("/v1/product-lookup", response_model=ProductLookupResponse)
async def product_lookup(
    request: ProductLookupRequest,
    service: ProductLookupService = Depends(get_product_lookup_service),
) -> ProductLookupResponse:
    try:
        return await service.lookup(request)
    except ProductLookupProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "provider_error",
                "message": "A product lookup provider failed or timed out.",
            },
        ) from exc


@router.post("/v1/batch-lookup", response_model=BatchLookupResponse)
def batch_lookup(
    request: BatchLookupRequest,
    provider: BatchRuleProvider = Depends(get_batch_rule_provider),
) -> BatchLookupResponse:
    return provider.lookup(request)

