from __future__ import annotations

from typing import Any, Optional

import requests

from .models import FlightOffer


class SerpApiClient:
    def __init__(self, api_key: str, timeout_seconds: int = 30) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def search_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        currency: str,
        adults: int,
        nonstop: bool,
        max_price: float,
        max_results: int,
        gl: str,
        hl: str,
        deep_search: bool,
        allowed_airlines: Optional[set[str]] = None,
    ) -> list[FlightOffer]:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_flights",
            "api_key": self._api_key,
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "type": 2,  # one way
            "currency": currency,
            "adults": adults,
            "stops": 1 if nonstop else 0,
            "sort_by": 2,  # price
            "hl": hl,
            "gl": gl,
            "deep_search": str(deep_search).lower(),
        }
        if allowed_airlines:
            params["include_airlines"] = ",".join(sorted(allowed_airlines))
        if max_price > 0:
            params["max_price"] = int(round(max_price))

        response = requests.get(url, params=params, timeout=self._timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(f"SerpAPI error: {payload['error']}")

        raw_offers = (payload.get("best_flights") or []) + (payload.get("other_flights") or [])
        offers: list[FlightOffer] = []
        for item in raw_offers:
            parsed = self._parse_offer(
                origin=origin,
                destination=destination,
                raw=item,
                currency=currency,
            )
            if parsed is None:
                continue
            if parsed.price > max_price:
                continue
            if allowed_airlines and not set(parsed.carriers).intersection(allowed_airlines):
                continue
            offers.append(parsed)

        offers.sort(key=lambda offer: offer.price)
        return offers[:max_results]

    @staticmethod
    def _parse_offer(
        origin: str, destination: str, raw: dict[str, Any], currency: str
    ) -> Optional[FlightOffer]:
        segments = raw.get("flights") or []
        if not segments:
            return None

        first_segment = segments[0]
        last_segment = segments[-1]

        departure_at = first_segment.get("departure_airport", {}).get("time", "")
        arrival_at = last_segment.get("arrival_airport", {}).get("time", "")
        if not departure_at:
            return None

        price = raw.get("price")
        try:
            price_value = float(price)
        except (TypeError, ValueError):
            return None

        carriers: list[str] = []
        for segment in segments:
            airline_name = str(segment.get("airline", "")).strip()
            flight_number = str(segment.get("flight_number", "")).strip()
            code = flight_number.split(" ", 1)[0].upper() if flight_number else ""
            carrier = code if code else airline_name
            if carrier and carrier not in carriers:
                carriers.append(carrier)

        return FlightOffer(
            origin=origin,
            destination=destination,
            departure_at=departure_at,
            arrival_at=arrival_at,
            price=price_value,
            currency=currency,
            carriers=tuple(carriers),
            stops=max(0, len(segments) - 1),
        )
