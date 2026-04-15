# Alerta de vuelos baratos (SerpAPI + Telegram)

Este proyecto busca vuelos baratos para multiples rutas y varias aerolineas
(Copa, American Airlines, Avianca, LATAM, etc.) usando **SerpAPI (Google Flights)**.

Puede ejecutarse una vez o en modo continuo (chequeo diario) y te avisa por
**Telegram** (canal principal) y opcionalmente por email cuando encuentra
ofertas por debajo de tu precio maximo.

Soporta:
- `TRIP_TYPE=2` (solo ida)
- `TRIP_TYPE=1` (ida y vuelta) con vuelta flexible, por ejemplo entre 28 y 32 dias.

## 1) Requisitos

- Python 3.10+
- Cuenta SerpAPI con:
  - `SERPAPI_KEY`
- Bot de Telegram (gratis) con:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- Email opcional

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

`ORIGIN_AIRPORTS` + `DESTINATION_AIRPORTS` genera automaticamente todas las
combinaciones origen-destino (sin repetir origen=destino).

En el `.env.example` ya viene listo para:

- Buenos Aires y Santiago -> Centroamerica, Europa, Brasil y USA
- Costa Rica -> Guatemala

Si preferis control manual, podes usar `ROUTES=...` y dejar vacias las
variables de grupos.

### Fechas de diciembre + vuelta ~30 dias

Si queres buscar para fiestas de fin de ano, configura salida fija en diciembre:

```env
TRIP_TYPE=1
FIXED_DEPARTURE_DATE_FROM=2026-12-15
FIXED_DEPARTURE_DATE_TO=2026-12-31
RETURN_DAYS_MIN=28
RETURN_DAYS_MAX=32
RETURN_DAYS_STEP=1
```

Con eso prueba salidas entre esas fechas y regreso entre 28 y 32 dias despues.

### Aerolineas

En `AIRLINES` podes filtrar por codigos IATA de aerolinea:

- CM = Copa
- AA = American Airlines
- AV = Avianca
- LA = LATAM

Si queres incluir todas, deja `AIRLINES=` vacio.

### Evitar errores 429 (Too Many Requests)

Si ves muchos `429` de SerpAPI, baja volumen por corrida con:

```env
DEEP_SEARCH=false
MAX_RESULTS_PER_DATE=1
REQUEST_THROTTLE_SECONDS=0.7
MAX_REQUESTS_PER_RUN=40
SERPAPI_MAX_RETRIES=4
SERPAPI_BACKOFF_BASE_SECONDS=2.0
```

Tambien ayuda usar menos rutas por corrida (por bloques).

### Rotacion diaria de rutas con presupuesto (ideal para 250 consultas/mes)

Si tu plan tiene pocas consultas, podes limitar la corrida a un presupuesto fijo y
hacer que el sistema cambie de rutas automaticamente cada dia:

```env
DAILY_REQUEST_BUDGET=6
ROTATE_ROUTES_DAILY=true
ROUTE_ROTATION_STATE_FILE=data/route_rotation_state.json
```

Con eso:
- la corrida usa como maximo 6 requests (ademas de `REQUEST_MAX_PER_RUN`);
- cada dia toma otro bloque de rutas de forma circular;
- no tenes que cambiar `ROUTES` manualmente todos los dias.

Tip: combina esto con cron diario (una sola corrida por dia).

### Error 401 Unauthorized en SerpAPI

Si ves en logs `401 Unauthorized` o `403 Forbidden`:

1. Verifica que `SERPAPI_KEY` en `.env` sea la clave vigente.
2. Si la clave se expuso en capturas/logs, regenerala en SerpAPI y actualiza `.env`.
3. Revisa que la cuenta tenga plan activo y permiso para `google_flights`.

El script ahora corta la corrida al detectar 401/403 para evitar llenar el log con el mismo error.

## 4) Notificaciones por Telegram (gratis)

1. Crea un bot con **@BotFather** y copia el token.
2. Habla con tu bot (envia cualquier mensaje).
3. Abri en navegador:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
4. Copia el `chat.id` y colocalo en `.env`.

Variables:

```env
SEND_TELEGRAM=true
TELEGRAM_BOT_TOKEN=123456789:AA...
TELEGRAM_CHAT_ID=123456789
```

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

- `SERPAPI_KEY`: clave privada de SerpAPI
- `MAX_PRICE`: precio maximo a considerar "barato"
- `ORIGIN_AIRPORTS`: origenes separados por coma (ej: `EZE,AEP,SCL,SJO`)
- `DESTINATION_AIRPORTS`: destinos separados por coma
- `ROUTES`: opcional; lista manual `ORIGEN-DESTINO` separada por coma
- `START_IN_DAYS`: desde que dia empezar a buscar (0 = hoy)
- `DEPARTURE_WINDOW_DAYS`: cuantos dias hacia adelante mirar
- `DATE_STEP_DAYS`: salto entre fechas (1 = todos los dias)
- `TRIP_TYPE`: `2` solo ida, `1` ida y vuelta
- `FIXED_DEPARTURE_DATE_FROM` y `FIXED_DEPARTURE_DATE_TO`: rango fijo de salida
- `RETURN_DAYS_MIN` / `RETURN_DAYS_MAX`: ventana de dias para retorno (solo ida y vuelta)
- `RETURN_DAYS_STEP`: salto de dias para probar retornos
- `NONSTOP_ONLY`: solo directos o no
- `AIRLINES`: filtro opcional de aerolineas
- `GOOGLE_FLIGHTS_GL`: pais Google Flights (ej: `ar`)
- `GOOGLE_FLIGHTS_HL`: idioma Google Flights (ej: `es`)
- `REQUEST_THROTTLE_SECONDS`: pausa entre requests para no saturar la API
- `MAX_REQUESTS_PER_RUN`: tope de requests por ejecucion
- `DAILY_REQUEST_BUDGET`: tope diario deseado (si > 0, aplica como limite adicional por corrida)
- `ROTATE_ROUTES_DAILY`: rota rutas automaticamente entre corridas diarias
- `ROUTE_ROTATION_STATE_FILE`: archivo donde se guarda el puntero de rotacion
- `SERPAPI_MAX_RETRIES`: reintentos automáticos en 429/5xx
- `SERPAPI_BACKOFF_BASE_SECONDS`: base de espera exponencial entre reintentos
- `SEND_PROMOS`: habilita envio de promos desde RSS
- `PROMO_FEEDS`: lista de feeds RSS separados por coma
- `PROMO_MAX_ITEMS`: maximo de promos por mensaje
- `SEND_TELEGRAM`: envia alertas por Telegram
- `SEND_EMAIL`: email opcional (por default `false`)

## 7) Notas

- El proyecto consulta resultados de Google Flights via SerpAPI.
- Los resultados dependen de disponibilidad y reglas del proveedor.
- Si no hay ofertas por debajo del umbral, no se envia alerta.
- Si alguna combinacion devuelve error o sin resultados, se salta y el resto continua.
- Cada oferta en Telegram incluye un enlace directo a Google Flights.
- Si activas promos RSS (`SEND_PROMOS=true`), Telegram incluye bloque de promociones.
