from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from .config import AppConfig
from .models import FlightOffer
from .serpapi_client import SerpApiClient


def _iter_departure_dates(config: AppConfig) -> Iterable[date]:
    if config.fixed_departure_date_from and config.fixed_departure_date_to:
        start = config.fixed_departure_date_from
        end = config.fixed_departure_date_to
    else:
        start = date.today() + timedelta(days=config.start_in_days)
        end = start + timedelta(days=config.departure_window_days)

    current = start
    while current <= end:
        yield current
        current += timedelta(days=config.date_step_days)


def search_deals(config: AppConfig) -> list[FlightOffer]:
    client = SerpApiClient(api_key=config.serpapi_key)
    allowed_airlines = config.allowed_airlines_set()
    deals: list[FlightOffer] = []

    for origin, destination in config.routes:
        for departure_date in _iter_departure_dates(config):
            try:
                if config.trip_type == 1:
                    return_start = departure_date + timedelta(days=config.return_days_min)
                    return_end = departure_date + timedelta(days=config.return_days_max)
                    return_date = return_start
                    while return_date <= return_end:
                        offers = client.search_offers(
                            origin=origin,
                            destination=destination,
                            departure_date=departure_date.isoformat(),
                            return_date=return_date.isoformat(),
                            trip_type=config.trip_type,
                            currency=config.currency,
                            adults=config.adults,
                            nonstop=config.nonstop,
                            gl=config.gl,
                            hl=config.hl,
                            deep_search=config.deep_search,
                            max_results=config.max_results_per_date,
                            max_price=config.max_price,
                            allowed_airlines=allowed_airlines,
                        )
                        deals.extend(offers)
                        return_date += timedelta(days=config.return_days_step)
                else:
                    offers = client.search_offers(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date.isoformat(),
                        return_date=None,
                        trip_type=config.trip_type,
                        currency=config.currency,
                        adults=config.adults,
                        nonstop=config.nonstop,
                        gl=config.gl,
                        hl=config.hl,
                        deep_search=config.deep_search,
                        max_results=config.max_results_per_date,
                        max_price=config.max_price,
                        allowed_airlines=allowed_airlines,
                    )
                    deals.extend(offers)
            except Exception as exc:
                print(f"Advertencia: se omite {origin}->{destination} ({departure_date.isoformat()}): {exc}")
                continue

    # Keep the best deal per exact route+date+carriers tuple.
    unique: dict[tuple[str, str, str, str, tuple[str, ...]], FlightOffer] = {}
    for deal in deals:
        key = deal.dedupe_key()
        existing = unique.get(key)
        if existing is None or deal.price < existing.price:
            unique[key] = deal

    sorted_deals = sorted(unique.values(), key=lambda d: (d.price, d.departure_at))
    return sorted_deals


def render_deals_message(deals: list[FlightOffer], config: AppConfig) -> str:
    trip_desc = "ida y vuelta" if config.trip_type == 1 else "solo ida"
    lines = [
        f"Ofertas ({trip_desc}) por debajo de {config.max_price:.2f} {config.currency}:",
        "",
    ]
    for deal in deals:
        airlines = ",".join(deal.carriers) if deal.carriers else "N/A"
        date_block = deal.departure_at[:10]
        if deal.return_at:
            date_block = f"{deal.departure_at[:10]} -> {deal.return_at[:10]}"
        lines.append(
            f"- {deal.origin}->{deal.destination} | "
            f"{date_block} | "
            f"{deal.price:.2f} {deal.currency} | "
            f"Aerolineas: {airlines} | Escalas: {deal.stops}"
        )
    return "\n".join(lines)
