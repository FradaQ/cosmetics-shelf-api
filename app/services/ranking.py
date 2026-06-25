from app.models import Confidence, ProductCandidate, ProductLookupRequest, ProductSource
from app.services.brand import brand_matches


class RankingService:
    def rank(
        self, candidates: list[ProductCandidate], request: ProductLookupRequest
    ) -> list[ProductCandidate]:
        deduped: dict[str, ProductCandidate] = {}
        for candidate in candidates:
            key = self._dedupe_key(candidate)
            current = deduped.get(key)
            if current is None or self._score(candidate, request) > self._score(current, request):
                deduped[key] = candidate

        candidates = list(deduped.values())
        brand_matched = self._brand_matched_candidates(candidates, request)
        if request.brand.strip():
            candidates = brand_matched

        ranked = sorted(
            candidates,
            key=lambda candidate: self._score(candidate, request),
            reverse=True,
        )
        for candidate in ranked:
            candidate.confidence = self._confidence(self._score(candidate, request))
        return ranked[:10]

    def _score(self, candidate: ProductCandidate, request: ProductLookupRequest) -> int:
        score = 0
        reasons = set(candidate.matchReasons)
        if candidate.source == ProductSource.official_website:
            score += 25
        elif candidate.source == ProductSource.authorized_retailer:
            score += 18
        elif candidate.source == ProductSource.open_beauty_facts:
            score += 15
        elif candidate.source == ProductSource.user_provided:
            score += 20
        if "official domain" in reasons:
            score += 30
        if "authorized retailer fallback" in reasons:
            score += 20
        if "authorized retailer domain" in reasons:
            score += 15
        if "user supplied product page" in reasons:
            score += 15
        if "user supplied official image" in reasons:
            score += 10
        if "barcode match" in reasons:
            score += 35
        if "brand match" in reasons:
            score += 20
        if "name match" in reasons:
            score += 20
        if candidate.imageURL:
            score += 5
        if candidate.productPageURL:
            score += 5
        if request.brand and candidate.brand:
            if brand_matches(request.brand, candidate.brand):
                score += 10
        return score

    def _brand_matched_candidates(
        self, candidates: list[ProductCandidate], request: ProductLookupRequest
    ) -> list[ProductCandidate]:
        requested_brand = request.brand.strip()
        if not requested_brand:
            return candidates
        return [
            candidate
            for candidate in candidates
            if candidate.brand and brand_matches(requested_brand, candidate.brand)
        ]

    def _confidence(self, score: int) -> Confidence:
        if score >= 75:
            return Confidence.high
        if score >= 45:
            return Confidence.medium
        return Confidence.low

    def _dedupe_key(self, candidate: ProductCandidate) -> str:
        if candidate.barcode:
            return f"barcode:{candidate.barcode}"
        if candidate.productPageURL:
            return f"url:{candidate.productPageURL}"
        return f"name:{candidate.brand.lower()}:{candidate.englishName.lower()}"
