import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_routes(value: str) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for item in _parse_csv(value):
        if "-" not in item:
            raise ValueError(
                f"Ruta invalida '{item}'. Usa ORIGEN-DESTINO (ejemplo: EZE-SJO)."
            )

        origin, destination = item.split("-", 1)
        origin = origin.strip().upper()
        destination = destination.strip().upper()

        if len(origin) != 3 or len(destination) != 3:
            raise ValueError(
                f"Ruta invalida '{item}'. Cada codigo IATA debe tener 3 letras."
            )
        routes.append((origin, destination))

    if not routes:
        raise ValueError("ROUTES no contiene rutas validas.")
    return routes


def _parse_airports(value: str, var_name: str) -> list[str]:
    airports = [code.upper() for code in _parse_csv(value)]
    for code in airports:
        if len(code) != 3:
            raise ValueError(
                f"{var_name} contiene codigo invalido '{code}'. Usa IATA de 3 letras."
            )
    return airports


def _build_routes_from_groups(origins: list[str], destinations: list[str]) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for origin in origins:
        for destination in destinations:
            if origin != destination:
                routes.append((origin, destination))
    return routes


@dataclass(frozen=True)
class AppConfig:
    serpapi_key: str
    max_price: float
    routes: list[tuple[str, str]]
    airlines: list[str]
    start_in_days: int
    departure_window_days: int
    date_step_days: int
    adults: int
    nonstop: bool
    currency: str
    gl: str
    hl: str
    deep_search: bool
    max_results_per_date: int
    send_telegram: bool
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]
    email_sender: Optional[str]
    email_password: Optional[str]
    email_receiver: Optional[str]
    email_subject: str
    smtp_host: str
    smtp_port: int
    smtp_ssl: bool
    send_email: bool
    run_forever: bool
    check_interval_hours: int

    def allowed_airlines_set(self) -> Optional[set[str]]:
        if not self.airlines:
            return None
        return {code.upper() for code in self.airlines}


def load_config() -> AppConfig:
    serpapi_key = os.getenv("SERPAPI_KEY", "").strip()
    max_price_str = os.getenv("MAX_PRICE", "").strip()
    routes_str = os.getenv("ROUTES", "").strip()
    origin_airports_str = os.getenv("ORIGIN_AIRPORTS", "").strip()
    destination_airports_str = os.getenv("DESTINATION_AIRPORTS", "").strip()

    if not serpapi_key:
        raise ValueError("Falta SERPAPI_KEY.")
    if not max_price_str:
        raise ValueError("Falta MAX_PRICE.")
    max_price = float(max_price_str)
    if max_price <= 0:
        raise ValueError("MAX_PRICE debe ser mayor a 0.")

    if routes_str:
        routes = _parse_routes(routes_str)
    else:
        origins = _parse_airports(origin_airports_str, "ORIGIN_AIRPORTS")
        destinations = _parse_airports(destination_airports_str, "DESTINATION_AIRPORTS")
        if not origins or not destinations:
            raise ValueError(
                "Defini ROUTES o bien ORIGIN_AIRPORTS + DESTINATION_AIRPORTS."
            )
        routes = _build_routes_from_groups(origins, destinations)

    airlines = [code.upper() for code in _parse_csv(os.getenv("AIRLINES", ""))]

    start_in_days = int(os.getenv("START_IN_DAYS", "0"))
    departure_window_days = int(os.getenv("DEPARTURE_WINDOW_DAYS", "30"))
    date_step_days = int(os.getenv("DATE_STEP_DAYS", "1"))
    adults = int(os.getenv("ADULTS", "1"))
    nonstop = _bool_env("NONSTOP_ONLY", False)
    currency = os.getenv("CURRENCY", "USD").upper()
    gl = os.getenv("GOOGLE_FLIGHTS_GL", "ar").lower()
    hl = os.getenv("GOOGLE_FLIGHTS_HL", "es").lower()
    deep_search = _bool_env("DEEP_SEARCH", False)
    max_results_per_date = int(os.getenv("MAX_RESULTS_PER_DATE", "5"))

    send_telegram = _bool_env("SEND_TELEGRAM", True)
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    email_sender = os.getenv("EMAIL_SENDER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_receiver = os.getenv("EMAIL_RECEIVER")
    email_subject = os.getenv("EMAIL_SUBJECT", "Alerta de vuelos baratos")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_ssl = _bool_env("SMTP_SSL", True)
    send_email = _bool_env("SEND_EMAIL", False)

    run_forever = _bool_env("RUN_FOREVER", False)
    check_interval_hours = int(os.getenv("CHECK_INTERVAL_HOURS", "24"))

    if departure_window_days < 0:
        raise ValueError("DEPARTURE_WINDOW_DAYS no puede ser negativo.")
    if date_step_days <= 0:
        raise ValueError("DATE_STEP_DAYS debe ser mayor a 0.")
    if adults <= 0:
        raise ValueError("ADULTS debe ser mayor a 0.")
    if max_results_per_date <= 0:
        raise ValueError("MAX_RESULTS_PER_DATE debe ser mayor a 0.")
    if check_interval_hours <= 0:
        raise ValueError("CHECK_INTERVAL_HOURS debe ser mayor a 0.")

    return AppConfig(
        serpapi_key=serpapi_key,
        max_price=max_price,
        routes=routes,
        airlines=airlines,
        start_in_days=start_in_days,
        departure_window_days=departure_window_days,
        date_step_days=date_step_days,
        adults=adults,
        nonstop=nonstop,
        currency=currency,
        gl=gl,
        hl=hl,
        deep_search=deep_search,
        max_results_per_date=max_results_per_date,
        send_telegram=send_telegram,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        email_sender=email_sender,
        email_password=email_password,
        email_receiver=email_receiver,
        email_subject=email_subject,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_ssl=smtp_ssl,
        send_email=send_email,
        run_forever=run_forever,
        check_interval_hours=check_interval_hours,
    )
