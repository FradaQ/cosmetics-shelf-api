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

Returns ranked official candidates. The default lookup path now returns only verified `officialWebsite` candidates; community or third-party catalog results are not returned.

```json
{
  "query": "Lancome Genifique serum",
  "brand": "Lancome",
  "barcode": "",
  "locale": "en-US",
  "preferredLanguage": "en",
  "officialProductPageURL": "",
  "officialImageURL": "",
  "officialName": "",
  "allowRetailerFallback": false,
  "preferredRetailers": []
}
```

If the iOS app already has a user-maintained official product URL or official image URL, send them in `officialProductPageURL` and `officialImageURL`. The API accepts the candidate only when the product page domain matches the known official brand-domain list. If the domain is not verified, it is filtered out of the default product lookup response.

For brands whose official sites block server-side lookup, the client can opt into authorized retailer fallback:

```json
{
  "query": "Lancome Genifique serum",
  "brand": "Lancome",
  "allowRetailerFallback": true,
  "preferredRetailers": ["sephora"]
}
```

Retailer fallback candidates use `source: "authorizedRetailer"`, not `officialWebsite`. The service returns them only when no verified official candidate is available.

### `POST /v1/batch-lookup`

Returns a batch-code result only when a reliable brand-specific local rule exists. Unsupported brands return `result: "no_result"` so the iOS app can show manual entry.

```json
{
  "brand": "Lancome",
  "batchCode": "40X600",
  "category": "skincare"
}
```

Unsupported brands include an external informational lookup suggestion:

```json
{
  "result": "no_result",
  "manufactureDate": null,
  "expiryDate": null,
  "confidence": null,
  "source": "unsupported",
  "sourceDescription": "No reliable brand-specific batch-code rule is configured.",
  "message": "Use manual manufacture or expiry date entry in the app.",
  "suggestedExternalLookup": {
    "name": "CheckFresh",
    "url": "https://www.checkfresh.com/",
    "note": "External informational lookup. Verify the result before saving dates."
  }
}
```

The service does not scrape CheckFresh or treat it as an official API. The app can open the external lookup as a user-assisted reference, then save dates only after user confirmation.

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

- `OfficialSearchProvider`: uses user-supplied official product URLs/images immediately, verifies known official brand domains, and can query lightweight official-site product suggestion endpoints for known brands.
- `SephoraRetailerProvider`: optional authorized-retailer fallback. It is only used when `allowRetailerFallback` is true and official lookup has no verified result.
- `OpenBeautyFactsProvider`: available in the codebase for future fallback experiments, but it is not part of the default `/v1/product-lookup` provider chain because product lookup currently returns official information and official images only.
- `BatchRuleProvider`: conservative rule engine skeleton. It returns no result unless a trusted brand-specific parser is configured.
- `RankingService`: de-duplicates official candidates, scores source/name/brand/barcode/page/image signals, and assigns confidence.

## Official Brand Coverage

Current official-domain coverage:

| Brand | Domains | Automatic lookup |
| --- | --- | --- |
| Lancome / Lancôme | `lancome-usa.com`, `lancome.com` | Manual official URL/image only. The site currently returns a browser challenge to server-side lookup requests. |
| Estée Lauder | `esteelauder.com` | Manual official URL/image only. |
| Clinique | `clinique.com` | Manual official URL/image only. |
| Kiehl's | `kiehls.com` | Manual official URL/image only. |
| The Ordinary | `theordinary.com` | Manual official URL/image only. |
| CeraVe | `cerave.com` | Manual official URL/image only. |
| La Mer | `cremedelamer.com`, `lamer.com` | Manual official URL/image only. |
| Tatcha | `tatcha.com` | Automatic official product lookup via site product suggestions. |
| Mediheal | `mediheal.com`, `medihealus.com`, `mediheal.co.kr` | Automatic official product lookup on `mediheal.com`; Korean domain is accepted for official URL verification. |
| Whipped | `whipped.co.kr` | Manual official URL/image only. |

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
- Treat batch-code rules and external lookup results as estimates unless the source is actually official.

## Tests

```bash
pytest
```

## Example Requests

```bash
BASE_URL=http://127.0.0.1:8000 ./examples/curl.sh
```
