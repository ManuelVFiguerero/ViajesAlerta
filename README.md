# Alerta de vuelos baratos (multi-aerolinea)

Este proyecto busca vuelos baratos para multiples rutas y varias aerolineas
(Copa, American Airlines, Avianca, LATAM, etc.) usando la API de Amadeus.

Puede ejecutarse una vez o en modo continuo (chequeo diario) y te avisa por email
cuando encuentra ofertas por debajo de tu precio maximo.

## 1) Requisitos

- Python 3.10+
- Cuenta de Amadeus for Developers con:
  - `AMADEUS_CLIENT_ID`
  - `AMADEUS_CLIENT_SECRET`
- Credenciales SMTP para email (por ejemplo Gmail con App Password)

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

### Ejemplo de rutas para tu caso

Ya viene cargado en `.env.example`:

- Buenos Aires -> Costa Rica
- Buenos Aires -> Guatemala
- Costa Rica -> Guatemala
- Santiago -> Costa Rica
- Santiago -> Guatemala

Formato:

```env
ROUTES=EZE-SJO,EZE-GUA,SJO-GUA,SCL-SJO,SCL-GUA
```

### Aerolineas

En `AIRLINES` podes filtrar por codigos IATA de aerolinea:

- CM = Copa
- AA = American Airlines
- AV = Avianca
- LA = LATAM

Si queres incluir todas, deja `AIRLINES=` vacio.

## 4) Ejecucion

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

## 5) Variables principales

- `MAX_PRICE`: precio maximo a considerar "barato"
- `ROUTES`: lista de rutas `ORIGEN-DESTINO` separadas por coma
- `START_IN_DAYS`: desde que dia empezar a buscar (0 = hoy)
- `DEPARTURE_WINDOW_DAYS`: cuantos dias hacia adelante mirar
- `DATE_STEP_DAYS`: salto entre fechas (1 = todos los dias)
- `NONSTOP_ONLY`: solo directos o no
- `AIRLINES`: filtro opcional de aerolineas
- `SEND_EMAIL`: si `false`, solo imprime resultados

## 6) Notas

- El proyecto usa el endpoint de ofertas de vuelo de Amadeus.
- Los resultados dependen de disponibilidad y reglas del proveedor.
- Si no hay ofertas por debajo del umbral, no se envia email.
