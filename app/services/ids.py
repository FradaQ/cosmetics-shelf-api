import hashlib


def stable_id(*parts: str) -> str:
    clean_parts = [part.strip().lower() for part in parts if part and part.strip()]
    digest = hashlib.sha256("|".join(clean_parts).encode("utf-8")).hexdigest()
    return digest[:16]

