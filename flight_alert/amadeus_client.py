from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any, Optional

import requests
from .models import FlightOffer


class AmadeusClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://test.api.amadeus.com",
        timeout_seconds: int = 20,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

        self._access_token: Optional[str] = None
        self._token_expiration: Optional[datetime] = None

    def _token_valid(self) -> bool:
        if not self._access_token or not self._token_expiration:
            return False
        return datetime.utcnow() < self._token_expiration

    def _authenticate(self) -> str:
        if self._token_valid():
            return self._access_token or ""

        token_url = f"{self._base_url}/v1/security/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        response = requests.post(token_url, data=payload, timeout=self._timeout_seconds)
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data.get("access_token", "")
        expires_in = int(token_data.get("expires_in", 0))
        if not access_token or expires_in <= 0:
            raise RuntimeError("No se pudo obtener token valido de Amadeus.")

        self._access_token = access_token
        # Refresh a bit earlier to avoid edge expiration.
        self._token_expiration = datetime.utcnow() + timedelta(seconds=expires_in - 30)
        return self._access_token

    def search_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        currency: str,
        adults: int,
        max_results: int,
        nonstop: bool,
        max_price: float,
        allowed_airlines: Optional[set[str]] = None,
    ) -> list[FlightOffer]:
        token = self._authenticate()
        url = f"{self._base_url}/v2/shopping/flight-offers"
        params: dict[str, Any] = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "nonStop": str(nonstop).lower(),
            "currencyCode": currency,
            "max": max_results,
            "maxPrice": max(1, math.ceil(max_price)),
        }
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(
            url, params=params, headers=headers, timeout=self._timeout_seconds
        )
        response.raise_for_status()
        payload = response.json()

        offers: list[FlightOffer] = []
        for item in payload.get("data", []):
            parsed = self._parse_offer(origin=origin, destination=destination, offer=item)
            if parsed is None:
                continue
            if parsed.price > max_price:
                continue
            if allowed_airlines and not set(parsed.carriers).intersection(allowed_airlines):
                continue
            offers.append(parsed)

        return offers

    @staticmethod
    def _parse_offer(origin: str, destination: str, offer: dict[str, Any]) -> Optional[FlightOffer]:
        itineraries = offer.get("itineraries") or []
        if not itineraries:
            return None
        first_itinerary = itineraries[0]
        segments = first_itinerary.get("segments") or []
        if not segments:
            return None

        first_segment = segments[0]
        last_segment = segments[-1]
        departure_at = first_segment.get("departure", {}).get("at", "")
        arrival_at = last_segment.get("arrival", {}).get("at", "")
        if not departure_at:
            return None

        carriers: list[str] = []
        for segment in segments:
            carrier = segment.get("carrierCode")
            if carrier and carrier not in carriers:
                carriers.append(carrier)

        price_total = offer.get("price", {}).get("total")
        currency = offer.get("price", {}).get("currency", "")
        if price_total is None:
            return None

        try:
            price = float(price_total)
        except (TypeError, ValueError):
            return None

        return FlightOffer(
            origin=origin,
            destination=destination,
            departure_at=departure_at,
            arrival_at=arrival_at,
            price=price,
            currency=currency,
            carriers=tuple(carriers),
            stops=max(0, len(segments) - 1),
        )
