from __future__ import annotations

import time
from typing import Any, Optional

import requests
from urllib.parse import urlencode

from .models import FlightOffer


class SerpApiError(RuntimeError):
    """Base exception for SerpAPI failures."""


class SerpApiAuthError(SerpApiError):
    """Raised when SerpAPI credentials are invalid or unauthorized."""


class SerpApiQuotaError(SerpApiError):
    """Raised when SerpAPI usage quota is exhausted or heavily rate limited."""


def _response_error_detail(response: requests.Response) -> str:
    detail = response.text.strip()
    try:
        payload = response.json()
        detail = str(payload.get("error") or payload.get("message") or detail)
    except ValueError:
        pass
    return detail or f"HTTP {response.status_code}"


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
            error_text = str(payload["error"])
            lowered = error_text.lower()
            if "hasn't returned any results" in lowered:
                return []
            if "run out of searches" in lowered or "out of searches" in lowered:
                raise SerpApiQuotaError(
                    "SerpAPI reporta que la cuenta no tiene busquedas disponibles."
                )
            raise SerpApiError(f"SerpAPI error: {error_text}")

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
            try:
                response = requests.get(url, params=params, timeout=self._timeout_seconds)
            except requests.RequestException as exc:
                if attempt >= max_retries:
                    raise SerpApiError(
                        "Error de red consultando SerpAPI luego de varios reintentos."
                    ) from exc
                wait_seconds = min(
                    max_backoff_seconds,
                    backoff_base_seconds * (2**attempt),
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue

            # Treat "no results" as a valid empty response instead of an exception.
            if response.status_code == 200:
                payload = response.json()
                if payload.get("error"):
                    error_text = str(payload["error"])
                    lowered = error_text.lower()
                    if "hasn't returned any results" in lowered:
                        return response
                    if "run out of searches" in lowered or "out of searches" in lowered:
                        raise SerpApiQuotaError(
                            "SerpAPI reporta que la cuenta no tiene busquedas disponibles."
                        )
                    raise SerpApiError(f"SerpAPI error: {error_text}")
                return response

            detail = _response_error_detail(response)
            lowered_detail = detail.lower()

            if response.status_code in {401, 403}:
                raise SerpApiAuthError(
                    "SerpAPI devolvio Unauthorized/Forbidden (401/403). "
                    "Revisa SERPAPI_KEY en .env, que siga activa y con permisos. "
                    f"Detalle: {detail}"
                )

            if response.status_code == 429 and (
                "run out of searches" in lowered_detail or "out of searches" in lowered_detail
            ):
                raise SerpApiQuotaError(
                    "SerpAPI reporta que no quedan busquedas en la cuenta."
                )

            is_retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if not is_retryable or attempt >= max_retries:
                if response.status_code == 429:
                    raise SerpApiQuotaError(
                        "SerpAPI devolvio 429 (Too Many Requests) tras reintentos. "
                        "Baja volumen de consultas o divide rutas en bloques."
                    )
                raise SerpApiError(
                    f"SerpAPI devolvio HTTP {response.status_code}. Detalle: {detail}"
                )

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
