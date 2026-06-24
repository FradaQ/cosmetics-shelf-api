import re
import unicodedata

from app.models import Confidence, ProductCandidate, ProductLookupRequest, ProductSource


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
        elif candidate.source == ProductSource.open_beauty_facts:
            score += 15
        if "official domain" in reasons:
            score += 30
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
            if _brand_matches(request.brand, candidate.brand):
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
            if candidate.brand and _brand_matches(requested_brand, candidate.brand)
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


def _brand_matches(requested_brand: str, candidate_brand: str) -> bool:
    requested = _normalize_brand(requested_brand)
    candidate = _normalize_brand(candidate_brand)
    if not requested or not candidate:
        return False
    return requested == candidate or requested in candidate or candidate in requested


def _normalize_brand(value: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "", without_accents.lower())
