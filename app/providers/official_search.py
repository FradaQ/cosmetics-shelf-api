from typing import Optional
from urllib.parse import quote, urljoin, urlparse

import httpx

from app.config import Settings
from app.models import Confidence, ProductCandidate, ProductLookupRequest, ProductSource
from app.providers.page_metadata import parse_page_metadata
from app.services.brand import brand_matches, normalize_brand
from app.services.category import guess_category
from app.services.ids import stable_id


OFFICIAL_BRAND_DOMAINS: dict[str, tuple[str, ...]] = {
    "lancome": ("lancome-usa.com", "lancome.com"),
    "lancôme": ("lancome-usa.com", "lancome.com"),
    "estee lauder": ("esteelauder.com",),
    "estée lauder": ("esteelauder.com",),
    "clinique": ("clinique.com",),
    "kiehls": ("kiehls.com",),
    "kiehl's": ("kiehls.com",),
    "the ordinary": ("theordinary.com",),
    "cerave": ("cerave.com",),
    "lamer": ("cremedelamer.com", "lamer.com"),
    "la mer": ("cremedelamer.com", "lamer.com"),
    "tatcha": ("tatcha.com",),
}


class OfficialSearchProvider:
    """Provider boundary for future official-site search integration.

    The first milestone keeps this provider non-networked unless a search
    backend is added. Page parsing is implemented and tested so search results
    can be safely mapped into candidates later.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def lookup(self, request: ProductLookupRequest) -> list[ProductCandidate]:
        candidates = []
        user_supplied = self.candidate_from_user_supplied(request)
        if user_supplied:
            candidates.append(user_supplied)
        candidates.extend(await self._lookup_known_official_sites(request))
        if not self.settings.official_search_enabled:
            return candidates
        return candidates

    def preferred_domains_for_brand(self, brand: str) -> tuple[str, ...]:
        normalized = normalize_brand(brand)
        if normalized in OFFICIAL_BRAND_DOMAINS:
            return OFFICIAL_BRAND_DOMAINS[normalized]
        return OFFICIAL_BRAND_DOMAINS.get(brand.strip().lower(), ())

    def candidate_from_user_supplied(
        self, request: ProductLookupRequest
    ) -> Optional[ProductCandidate]:
        if not request.officialProductPageURL and not request.officialImageURL:
            return None

        page_url = str(request.officialProductPageURL) if request.officialProductPageURL else ""
        image_url = str(request.officialImageURL) if request.officialImageURL else ""
        known_official_domain = self._is_known_official_domain(page_url, request.brand)
        source = (
            ProductSource.official_website
            if known_official_domain
            else ProductSource.user_provided
        )
        reasons = []
        if page_url:
            reasons.append("user supplied product page")
        if image_url:
            reasons.append("user supplied official image")
        if known_official_domain:
            reasons.append("official domain")
        elif page_url:
            reasons.append("official domain not verified")
        if request.brand:
            reasons.append("brand match")
        if request.query or request.officialName:
            reasons.append("name match")

        name = request.officialName.strip() or request.query.strip()
        return ProductCandidate(
            id=stable_id(source.value, page_url, image_url, request.brand, name),
            localName="",
            englishName=name,
            brand=request.brand,
            category=guess_category(name),
            imageURL=image_url or None,
            productPageURL=page_url or None,
            barcode=request.barcode,
            source=source,
            confidence=Confidence.high if known_official_domain else Confidence.medium,
            matchReasons=reasons,
        )

    async def _lookup_known_official_sites(
        self, request: ProductLookupRequest
    ) -> list[ProductCandidate]:
        domains = self.preferred_domains_for_brand(request.brand)
        if not domains:
            return []

        search_query = self._official_search_query(request)
        if not search_query:
            return []

        candidates: list[ProductCandidate] = []
        for domain in domains[:2]:
            candidates.extend(await self._lookup_shopify_suggest(domain, search_query, request))
        return candidates

    async def _lookup_shopify_suggest(
        self, domain: str, search_query: str, request: ProductLookupRequest
    ) -> list[ProductCandidate]:
        url = (
            f"https://{domain}/search/suggest.json"
            f"?q={quote(search_query)}&resources[type]=product&resources[limit]=5"
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": self.settings.open_beauty_facts_user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        products = (
            data.get("resources", {})
            .get("results", {})
            .get("products", [])
        )
        return [
            self._candidate_from_shopify_product(domain, product, request)
            for product in products
            if isinstance(product, dict)
        ]

    def _candidate_from_shopify_product(
        self, domain: str, product: dict, request: ProductLookupRequest
    ) -> ProductCandidate:
        title = str(product.get("title") or "").strip()
        product_url = urljoin(f"https://{domain}", str(product.get("url") or ""))
        product_url = product_url.split("?")[0]
        image_url = _shopify_image_url(product)
        reasons = ["official site search", "official domain"]
        if request.brand:
            reasons.append("brand match")
        if title and _has_overlap(self._official_search_query(request), title):
            reasons.append("name match")
        if image_url:
            reasons.append("official image")

        return ProductCandidate(
            id=stable_id(ProductSource.official_website.value, product_url, title),
            localName="",
            englishName=title,
            brand=request.brand,
            category=guess_category(title, self._official_search_query(request)),
            imageURL=image_url or None,
            productPageURL=product_url,
            barcode=request.barcode,
            source=ProductSource.official_website,
            confidence=Confidence.low,
            matchReasons=reasons,
        )

    def candidate_from_page(
        self, url: str, html: str, request: ProductLookupRequest
    ) -> ProductCandidate:
        metadata = parse_page_metadata(html)
        domain = urlparse(url).netloc.removeprefix("www.")
        preferred_domains = self.preferred_domains_for_brand(request.brand)
        reasons = ["structured metadata"] if metadata.product_name else ["page metadata"]
        if any(domain.endswith(official) for official in preferred_domains):
            reasons.append("official domain")
        if request.brand and brand_matches(request.brand, metadata.brand or request.brand):
            reasons.append("brand match")
        if request.query and _has_overlap(request.query, metadata.title):
            reasons.append("name match")

        name = metadata.product_name or metadata.title
        return ProductCandidate(
            id=stable_id(ProductSource.official_website.value, url, name),
            localName="",
            englishName=name,
            brand=metadata.brand or request.brand,
            category=guess_category(name, request.query),
            imageURL=metadata.image_url or None,
            productPageURL=metadata.canonical_url or url,
            barcode=request.barcode,
            source=ProductSource.official_website,
            confidence=Confidence.low,
            matchReasons=reasons,
        )

    def _is_known_official_domain(self, url: str, brand: str) -> bool:
        if not url or not brand:
            return False
        domain = urlparse(url).netloc.removeprefix("www.")
        return any(
            domain == official or domain.endswith(f".{official}")
            for official in self.preferred_domains_for_brand(brand)
        )

    def _official_search_query(self, request: ProductLookupRequest) -> str:
        query = request.officialName.strip() or request.query.strip()
        if request.brand:
            normalized_brand = normalize_brand(request.brand)
            query_tokens = [
                token
                for token in query.split()
                if normalize_brand(token) != normalized_brand
            ]
            query = " ".join(query_tokens).strip() or query
        return query


def _has_overlap(left: str, right: str) -> bool:
    left_tokens = {token for token in left.lower().split() if len(token) > 2}
    right_tokens = {token for token in right.lower().split() if len(token) > 2}
    return bool(left_tokens & right_tokens)


def _shopify_image_url(product: dict) -> str:
    featured_image = product.get("featured_image")
    if isinstance(featured_image, dict) and featured_image.get("url"):
        return str(featured_image.get("url")).strip()
    return str(product.get("image") or "").strip()
