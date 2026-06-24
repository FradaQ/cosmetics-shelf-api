import json
from html.parser import HTMLParser
from typing import Any, Optional


class PageMetadata:
    def __init__(
        self,
        title: str = "",
        image_url: str = "",
        canonical_url: str = "",
        brand: str = "",
        product_name: str = "",
    ) -> None:
        self.title = title
        self.image_url = image_url
        self.canonical_url = canonical_url
        self.brand = brand
        self.product_name = product_name


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.json_ld: list[dict[str, Any]] = []
        self._in_title = False
        self._in_json_ld = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attr = {name.lower(): value or "" for name, value in attrs}
        if tag == "title":
            self._in_title = True
            self._buffer = []
        elif tag == "meta":
            key = attr.get("property") or attr.get("name")
            content = attr.get("content", "")
            if key and content:
                self.meta[key.lower()] = content.strip()
        elif tag == "link":
            rel = attr.get("rel", "").lower()
            href = attr.get("href", "")
            if rel and href:
                self.links[rel] = href.strip()
        elif tag == "script" and attr.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_title or self._in_json_ld:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self.title = " ".join("".join(self._buffer).split())
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._parse_json_ld("".join(self._buffer))
            self._in_json_ld = False

    def _parse_json_ld(self, raw: str) -> None:
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            return
        nodes = parsed if isinstance(parsed, list) else [parsed]
        for node in nodes:
            if isinstance(node, dict):
                self.json_ld.append(node)


def parse_page_metadata(html: str) -> PageMetadata:
    parser = _MetadataParser()
    parser.feed(html)
    product = _find_product(parser.json_ld)
    product_name = str(product.get("name", "")).strip() if product else ""
    brand = _extract_brand(product) if product else ""
    image_url = _extract_image(product) if product else ""
    canonical_url = str(product.get("url", "")).strip() if product else ""

    title = (
        product_name
        or parser.meta.get("og:title", "")
        or parser.meta.get("twitter:title", "")
        or parser.title
    )
    image = (
        image_url
        or parser.meta.get("og:image", "")
        or parser.meta.get("twitter:image", "")
    )
    url = (
        canonical_url
        or parser.meta.get("og:url", "")
        or parser.links.get("canonical", "")
    )
    return PageMetadata(
        title=title,
        image_url=image,
        canonical_url=url,
        brand=brand,
        product_name=product_name,
    )


def _find_product(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    for node in nodes:
        nested = node.get("@graph")
        if isinstance(nested, list):
            found = _find_product([item for item in nested if isinstance(item, dict)])
            if found:
                return found
        node_type = node.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if any(str(item).lower() == "product" for item in types):
            return node
    return {}


def _extract_brand(product: dict[str, Any]) -> str:
    brand = product.get("brand")
    if isinstance(brand, dict):
        return str(brand.get("name", "")).strip()
    return str(brand or "").strip()


def _extract_image(product: dict[str, Any]) -> str:
    image = product.get("image")
    if isinstance(image, list) and image:
        return str(image[0]).strip()
    return str(image or "").strip()

