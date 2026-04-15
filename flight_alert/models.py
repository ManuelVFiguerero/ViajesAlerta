from dataclasses import dataclass


@dataclass(frozen=True)
class FlightOffer:
    origin: str
    destination: str
    departure_at: str
    arrival_at: str
    return_at: str | None
    deep_link: str
    price: float
    currency: str
    carriers: tuple[str, ...]
    stops: int

    def dedupe_key(self) -> tuple[str, str, str, str, tuple[str, ...]]:
        """Key used to keep cheapest offer per route/date/airline combo."""
        return (
            self.origin,
            self.destination,
            self.departure_at[:10],
            self.return_at[:10] if self.return_at else "",
            self.carriers,
        )
