from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Optional

import requests

from .models import PromoOffer


def _first_text(item: ET.Element, names: list[str]) -> str:
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def _parse_published(item: ET.Element) -> Optional[str]:
    raw = _first_text(item, ["pubDate", "published", "updated"])
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).isoformat()
    except (TypeError, ValueError):
        return raw


def fetch_promos(feeds: list[str], max_items: int) -> list[PromoOffer]:
    promos: list[PromoOffer] = []
    if max_items <= 0:
        return promos

    for feed_url in feeds:
        try:
            response = requests.get(feed_url, timeout=20)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception as exc:
            print(f"Advertencia promo: no se pudo leer feed {feed_url}: {exc}")
            continue

        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")
        for item in items:
            title = _first_text(item, ["title"])
            link = _first_text(item, ["link"])
            if not title or not link:
                continue
            promos.append(
                PromoOffer(
                    title=title,
                    link=link,
                    source=feed_url,
                    published_at=_parse_published(item),
                )
            )
            if len(promos) >= max_items:
                return promos

    return promos
