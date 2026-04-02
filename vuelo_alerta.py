import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
MAX_PRICE = float(os.getenv("MAX_PRICE"))

ORIGEN = "ALC"  # IATA código de origen, ejemplo Alicante

def enviar_email(asunto, cuerpo):
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(cuerpo)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def buscar_vuelos():
    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=30)
    url = (
       f"https://www.ryanair.com/api/farfnd/3/oneWayFares?"
    f"departureAirportIataCode={ORIGEN}&"
    f"language=es&limit=50&market=es-es&offset=0&"
    f"outboundDepartureDateFrom={fecha_inicio.strftime('%Y-%m-%d')}&"
    f"outboundDepartureDateTo={fecha_fin.strftime('%Y-%m-%d')}"
    )

    print("Consultando API Ryanair...")
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error en consulta API: {resp.status_code}")
        return []

    data = resp.json()
    vuelos_baratos = []

    for fare in data.get("fares", []):
        precio = fare.get("summary", {}).get("price", {}).get("value", float("inf"))
        destino = fare.get("outbound", {}).get("arrivalAirport", {}).get("name", "Destino desconocido")
        fecha_salida = fare.get("outbound", {}).get("departureDate", "Fecha desconocida")
        if precio <= MAX_PRICE:
            vuelos_baratos.append({
                "destino": destino,
                "precio": precio,
                "fecha": fecha_salida[:10]  # solo fecha, sin hora
            })

    return vuelos_baratos

def main():
    vuelos = buscar_vuelos()
    if vuelos:
        cuerpo = f"✈️ Vuelos desde {ORIGEN} por menos de €{MAX_PRICE:.2f}:\n\n"
        for v in vuelos:
            cuerpo += f"- {v['destino']}: €{v['precio']} ({v['fecha']})\n"
        enviar_email("¡Vuelos baratos encontrados!", cuerpo)
        print("Email enviado con vuelos baratos.")
    else:
        print("No se encontraron vuelos baratos.")

if __name__ == "__main__":
    main()
