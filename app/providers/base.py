from typing import Protocol

from app.models import (
    BatchLookupRequest,
    BatchLookupResponse,
    ProductLookupRequest,
    ProductCandidate,
)


class ProductLookupProvider(Protocol):
    async def lookup(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        ...


class BatchLookupProvider(Protocol):
    def lookup(self, request: BatchLookupRequest) -> BatchLookupResponse:
        ...

