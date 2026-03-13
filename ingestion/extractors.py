"""
Content extraction utilities salvaged from the auto-discovery service.

Used by the seed_from_blogs management command to extract venue data
from blog HTML pages. Lightweight — uses readability-lxml and regex only.
"""

import json
import re
import logging
from typing import Optional, Dict
from urllib.parse import urljoin

log = logging.getLogger(__name__)


def extract_readable(html: str) -> Dict:
    """
    Extract readable content from HTML using readability-lxml.

    Returns: {title, text, publish_date, is_recent}
    """
    try:
        from readability import Document
        doc = Document(html)
        title = doc.title()
        content_html = doc.summary()

        # Strip HTML tags for plain text
        text = re.sub(r'<[^>]+>', ' ', content_html)
        text = re.sub(r'\s+', ' ', text).strip()

        return {"title": title, "text": text}
    except ImportError:
        log.warning("readability-lxml not installed, falling back to regex extraction")
        # Fallback: basic regex extraction
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return {"title": title, "text": text}
    except Exception as e:
        log.error(f"Content extraction failed: {e}")
        return {"title": "", "text": ""}


def extract_jsonld(html: str) -> Optional[Dict]:
    """
    Extract JSON-LD structured data (Restaurant/LocalBusiness) from HTML.

    Returns: {name, address, telephone, openingHours} or None
    """
    try:
        # Find all JSON-LD script blocks
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                data = json.loads(match.strip())
            except json.JSONDecodeError:
                continue

            # Handle arrays
            items = data if isinstance(data, list) else [data]

            for item in items:
                item_type = item.get('@type', '')
                if isinstance(item_type, list):
                    item_type = ' '.join(item_type)

                if any(t in item_type for t in ('Restaurant', 'LocalBusiness', 'FoodEstablishment')):
                    address = item.get('address', '')
                    if isinstance(address, dict):
                        address = ', '.join(filter(None, [
                            address.get('streetAddress', ''),
                            address.get('addressLocality', ''),
                            address.get('addressRegion', ''),
                        ]))

                    return {
                        "name": item.get('name', ''),
                        "address": address,
                        "telephone": item.get('telephone', ''),
                        "openingHours": item.get('openingHours', ''),
                    }
    except Exception as e:
        log.error(f"JSON-LD extraction failed: {e}")

    return None


def extract_maps_links(html: str) -> list:
    """Extract Google Maps links from HTML."""
    patterns = [
        r'https?://(?:www\.)?google\.com/maps[^\s"\'<>]+',
        r'https?://maps\.google\.com[^\s"\'<>]+',
        r'https?://maps\.app\.goo\.gl/[^\s"\'<>]+',
    ]
    links = []
    for pattern in patterns:
        links.extend(re.findall(pattern, html))
    return list(set(links))
