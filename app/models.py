from enum import Enum
from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class ProductSource(str, Enum):
    open_beauty_facts = "openBeautyFacts"
    official_website = "officialWebsite"
    authorized_retailer = "authorizedRetailer"
    user_provided = "userProvided"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ProductCategory(str, Enum):
    skincare = "skincare"
    makeup = "makeup"
    fragrance = "fragrance"
    hair_body = "hairBody"
    unknown = "unknown"


class HealthResponse(BaseModel):
    status: str
    version: str


class ProductLookupRequest(BaseModel):
    query: str = Field(default="", max_length=200)
    brand: str = Field(default="", max_length=100)
    barcode: str = Field(default="", max_length=64)
    locale: str = Field(default="en-US", min_length=2, max_length=16)
    preferredLanguage: str = Field(default="en", min_length=2, max_length=8)
    officialProductPageURL: Optional[AnyHttpUrl] = None
    officialImageURL: Optional[AnyHttpUrl] = None
    officialName: str = Field(default="", max_length=200)
    allowRetailerFallback: bool = False
    preferredRetailers: List[str] = Field(default_factory=list, max_length=5)
    retailerProductPageURL: Optional[AnyHttpUrl] = None
    retailerImageURL: Optional[AnyHttpUrl] = None
    retailerName: str = Field(default="", max_length=100)
    retailerProductName: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def query_or_barcode_required(self) -> "ProductLookupRequest":
        if (
            not self.query.strip()
            and not self.barcode.strip()
            and not self.officialProductPageURL
            and not self.officialImageURL
            and not self.retailerProductPageURL
            and not self.retailerImageURL
        ):
            raise ValueError(
                "Either query, barcode, officialProductPageURL, officialImageURL, retailerProductPageURL, or retailerImageURL is required."
            )
        return self


class ProductCandidate(BaseModel):
    id: str
    localName: str = ""
    englishName: str = ""
    brand: str = ""
    category: ProductCategory = ProductCategory.unknown
    imageURL: Optional[AnyHttpUrl] = None
    productPageURL: Optional[AnyHttpUrl] = None
    barcode: str = ""
    source: ProductSource
    confidence: Confidence
    matchReasons: List[str] = Field(default_factory=list)


class ProductLookupResponse(BaseModel):
    candidates: List[ProductCandidate]


class BatchLookupRequest(BaseModel):
    brand: str = Field(..., min_length=1, max_length=100)
    batchCode: str = Field(..., min_length=2, max_length=32)
    category: ProductCategory = ProductCategory.unknown


class BatchLookupResponse(BaseModel):
    result: str
    manufactureDate: Optional[str] = None
    expiryDate: Optional[str] = None
    confidence: Optional[Confidence] = None
    source: str
    sourceDescription: str
    message: Optional[str] = None
