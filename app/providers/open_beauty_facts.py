from typing import Any, Optional

import httpx

from app.config import Settings
from app.models import Confidence, ProductCandidate, ProductLookupRequest, ProductSource
from app.services.brand import brand_matches
from app.services.category import guess_category
from app.services.ids import stable_id


class OpenBeautyFactsProvider:
    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None) -> None:
        self.settings = settings
        self.client = client

    async def lookup(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        if request.barcode.strip():
            return await self._lookup_barcode(request)
        return await self._search(request)

    async def _search(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        params = {
            "search_terms": " ".join(
                part for part in [request.brand.strip(), request.query.strip()] if part
            ),
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "fields": (
                "code,product_name,product_name_en,brands,categories_tags,"
                "image_front_url,url,lang"
            ),
        }
        data = await self._get_json("/cgi/search.pl", params=params)
        return [self._candidate(product, request) for product in data.get("products", [])]

    async def _lookup_barcode(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        data = await self._get_json(f"/api/v2/product/{request.barcode.strip()}.json")
        product = data.get("product")
        if not product:
            return []
        return [self._candidate(product, request)]

    async def _get_json(
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        headers = {"User-Agent": self.settings.open_beauty_facts_user_agent}
        close_client = self.client is None
        client = self.client or httpx.AsyncClient(
            base_url=self.settings.open_beauty_facts_base_url,
            timeout=self.settings.request_timeout_seconds,
            headers=headers,
            follow_redirects=True,
        )
        try:
            last_error: Optional[Exception] = None
            for _ in range(2):
                try:
                    response = await client.get(path, params=params, headers=headers)
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
            if last_error:
                raise last_error
            return {}
        finally:
            if close_client:
                await client.aclose()

    def _candidate(
        self, product: dict[str, Any], request: ProductLookupRequest
    ) -> ProductCandidate:
        local_name = str(product.get("product_name") or "").strip()
        english_name = str(product.get("product_name_en") or local_name).strip()
        brand = _first_brand(str(product.get("brands") or ""))
        barcode = str(product.get("code") or "").strip()
        category_text = " ".join(product.get("categories_tags") or [])
        reasons = ["Open Beauty Facts result"]
        if request.brand and brand_matches(request.brand, brand):
            reasons.append("brand match")
        if request.query and _has_name_overlap(request.query, english_name or local_name):
            reasons.append("name match")
        if barcode and request.barcode and barcode == request.barcode:
            reasons.append("barcode match")
        return ProductCandidate(
            id=stable_id(ProductSource.open_beauty_facts.value, barcode, brand, english_name),
            localName=local_name,
            englishName=english_name,
            brand=brand,
            category=guess_category(category_text, english_name, local_name),
            imageURL=product.get("image_front_url") or None,
            productPageURL=product.get("url") or None,
            barcode=barcode,
            source=ProductSource.open_beauty_facts,
            confidence=Confidence.low,
            matchReasons=reasons,
        )


def _first_brand(brands: str) -> str:
    return brands.split(",")[0].strip() if brands else ""


def _has_name_overlap(query: str, candidate: str) -> bool:
    query_tokens = {token for token in query.lower().split() if len(token) > 2}
    candidate_tokens = {token for token in candidate.lower().split() if len(token) > 2}
    return bool(query_tokens & candidate_tokens)

