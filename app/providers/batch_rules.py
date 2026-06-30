from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from app.models import (
    BatchLookupRequest,
    BatchLookupResponse,
    Confidence,
    SuggestedExternalLookup,
)


@dataclass(frozen=True)
class BatchRule:
    brand_key: str
    description: str
    parser: Callable[[str], Optional[date]]
    shelf_life_months: int = 36


class BatchRuleProvider:
    def __init__(self) -> None:
        self.rules: dict[str, BatchRule] = {}

    def lookup(self, request: BatchLookupRequest) -> BatchLookupResponse:
        brand_key = request.brand.strip().lower()
        rule = self.rules.get(brand_key)
        if not rule:
            return BatchLookupResponse(
                result="no_result",
                source="unsupported",
                sourceDescription=(
                    "No reliable brand-specific batch-code rule is configured."
                ),
                message="Use manual manufacture or expiry date entry in the app.",
                suggestedExternalLookup=_checkfresh_lookup(brand_key),
            )

        manufacture_date = rule.parser(request.batchCode.strip().upper())
        if manufacture_date is None:
            return BatchLookupResponse(
                result="no_result",
                source="localRule",
                sourceDescription=rule.description,
                message="The batch code did not match this brand rule.",
                suggestedExternalLookup=_checkfresh_lookup(brand_key),
            )

        expiry_date = _add_months(manufacture_date, rule.shelf_life_months)
        return BatchLookupResponse(
            result="found",
            manufactureDate=manufacture_date.isoformat(),
            expiryDate=expiry_date.isoformat(),
            confidence=Confidence.medium,
            source="localRule",
            sourceDescription=rule.description,
        )


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    if month in {4, 6, 9, 11}:
        return 30
    return 31


_CHECKFRESH_BRAND_PATHS = {
    "tatcha": "tatcha.html",
}


def _checkfresh_lookup(brand_key: str) -> SuggestedExternalLookup:
    brand_path = _CHECKFRESH_BRAND_PATHS.get(brand_key)
    url = (
        f"https://www.checkfresh.com/{brand_path}"
        if brand_path
        else "https://www.checkfresh.com/"
    )
    return SuggestedExternalLookup(
        name="CheckFresh",
        url=url,
        note=(
            "External informational lookup. Verify the result before saving dates."
        ),
    )
