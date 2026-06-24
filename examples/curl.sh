#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

curl "$BASE_URL/health"

curl -X POST "$BASE_URL/v1/product-lookup" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Lancome Genifique serum",
    "brand": "Lancome",
    "barcode": "",
    "locale": "en-US",
    "preferredLanguage": "en"
  }'

curl -X POST "$BASE_URL/v1/batch-lookup" \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Lancome",
    "batchCode": "40X600",
    "category": "skincare"
  }'

