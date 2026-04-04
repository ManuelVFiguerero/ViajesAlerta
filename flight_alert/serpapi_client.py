from __future__ import annotations

import time
from typing import Any, Optional

import requests
from urllib.parse import urlencode

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
        return_date: Optional[str],
        trip_type: int,
        currency: str,
        adults: int,
        nonstop: bool,
        max_price: float,
        max_results: int,
        gl: str,
        hl: str,
        deep_search: bool,
        throttle_seconds: float,
        max_retries: int,
        backoff_base_seconds: float,
        max_backoff_seconds: float,
        allowed_airlines: Optional[set[str]] = None,
    ) -> list[FlightOffer]:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_flights",
            "api_key": self._api_key,
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "type": trip_type,
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
        if trip_type == 1 and return_date:
            params["return_date"] = return_date
        public_link_params = {
            "f": "0",
            "hl": hl,
            "gl": gl,
            "curr": currency,
            "adults": adults,
            "stops": 1 if nonstop else 0,
            "sort": "price",
            "from": origin,
            "to": destination,
            "date": departure_date,
        }
        if trip_type == 1 and return_date:
            public_link_params["trip"] = "round"
            public_link_params["return"] = return_date
        else:
            public_link_params["trip"] = "oneway"
        search_url = (
            "https://www.google.com/travel/flights?"
            f"{urlencode(public_link_params)}"
        )

        response = self._request_with_retry(
            url=url,
            params=params,
            max_retries=max_retries,
            backoff_base_seconds=backoff_base_seconds,
            max_backoff_seconds=max_backoff_seconds,
        )
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)
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
                return_date=return_date,
                search_url=search_url,
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

    def _request_with_retry(
        self,
        url: str,
        params: dict[str, Any],
        max_retries: int,
        backoff_base_seconds: float,
        max_backoff_seconds: float,
    ) -> requests.Response:
        attempt = 0
        while True:
            response = requests.get(url, params=params, timeout=self._timeout_seconds)

            # Treat "no results" as a valid empty response instead of an exception.
            if response.status_code == 200:
                payload = response.json()
                if payload.get("error"):
                    error_text = str(payload["error"])
                    if "hasn't returned any results" in error_text:
                        return response
                    raise RuntimeError(f"SerpAPI error: {error_text}")
                return response

            is_retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if not is_retryable or attempt >= max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait_seconds = min(max_backoff_seconds, max(1.0, float(retry_after)))
            else:
                wait_seconds = min(
                    max_backoff_seconds,
                    backoff_base_seconds * (2**attempt),
                )

            time.sleep(wait_seconds)
            attempt += 1

    @staticmethod
    def _parse_offer(
        origin: str,
        destination: str,
        raw: dict[str, Any],
        currency: str,
        return_date: Optional[str],
        search_url: str,
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
            return_at=return_date,
            price=price_value,
            currency=currency,
            carriers=tuple(carriers),
            stops=max(0, len(segments) - 1),
            deep_link=search_url,
        )
