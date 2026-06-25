import httpx

from app.models import ProductLookupRequest, ProductLookupResponse, ProductSource
from app.providers.base import ProductLookupProvider
from app.services.ranking import RankingService


class ProductLookupService:
    def __init__(
        self,
        providers: list[ProductLookupProvider],
        ranking_service: RankingService,
    ) -> None:
        self.providers = providers
        self.ranking_service = ranking_service

    async def lookup(self, request: ProductLookupRequest) -> ProductLookupResponse:
        all_candidates = []
        for provider in self.providers:
            try:
                all_candidates.extend(await provider.lookup(request))
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                raise ProductLookupProviderError(str(exc)) from exc
        official_candidates = [
            candidate
            for candidate in all_candidates
            if candidate.source == ProductSource.official_website
        ]
        if official_candidates or not request.allowRetailerFallback:
            return ProductLookupResponse(
                candidates=self.ranking_service.rank(official_candidates, request)
            )

        retailer_candidates = [
            candidate
            for candidate in all_candidates
            if candidate.source == ProductSource.authorized_retailer
        ]
        return ProductLookupResponse(
            candidates=self.ranking_service.rank(retailer_candidates, request)
        )


class ProductLookupProviderError(RuntimeError):
    pass
