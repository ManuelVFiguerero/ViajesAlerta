from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from .amadeus_client import AmadeusClient
from .config import AppConfig
from .models import FlightDeal


def _iter_departure_dates(config: AppConfig) -> Iterable[date]:
    start = date.today() + timedelta(days=config.start_in_days)
    end = start + timedelta(days=config.departure_window_days)

    current = start
    while current <= end:
        yield current
        current += timedelta(days=config.date_step_days)


def search_deals(config: AppConfig) -> list[FlightDeal]:
    client = AmadeusClient(
        client_id=config.amadeus_client_id,
        client_secret=config.amadeus_client_secret,
    )
    allowed_airlines = config.allowed_airlines_set()
    deals: list[FlightDeal] = []

    for origin, destination in config.routes:
        for departure_date in _iter_departure_dates(config):
            offers = client.search_offers(
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                currency=config.currency,
                adults=config.adults,
                nonstop=config.nonstop,
                max_results=config.max_results_per_date,
                max_price=config.max_price,
                allowed_airlines=allowed_airlines,
            )
            for offer in offers:
                deals.append(
                    FlightDeal(
                        origin=offer.origin,
                        destination=offer.destination,
                        departure_at=offer.departure_at,
                        arrival_at=offer.arrival_at,
                        price=offer.price,
                        currency=offer.currency,
                        carriers=offer.carriers,
                        stops=offer.stops,
                    )
                )

    # Keep the best deal per exact route+date+carriers tuple.
    unique: dict[tuple[str, str, str, tuple[str, ...]], FlightDeal] = {}
    for deal in deals:
        key = deal.dedupe_key()
        existing = unique.get(key)
        if existing is None or deal.price < existing.price:
            unique[key] = deal

    sorted_deals = sorted(unique.values(), key=lambda d: (d.price, d.departure_at))
    return sorted_deals


def render_deals_message(deals: list[FlightDeal], config: AppConfig) -> str:
    lines = [
        f"Ofertas encontradas por debajo de {config.max_price:.2f} {config.currency}:",
        "",
    ]
    for deal in deals:
        airlines = ",".join(deal.carriers) if deal.carriers else "N/A"
        lines.append(
            f"- {deal.origin}->{deal.destination} | "
            f"{deal.departure_at[:10]} | "
            f"{deal.price:.2f} {deal.currency} | "
            f"Aerolineas: {airlines} | Escalas: {deal.stops}"
        )
    return "\n".join(lines)
