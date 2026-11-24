"""
AIRGUARD — Configuración central del backend
Modifica estos valores para ajustar el comportamiento del sistema.
"""

import os

# ── Rutas del proyecto ─────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data")
DB_PATH     = os.path.join(DATA_DIR, "airguard.db")
EXPORT_PATH = os.path.join(DATA_DIR, "exportacion.csv")

# ── Servidor Flask ─────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 5000

# ── Serial ────────────────────────────────────────────────
SERIAL_PORT     = "COM5"       # Puerto del ESP32. Se puede cambiar desde la API.
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT  = 2            # Segundos de espera por lectura serial
SERIAL_RETRY_S  = 5            # Segundos entre intentos de reconexión

# ── Sensor y umbrales (ADC 12 bits: 0–4095) ───────────────
# Línea base inicial. El sistema la actualiza automáticamente
# durante los primeros segundos de operación.
LINEA_BASE_INICIAL = 1200

# Umbrales experimentales (configurables desde el dashboard)
UMBRAL_PRECAUCION = 150    # Nivel elevado de gases (~3,7 % del rango ADC)
UMBRAL_ALERTA     = 700    # Nivel alto de gases (~17,1 % del rango ADC)

# ── Estadísticas y alertas ─────────────────────────────────
HISTORIAL_MAX        = 500    # Máximo de puntos en memoria para gráfica

# Histéresis como FRACCIÓN del umbral (no valor fijo). Así funciona
# también cuando los umbrales se cambian desde la API:
#   salir de ALERTA     cuando lectura < 0,85 * UMBRAL_ALERTA     (595)
#   salir de PRECAUCIÓN cuando lectura < 0,85 * UMBRAL_PRECAUCION (127)
# Con una histéresis fija de 200 los estados quedaban colgados.
HISTERESIS_SALIDA    = 0.85
ALERTA_MIN_INTERVALO = 10     # Segundos mínimos entre dos alertas del mismo tipo
MUESTRAS_TENDENCIA   = 6      # Muestras para detectar si el nivel sube o baja

# ── Nombre del sistema ─────────────────────────────────────
NOMBRE_SISTEMA  = "AIRGUARD"
VERSION_SISTEMA = "1.0.0"
