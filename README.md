# Cosmetics Shelf API

Lightweight backend API for the Cosmetics Shelf iPhone app. The service looks up product candidates from server-side providers and returns ranked, source-attributed results. It does not store a user's inventory.

## Stack

- Python 3.9+
- FastAPI
- Pydantic
- HTTPX
- Pytest

This keeps deployment simple on platforms such as Render, Fly.io, Railway, or a small container service.

## Endpoints

### `GET /health`

Returns service status and version.

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

### `POST /v1/product-lookup`

Returns ranked candidates. The first milestone uses Open Beauty Facts and a stubbed official-search provider boundary.

```json
{
  "query": "Lancome Genifique serum",
  "brand": "Lancome",
  "barcode": "",
  "locale": "en-US",
  "preferredLanguage": "en",
  "officialProductPageURL": "",
  "officialImageURL": "",
  "officialName": ""
}
```

If the iOS app already has a user-maintained official product URL or official image URL, send them in `officialProductPageURL` and `officialImageURL`. The API will rank verified official-domain candidates above Open Beauty Facts results. If the domain is not in the known official brand-domain list, the candidate is returned as `source: "userProvided"` with `official domain not verified` in `matchReasons`.

### `POST /v1/batch-lookup`

Returns a batch-code result only when a reliable brand-specific local rule exists. Unsupported brands return `result: "no_result"` so the iOS app can show manual entry.

```json
{
  "brand": "Lancome",
  "batchCode": "40X600",
  "category": "skincare"
}
```

## Local Setup

```bash
git clone https://github.com/FradaQ/cosmetics-shelf-api.git
cd cosmetics-shelf-api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the generated API explorer.

## Environment Variables

| Name | Default | Notes |
| --- | --- | --- |
| `APP_VERSION` | `0.1.0` | Returned from `/health`. |
| `REQUEST_TIMEOUT_SECONDS` | `5` | Provider HTTP timeout. |
| `OPEN_BEAUTY_FACTS_BASE_URL` | `https://world.openbeautyfacts.org` | Open Beauty Facts base URL. |
| `OPEN_BEAUTY_FACTS_USER_AGENT` | `CosmeticsShelfAPI/0.1.0 contact@example.com` | Set this to a real contact before production. |
| `OFFICIAL_SEARCH_ENABLED` | `false` | Placeholder switch for future official search integration. |
| `OFFICIAL_SEARCH_API_KEY` | empty | Keep provider keys server-side only. |

## Provider Architecture

- `OpenBeautyFactsProvider`: searches Open Beauty Facts by text or barcode.
- `OfficialSearchProvider`: uses user-supplied official product URLs/images immediately, verifies known official brand domains, and contains the future official-site search boundary.
- `BatchRuleProvider`: conservative rule engine skeleton. It returns no result unless a trusted brand-specific parser is configured.
- `RankingService`: de-duplicates candidates, scores source/name/brand/barcode/page/image signals, and assigns confidence.

## Metadata Parsing

Official product pages should be parsed in this order:

1. JSON-LD `Product` schema
2. Open Graph title/image/url
3. Twitter card title/image
4. HTML title fallback

The current parser is intentionally small and uses Python's standard `html.parser`.

## Production Notes

- Keep search-provider API keys on the server and never in the iOS app.
- Use a real contact in the Open Beauty Facts user agent.
- Respect robots.txt, site terms, and provider rate limits.
- Add caching before increasing lookup volume.
- Log provider failures without logging full user inventory. Requests should contain only the current lookup query.
- Treat batch-code rules as estimates unless the source is actually official.

## Tests

```bash
pytest
```

## Example Requests

```bash
BASE_URL=http://127.0.0.1:8000 ./examples/curl.sh
```
