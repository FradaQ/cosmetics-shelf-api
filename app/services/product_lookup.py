import httpx

from app.models import ProductLookupRequest, ProductLookupResponse
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
        return ProductLookupResponse(
            candidates=self.ranking_service.rank(all_candidates, request)
        )


class ProductLookupProviderError(RuntimeError):
    pass

