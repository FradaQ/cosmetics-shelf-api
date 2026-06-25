from typing import Any, Optional
from urllib.parse import quote, urlparse

import httpx

from app.config import Settings
from app.models import Confidence, ProductCandidate, ProductLookupRequest, ProductSource
from app.services.brand import brand_matches
from app.services.category import guess_category
from app.services.ids import stable_id


SEPHORA_DOMAINS = ("sephora.com", "www.sephora.com")


class SephoraRetailerProvider:
    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None) -> None:
        self.settings = settings
        self.client = client

    async def lookup(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        if not self._should_lookup(request):
            return []

        candidates = []
        user_supplied = self.candidate_from_user_supplied(request)
        if user_supplied:
            candidates.append(user_supplied)
        candidates.extend(await self._search(request))
        return candidates

    def candidate_from_user_supplied(
        self, request: ProductLookupRequest
    ) -> Optional[ProductCandidate]:
        if not request.retailerProductPageURL and not request.retailerImageURL:
            return None

        page_url = str(request.retailerProductPageURL) if request.retailerProductPageURL else ""
        image_url = str(request.retailerImageURL) if request.retailerImageURL else ""
        if page_url and not self._is_sephora_url(page_url):
            return None

        name = request.retailerProductName.strip() or request.query.strip()
        reasons = ["authorized retailer fallback"]
        if page_url:
            reasons.append("authorized retailer domain")
            reasons.append("user supplied retailer product page")
        if image_url:
            reasons.append("user supplied retailer image")
        if request.brand:
            reasons.append("brand match")
        if name:
            reasons.append("name match")

        return ProductCandidate(
            id=stable_id(ProductSource.authorized_retailer.value, page_url, image_url, name),
            localName="",
            englishName=name,
            brand=request.brand,
            category=guess_category(name, request.query),
            imageURL=image_url or None,
            productPageURL=page_url or None,
            barcode=request.barcode,
            source=ProductSource.authorized_retailer,
            confidence=Confidence.medium,
            matchReasons=reasons,
        )

    async def _search(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        search_query = " ".join(
            part for part in [request.brand.strip(), request.query.strip()] if part
        )
        if not search_query:
            return []

        url = f"https://www.sephora.com/api/catalog/search?keyword={quote(search_query)}"
        close_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.settings.open_beauty_facts_user_agent},
        )
        try:
            response = await client.get(url)
            if response.status_code in {401, 403, 429}:
                return []
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        finally:
            if close_client:
                await client.aclose()

        products = _extract_products(data)
        return [
            self._candidate_from_product(product, request)
            for product in products
            if isinstance(product, dict)
        ]

    def _candidate_from_product(
        self, product: dict[str, Any], request: ProductLookupRequest
    ) -> ProductCandidate:
        brand = str(product.get("brandName") or product.get("brand") or request.brand).strip()
        name = str(product.get("displayName") or product.get("productName") or "").strip()
        product_url = _absolute_sephora_url(
            str(product.get("targetUrl") or product.get("productUrl") or "")
        )
        image_url = _sephora_image_url(product)
        reasons = ["authorized retailer fallback", "authorized retailer domain"]
        if request.brand and brand_matches(request.brand, brand):
            reasons.append("brand match")
        if request.query and _has_overlap(request.query, name):
            reasons.append("name match")
        if image_url:
            reasons.append("retailer image")

        return ProductCandidate(
            id=stable_id(ProductSource.authorized_retailer.value, product_url, brand, name),
            localName="",
            englishName=name,
            brand=brand,
            category=guess_category(name, request.query),
            imageURL=image_url or None,
            productPageURL=product_url or None,
            barcode=request.barcode,
            source=ProductSource.authorized_retailer,
            confidence=Confidence.low,
            matchReasons=reasons,
        )

    def _should_lookup(self, request: ProductLookupRequest) -> bool:
        if not request.allowRetailerFallback:
            return False
        if not request.preferredRetailers:
            return True
        return any(retailer.strip().lower() == "sephora" for retailer in request.preferredRetailers)

    def _is_sephora_url(self, url: str) -> bool:
        domain = urlparse(url).netloc.removeprefix("www.")
        return domain == "sephora.com" or domain.endswith(".sephora.com")


def _extract_products(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("products", "productResults", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    nested = data.get("results")
    if isinstance(nested, dict):
        return _extract_products(nested)
    return []


def _absolute_sephora_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if not url.startswith("/"):
        url = f"/{url}"
    return f"https://www.sephora.com{url}"


def _sephora_image_url(product: dict[str, Any]) -> str:
    image = product.get("heroImage") or product.get("image") or product.get("imageUrl")
    if isinstance(image, dict):
        image = image.get("url") or image.get("imageUrl")
    return str(image or "").strip()


def _has_overlap(left: str, right: str) -> bool:
    left_tokens = {token for token in left.lower().split() if len(token) > 2}
    right_tokens = {token for token in right.lower().split() if len(token) > 2}
    return bool(left_tokens & right_tokens)

