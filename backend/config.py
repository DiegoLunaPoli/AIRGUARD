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
UMBRAL_PRECAUCION = 1800   # Variación significativa
UMBRAL_ALERTA     = 2500   # Variación alta

# ── Estadísticas y alertas ─────────────────────────────────
HISTORIAL_MAX        = 500    # Máximo de puntos en memoria para gráfica
ALERTA_HISTÉRESIS    = 200    # El estado solo baja cuando cae HISTÉRESIS por debajo del umbral
ALERTA_MIN_INTERVALO = 10     # Segundos mínimos entre dos alertas del mismo tipo

# ── Nombre del sistema ─────────────────────────────────────
NOMBRE_SISTEMA  = "AIRGUARD"
VERSION_SISTEMA = "1.0.0"
