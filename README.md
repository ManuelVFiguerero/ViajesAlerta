# Alerta de vuelos baratos (multi-aerolinea)

Este proyecto busca vuelos baratos para multiples rutas y varias aerolineas
(Copa, American Airlines, Avianca, LATAM, etc.) usando la API de Amadeus.

Puede ejecutarse una vez o en modo continuo (chequeo diario) y te avisa por
WhatsApp (Twilio) y opcionalmente por email cuando encuentra ofertas por debajo
de tu precio maximo.

## 1) Requisitos

- Python 3.10+
- Cuenta de Amadeus for Developers con:
  - `AMADEUS_CLIENT_ID`
  - `AMADEUS_CLIENT_SECRET`
- Cuenta Twilio con WhatsApp habilitado:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM` (ejemplo: `whatsapp:+14155238886`)
- Email es opcional

## 2) Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configuracion

1. Copia el ejemplo:

```bash
cp .env.example .env
```

2. Edita `.env` con tus claves y reglas.

### Rutas y destinos ampliados

`ORIGIN_AIRPORTS` + `DESTINATION_AIRPORTS` te genera automaticamente todas las
combinaciones origen-destino (sin repetir origen=destino).

En el `.env.example` viene listo para:

- Buenos Aires y Santiago -> Centroamerica, Europa, Brasil y USA
- Costa Rica -> Guatemala

Si preferis control manual, podes usar `ROUTES=...` y dejar vacias las variables
de grupos.

### Aerolineas

En `AIRLINES` podes filtrar por codigos IATA de aerolinea:

- CM = Copa
- AA = American Airlines
- AV = Avianca
- LA = LATAM

Si queres incluir todas, deja `AIRLINES=` vacio.

## 4) Notificaciones por WhatsApp

1. Crea un proyecto en Twilio y habilita WhatsApp sandbox o numero productivo.
2. Completa en `.env`:

```env
SEND_WHATSAPP=true
WHATSAPP_TO=whatsapp:+5492213041688
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

Con esto, cada vez que encuentre ofertas, te llega mensaje al WhatsApp.

## 5) Ejecucion

### Ejecutar una sola vez

```bash
python3 vuelo_alerta.py
```

### Ejecutar en modo diario/continuo

Configura:

```env
RUN_FOREVER=true
CHECK_INTERVAL_HOURS=24
```

Y luego:

```bash
python3 vuelo_alerta.py
```

## 6) Variables principales

- `MAX_PRICE`: precio maximo a considerar "barato"
- `ORIGIN_AIRPORTS`: origenes separados por coma (ej: `EZE,AEP,SCL,SJO`)
- `DESTINATION_AIRPORTS`: destinos separados por coma
- `ROUTES`: opcional; lista manual `ORIGEN-DESTINO` separada por coma
- `START_IN_DAYS`: desde que dia empezar a buscar (0 = hoy)
- `DEPARTURE_WINDOW_DAYS`: cuantos dias hacia adelante mirar
- `DATE_STEP_DAYS`: salto entre fechas (1 = todos los dias)
- `NONSTOP_ONLY`: solo directos o no
- `AIRLINES`: filtro opcional de aerolineas
- `SEND_WHATSAPP`: envia alertas por WhatsApp (Twilio)
- `SEND_EMAIL`: email opcional (por default `false`)

## 7) Notas

- El proyecto usa el endpoint de ofertas de vuelo de Amadeus.
- Los resultados dependen de disponibilidad y reglas del proveedor.
- Si no hay ofertas por debajo del umbral, no se envia alerta.
