from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse


MIN_IMAGE_WIDTH = 320
MIN_IMAGE_HEIGHT = 180


def strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_article_html(url: str, html: str) -> dict:
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    title = strip_html(title_match.group(1)) if title_match else ""
    meta_description = ""
    meta_match = re.search(
        r'(?is)<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
        html,
    )
    if meta_match:
        meta_description = unescape(meta_match.group(1)).strip()
    paragraphs = [strip_html(match) for match in re.findall(r"(?is)<p[^>]*>(.*?)</p>", html)]
    text = "\n".join(paragraph for paragraph in paragraphs if len(paragraph) > 20)
    if not text:
        text = strip_html(html)
    parsed = urlparse(url)
    return {
        "url": url,
        "title": title or parsed.netloc or "Untitled article",
        "text": text,
        "published_at": "",
        "author": "",
        "site_name": parsed.netloc,
        "language": "",
        "description": meta_description,
        "links": sorted(set(re.findall(r'(?is)<a\s+[^>]*href=["\']([^"\']+)["\']', html))),
        "primary_source_candidate": "",
    }


def extract_article_images(url: str, html: str) -> list[dict]:
    images: list[dict] = []
    for index, match in enumerate(re.finditer(r"(?is)<img\s+([^>]+)>", html), start=1):
        attrs = match.group(1)
        src_match = re.search(r'src=["\']([^"\']+)["\']', attrs)
        if not src_match:
            continue
        width = _int_attr(attrs, "width")
        height = _int_attr(attrs, "height")
        if width and height and (width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT):
            continue
        src = src_match.group(1)
        lowered = src.lower()
        if any(token in lowered for token in ("logo", "avatar", "icon", "banner", "sprite")):
            continue
        images.append(
            {
                "asset_id": f"article_image_{index:03d}",
                "source_url": src,
                "source_page": url,
                "provider": "article",
                "author": "",
                "caption": "",
                "license": "unknown",
                "credit_required": False,
                "rights_status": "reference_only",
                "allowed_for_render": False,
                "width": width,
                "height": height,
            }
        )
    return images


def _int_attr(attrs: str, name: str) -> int | None:
    match = re.search(rf'{name}=["\']?(\d+)', attrs, re.IGNORECASE)
    return int(match.group(1)) if match else None

