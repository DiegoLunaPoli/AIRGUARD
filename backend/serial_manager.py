"""
AIRGUARD — Gestor de comunicación serial con el ESP32
Lee mensajes JSON del puerto serial en un hilo independiente.
No bloquea Flask si el ESP32 se desconecta.
"""

import serial
import serial.tools.list_ports
import threading
import json
import time
import logging
from config import SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TIMEOUT, SERIAL_RETRY_S

logger = logging.getLogger(__name__)


class SerialManager:
    """
    Gestiona la conexión serial con el ESP32.
    Opera en un hilo separado para no bloquear Flask.
    """

    def __init__(self, callback):
        """
        callback: función que se llama con cada mensaje JSON válido recibido.
                  Firma: callback(datos: dict)
        """
        self._callback    = callback
        self._puerto      = SERIAL_PORT
        self._baudrate    = SERIAL_BAUDRATE
        self._conn        = None          # Objeto serial.Serial
        self._hilo        = None          # Hilo de lectura
        self._activo      = False         # Controla el bucle del hilo
        self._conectado   = False         # Estado de la conexión
        self._ultimo_msg  = None          # Timestamp del último mensaje recibido
        self._errores     = 0             # Contador de errores consecutivos

    # ── Propiedades públicas ───────────────────────────────

    @property
    def conectado(self) -> bool:
        return self._conectado

    @property
    def puerto(self) -> str:
        return self._puerto

    @property
    def ultimo_mensaje(self):
        return self._ultimo_msg

    # ── Control de la conexión ─────────────────────────────

    def iniciar(self, puerto: str = None):
        """Inicia el hilo de lectura serial."""
        if puerto:
            self._puerto = puerto

        self._activo = True
        self._hilo   = threading.Thread(
            target=self._bucle_lectura,
            daemon=True,         # El hilo muere cuando cierra el programa principal
            name="SerialThread"
        )
        self._hilo.start()
        logger.info("Hilo serial iniciado. Puerto objetivo: %s", self._puerto)

    def detener(self):
        """Detiene el hilo de lectura y cierra el puerto."""
        self._activo = False
        self._cerrar_puerto()
        logger.info("SerialManager detenido.")

    def cambiar_puerto(self, nuevo_puerto: str):
        """Cambia el puerto serial y reinicia la conexión."""
        logger.info("Cambiando puerto de %s a %s", self._puerto, nuevo_puerto)
        self._cerrar_puerto()
        self._puerto    = nuevo_puerto
        self._conectado = False
        self._errores   = 0

    # ── Bucle de lectura ───────────────────────────────────

    def _bucle_lectura(self):
        """
        Bucle principal del hilo serial.
        Intenta conectar, lee mensajes y reconecta si hay error.
        """
        while self._activo:
            if not self._conectado:
                self._intentar_conexion()
                if not self._conectado:
                    # Esperar antes de reintentar
                    time.sleep(SERIAL_RETRY_S)
                    continue

            try:
                linea = self._conn.readline()
                if not linea:
                    continue

                texto = linea.decode("utf-8", errors="ignore").strip()
                if not texto:
                    continue

                # Intentar parsear como JSON
                try:
                    datos = json.loads(texto)
                    self._errores  = 0
                    self._ultimo_msg = time.time()
                    self._callback(datos)
                except json.JSONDecodeError:
                    # Puede ser un mensaje de arranque del ESP32 — ignorar
                    logger.debug("Línea no JSON ignorada: %s", texto[:80])

            except serial.SerialException as e:
                logger.warning("Error serial: %s", e)
                self._conectado = False
                self._cerrar_puerto()
                self._errores += 1
                # Notificar desconexión a través del callback
                self._callback({
                    "modo":    "DESCONECTADO",
                    "lectura": 0,
                    "timestamp": 0,
                    "error":   str(e)
                })

            except Exception as e:
                logger.error("Error inesperado en hilo serial: %s", e)
                self._conectado = False
                self._cerrar_puerto()
                time.sleep(2)

    def _intentar_conexion(self):
        """Intenta abrir el puerto serial."""
        try:
            logger.info("Intentando conectar a %s a %d baudios...",
                        self._puerto, self._baudrate)
            self._conn = serial.Serial(
                port=self._puerto,
                baudrate=self._baudrate,
                timeout=SERIAL_TIMEOUT
            )
            # Dar tiempo al ESP32 para reiniciarse (normal al abrir puerto)
            time.sleep(2)
            self._conn.reset_input_buffer()
            self._conectado = True
            self._errores   = 0
            logger.info("Conectado a %s", self._puerto)

        except serial.SerialException as e:
            logger.warning("No se pudo conectar a %s: %s", self._puerto, e)
            self._conectado = False

    def _cerrar_puerto(self):
        """Cierra el puerto serial de forma segura."""
        if self._conn and self._conn.is_open:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None

    # ── Utilidades ─────────────────────────────────────────

    @staticmethod
    def listar_puertos() -> list:
        """Devuelve lista de puertos COM disponibles en el sistema."""
        puertos = []
        for p in serial.tools.list_ports.comports():
            puertos.append({
                "puerto":      p.device,
                "descripcion": p.description,
                "hwid":        p.hwid
            })
        return puertos

    def obtener_estado(self) -> dict:
        """Devuelve el estado actual del gestor serial."""
        ahora = time.time()
        ultimo_hace = None
        if self._ultimo_msg:
            ultimo_hace = round(ahora - self._ultimo_msg, 1)

        return {
            "conectado":        self._conectado,
            "puerto":           self._puerto,
            "baudrate":         self._baudrate,
            "ultimo_mensaje_s": ultimo_hace,
            "errores":          self._errores,
        }
