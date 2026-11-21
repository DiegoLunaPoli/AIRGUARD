"""
AIRGUARD — Módulo de procesamiento de datos
Calcula estado, estadísticas y gestiona alertas con histéresis.
"""

import time
import logging
from collections import deque
from config import (
    LINEA_BASE_INICIAL, UMBRAL_PRECAUCION, UMBRAL_ALERTA,
    HISTORIAL_MAX, ALERTA_HISTÉRESIS, ALERTA_MIN_INTERVALO
)

logger = logging.getLogger(__name__)


class ProcesadorDatos:
    """
    Recibe lecturas del sensor, calcula estado y estadísticas,
    y determina cuándo emitir alertas.
    """

    def __init__(self):
        # Historial en memoria para gráfica (deque tiene tamaño fijo)
        self.historial = deque(maxlen=HISTORIAL_MAX)

        # Línea base adaptativa
        self.linea_base    = LINEA_BASE_INICIAL
        self.muestras_base = 0           # Cuántas muestras se usaron para calcular la base
        self.base_fijada   = False       # True cuando ya se calculó con datos reales

        # Umbrales (pueden modificarse desde la API)
        self.umbral_precaucion = UMBRAL_PRECAUCION
        self.umbral_alerta     = UMBRAL_ALERTA

        # Estado actual con histéresis
        self.estado_actual  = "NORMAL"
        self.estado_previo  = "NORMAL"

        # Estadísticas de sesión
        self.valor_min      = None
        self.valor_max      = None
        self.suma_total     = 0
        self.contador       = 0
        self.inicio_sesion  = time.time()

        # Control de alertas (evitar repetición excesiva)
        self._ultima_alerta_tipo = None
        self._ultima_alerta_ts   = 0

    def procesar(self, lectura: int, modo: str) -> dict:
        """
        Procesa una lectura. Devuelve un diccionario con:
        - lectura, modo, estado, estadísticas, variacion_pct
        - nueva_alerta (None o dict con la alerta a registrar)
        """
        ahora = time.time()

        # ── Actualizar línea base durante los primeros 20 valores ──
        if not self.base_fijada:
            self.muestras_base += 1
            # Promedio acumulativo
            self.linea_base = (
                (self.linea_base * (self.muestras_base - 1) + lectura) / self.muestras_base
            )
            if self.muestras_base >= 20:
                self.base_fijada = True
                logger.info("Línea base fijada en: %.1f", self.linea_base)

        # ── Estadísticas ───────────────────────────────────────────
        self.contador  += 1
        self.suma_total += lectura
        if self.valor_min is None or lectura < self.valor_min:
            self.valor_min = lectura
        if self.valor_max is None or lectura > self.valor_max:
            self.valor_max = lectura

        promedio = self.suma_total / self.contador

        # Variación porcentual respecto a la línea base
        if self.linea_base > 0:
            variacion_pct = ((lectura - self.linea_base) / self.linea_base) * 100.0
        else:
            variacion_pct = 0.0

        # ── Determinar estado con histéresis ───────────────────────
        nuevo_estado = self._calcular_estado(lectura)

        # ── Gestión de alertas ─────────────────────────────────────
        nueva_alerta = None
        if nuevo_estado != self.estado_actual:
            # Cambio de estado — registrar alerta si aplica
            if nuevo_estado in ("PRECAUCIÓN", "ALERTA"):
                # Respetar intervalo mínimo para el mismo tipo
                diferencia_ts = ahora - self._ultima_alerta_ts
                if (nuevo_estado != self._ultima_alerta_tipo or
                        diferencia_ts >= ALERTA_MIN_INTERVALO):
                    nueva_alerta = {
                        "tipo":    nuevo_estado,
                        "valor":   lectura,
                        "mensaje": f"Estado cambió a {nuevo_estado}. Lectura: {lectura}"
                    }
                    self._ultima_alerta_tipo = nuevo_estado
                    self._ultima_alerta_ts   = ahora

            self.estado_previo = self.estado_actual
            self.estado_actual = nuevo_estado

        # ── Agregar al historial ───────────────────────────────────
        self.historial.append({
            "ts":      ahora,
            "lectura": lectura,
            "estado":  nuevo_estado,
            "modo":    modo
        })

        return {
            "lectura":       lectura,
            "modo":          modo,
            "estado":        nuevo_estado,
            "linea_base":    round(self.linea_base, 1),
            "variacion_pct": round(variacion_pct, 2),
            "minimo":        self.valor_min,
            "maximo":        self.valor_max,
            "promedio":      round(promedio, 1),
            "contador":      self.contador,
            "nueva_alerta":  nueva_alerta,
            "duracion_s":    int(ahora - self.inicio_sesion),
        }

    def _calcular_estado(self, lectura: int) -> str:
        """
        Determina el estado con histéresis para evitar
        oscilaciones rápidas entre NORMAL / PRECAUCIÓN / ALERTA.
        """
        if self.estado_actual == "NORMAL":
            if lectura >= self.umbral_alerta:
                return "ALERTA"
            elif lectura >= self.umbral_precaucion:
                return "PRECAUCIÓN"
            return "NORMAL"

        elif self.estado_actual == "PRECAUCIÓN":
            if lectura >= self.umbral_alerta:
                return "ALERTA"
            # Bajar a NORMAL solo si cae HISTÉRESIS por debajo del umbral
            elif lectura < (self.umbral_precaucion - ALERTA_HISTÉRESIS):
                return "NORMAL"
            return "PRECAUCIÓN"

        else:  # ALERTA
            if lectura < (self.umbral_alerta - ALERTA_HISTÉRESIS):
                # Bajar a PRECAUCIÓN si aún está sobre el umbral de precaución
                if lectura >= self.umbral_precaucion:
                    return "PRECAUCIÓN"
                return "NORMAL"
            return "ALERTA"

    def set_umbrales(self, precaucion: int, alerta: int):
        """Permite modificar los umbrales desde la API."""
        self.umbral_precaucion = precaucion
        self.umbral_alerta     = alerta
        logger.info("Umbrales actualizados: PRECAUCIÓN=%d, ALERTA=%d", precaucion, alerta)

    def resetear_linea_base(self):
        """Reinicia el cálculo de la línea base."""
        self.linea_base    = LINEA_BASE_INICIAL
        self.muestras_base = 0
        self.base_fijada   = False

    def obtener_historial_grafica(self, ultimos_n: int = 120) -> list:
        """Devuelve los últimos N puntos del historial para la gráfica."""
        datos = list(self.historial)
        return datos[-ultimos_n:] if len(datos) > ultimos_n else datos

    def obtener_estadisticas(self) -> dict:
        """Devuelve el resumen de estadísticas de la sesión."""
        promedio = round(self.suma_total / self.contador, 1) if self.contador else 0
        duracion = int(time.time() - self.inicio_sesion)
        return {
            "minimo":        self.valor_min or 0,
            "maximo":        self.valor_max or 0,
            "promedio":      promedio,
            "contador":      self.contador,
            "linea_base":    round(self.linea_base, 1),
            "estado_actual": self.estado_actual,
            "duracion_s":    duracion,
        }
