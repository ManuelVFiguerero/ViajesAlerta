from __future__ import annotations

import sys
import time

from flight_alert.config import AppConfig, load_config
from flight_alert.notifier import send_email_alert, send_whatsapp_alert
from flight_alert.service import render_deals_message, search_deals


def _run_once(config: AppConfig) -> bool:
    deals = search_deals(config)

    if not deals:
        print("No se encontraron vuelos baratos para los criterios configurados.")
        return False

    body = render_deals_message(deals, config=config)
    print(body)

    if config.send_whatsapp:
        try:
            send_whatsapp_alert(config=config, body=body)
            print("WhatsApp enviado con alertas de vuelos baratos.")
        except ValueError as exc:
            print(f"No se pudo enviar WhatsApp: {exc}")

    if config.send_email:
        try:
            send_email_alert(config=config, body=body)
            print("Email enviado con alertas de vuelos baratos.")
        except ValueError as exc:
            print(f"No se pudo enviar email: {exc}")
    else:
        print("SEND_EMAIL=false, se omite el envio de correo.")
    return True


def main() -> int:
    try:
        config = load_config()
    except Exception as exc:
        print(f"Error de configuracion: {exc}")
        return 1

    if config.run_forever:
        print(
            "Modo continuo activo: chequeo cada "
            f"{config.check_interval_hours} hora(s)."
        )
        while True:
            print("-" * 80)
            print("Iniciando nueva busqueda de vuelos...")
            try:
                _run_once(config)
            except Exception as exc:
                print(f"Error durante la busqueda: {exc}")
            sleep_seconds = config.check_interval_hours * 3600
            print(f"Esperando {config.check_interval_hours} hora(s) para el proximo ciclo.")
            time.sleep(sleep_seconds)

    try:
        _run_once(config)
    except Exception as exc:
        print(f"Error durante la ejecucion: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
