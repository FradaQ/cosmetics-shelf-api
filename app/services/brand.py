import re
import unicodedata


def normalize_brand(value: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "", without_accents.lower())


def brand_matches(requested_brand: str, candidate_brand: str) -> bool:
    requested = normalize_brand(requested_brand)
    candidate = normalize_brand(candidate_brand)
    if not requested or not candidate:
        return False
    return requested == candidate or requested in candidate or candidate in requested

