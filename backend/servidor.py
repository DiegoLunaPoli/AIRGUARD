"""
AIRGUARD — Servidor Flask principal
API REST local para el dashboard web.
Ejecutar con: python servidor.py
Acceder en:  http://127.0.0.1:5000
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, send_file

# Asegurar que Python encuentre los módulos del mismo directorio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOST, PORT, NOMBRE_SISTEMA, VERSION_SISTEMA
from database import (
    inicializar_db, iniciar_sesion, cerrar_sesion,
    guardar_medicion, guardar_alerta,
    obtener_mediciones_recientes, obtener_alertas_recientes,
    obtener_sesiones, exportar_csv, limpiar_datos_demo
)
from processor import ProcesadorDatos
from serial_manager import SerialManager

# ── Configuración de logging ───────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ── Aplicación Flask ───────────────────────────────────────
# Servir archivos estáticos desde la carpeta frontend/
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# ── Estado global compartido ───────────────────────────────
# Usamos un lock para evitar problemas de concurrencia entre
# el hilo serial y los handlers de Flask.
_lock        = threading.Lock()
_procesador  = ProcesadorDatos()
_sesion_id   = None
_ultimo_dato = {
    "lectura":       0,
    "modo":          "ESPERANDO",
    "estado":        "NORMAL",
    "linea_base":    1200,
    "variacion_pct": 0.0,
    "timestamp":     None,
    "conectado":     False,
    "minimo":        None,
    "maximo":        None,
    "promedio":      0,
    "contador":      0,
    "duracion_s":    0,
}
_alertas_recientes = []  # Cache en memoria de las últimas alertas
_modo_actual       = "ESPERANDO"

# ── Callback serial ────────────────────────────────────────

def _on_serial_data(datos: dict):
    """
    Se llama desde el hilo serial cada vez que llega un mensaje JSON.
    Procesa los datos y actualiza el estado global.
    """
    global _sesion_id, _modo_actual, _ultimo_dato

    modo = datos.get("modo", "DESCONOCIDO")

    # ── Manejo de desconexión ──────────────────────────────
    if modo == "DESCONECTADO":
        with _lock:
            _ultimo_dato["conectado"] = False
            _ultimo_dato["modo"]      = "DESCONECTADO"
        logger.warning("ESP32 desconectado.")
        # Registrar alerta de desconexión
        if _sesion_id:
            guardar_alerta(_sesion_id, "DESCONEXIÓN", 0, "El ESP32 se desconectó.")
        return

    # ── Validar campos obligatorios ────────────────────────
    if "lectura" not in datos:
        logger.warning("Mensaje sin campo 'lectura': %s", datos)
        return

    lectura = datos["lectura"]
    if not isinstance(lectura, (int, float)):
        logger.warning("Campo 'lectura' no numérico: %s", lectura)
        return
    lectura = int(lectura)
    if not (0 <= lectura <= 4095):
        logger.warning("Lectura fuera de rango ADC: %d", lectura)
        return

    # ── Gestión de sesión ──────────────────────────────────
    with _lock:
        if _sesion_id is None or _modo_actual != modo:
            if _sesion_id is not None:
                cerrar_sesion(_sesion_id)
            _sesion_id  = iniciar_sesion(modo)
            _modo_actual = modo
            logger.info("Nueva sesión iniciada. ID=%d, Modo=%s", _sesion_id, modo)

        # ── Procesar ───────────────────────────────────────
        resultado = _procesador.procesar(lectura, modo)

        # ── Guardar en SQLite ──────────────────────────────
        guardar_medicion(_sesion_id, lectura, modo, resultado["estado"])

        # ── Gestionar alerta si hay una nueva ─────────────
        if resultado["nueva_alerta"]:
            alerta = resultado["nueva_alerta"]
            guardar_alerta(_sesion_id, alerta["tipo"], alerta["valor"], alerta["mensaje"])
            _alertas_recientes.insert(0, {
                "timestamp": datetime.now().isoformat(),
                "tipo":      alerta["tipo"],
                "valor":     alerta["valor"],
                "mensaje":   alerta["mensaje"]
            })
            # Mantener solo las últimas 50 en memoria
            if len(_alertas_recientes) > 50:
                _alertas_recientes.pop()

        # ── Actualizar estado global ───────────────────────
        _ultimo_dato.update({
            "lectura":       lectura,
            "modo":          modo,
            "estado":        resultado["estado"],
            "linea_base":    resultado["linea_base"],
            "variacion_pct": resultado["variacion_pct"],
            "timestamp":     datetime.now().isoformat(),
            "conectado":     True,
            "minimo":        resultado["minimo"],
            "maximo":        resultado["maximo"],
            "promedio":      resultado["promedio"],
            "contador":      resultado["contador"],
            "duracion_s":    resultado["duracion_s"],
        })


# ── SerialManager ──────────────────────────────────────────
_serial = SerialManager(callback=_on_serial_data)

# ── Rutas Flask ────────────────────────────────────────────

@app.route("/")
def index():
    """Sirve el dashboard principal."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/status")
def api_status():
    """Estado general del sistema: conexión, modo, última lectura."""
    with _lock:
        dato = dict(_ultimo_dato)
    serial_estado = _serial.obtener_estado()
    return jsonify({
        "sistema":     NOMBRE_SISTEMA,
        "version":     VERSION_SISTEMA,
        "timestamp":   datetime.now().isoformat(),
        "serial":      serial_estado,
        "dato":        dato,
        "umbrales": {
            "precaucion": _procesador.umbral_precaucion,
            "alerta":     _procesador.umbral_alerta,
        }
    })


@app.route("/api/data")
def api_data():
    """Lectura actual y estadísticas para el dashboard."""
    with _lock:
        dato = dict(_ultimo_dato)
    stats = _procesador.obtener_estadisticas()
    historial = _procesador.obtener_historial_grafica()

    # Preparar historial para la gráfica (solo campos necesarios)
    grafica = [{
        "ts":      round(p["ts"], 2),
        "lectura": p["lectura"],
        "estado":  p["estado"],
        "modo":    p["modo"],
    } for p in historial]

    return jsonify({
        "dato":       dato,
        "estadisticas": stats,
        "grafica":    grafica,
        "umbrales": {
            "precaucion": _procesador.umbral_precaucion,
            "alerta":     _procesador.umbral_alerta,
            "linea_base": stats["linea_base"],
        }
    })


@app.route("/api/history")
def api_history():
    """Historial de mediciones y sesiones desde SQLite."""
    limite = request.args.get("limite", 100, type=int)
    return jsonify({
        "mediciones": obtener_mediciones_recientes(limite),
        "sesiones":   obtener_sesiones(10),
    })


@app.route("/api/statistics")
def api_statistics():
    """Estadísticas de la sesión actual."""
    return jsonify(_procesador.obtener_estadisticas())


@app.route("/api/alerts")
def api_alerts():
    """Alertas recientes (combinación de cache en memoria y SQLite)."""
    limite = request.args.get("limite", 50, type=int)
    with _lock:
        cache = list(_alertas_recientes[:limite])
    # Completar con SQLite si hay pocas en cache
    if len(cache) < 5:
        cache = obtener_alertas_recientes(limite)
    return jsonify({"alertas": cache})


@app.route("/api/ports")
def api_ports():
    """Lista los puertos COM disponibles en el sistema."""
    return jsonify({"puertos": SerialManager.listar_puertos()})


@app.route("/api/set_port", methods=["POST"])
def api_set_port():
    """Cambia el puerto serial activo."""
    datos = request.get_json()
    if not datos or "puerto" not in datos:
        return jsonify({"error": "Se requiere campo 'puerto'"}), 400
    puerto = datos["puerto"]
    _serial.cambiar_puerto(puerto)
    return jsonify({"ok": True, "puerto": puerto})


@app.route("/api/set_thresholds", methods=["POST"])
def api_set_thresholds():
    """Actualiza los umbrales de PRECAUCIÓN y ALERTA."""
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "Sin datos JSON"}), 400
    try:
        precaucion = int(datos.get("precaucion", _procesador.umbral_precaucion))
        alerta     = int(datos.get("alerta",     _procesador.umbral_alerta))
        if not (0 < precaucion < alerta <= 4095):
            return jsonify({"error": "Valores inválidos. precaucion < alerta <= 4095"}), 400
        _procesador.set_umbrales(precaucion, alerta)
        return jsonify({"ok": True, "precaucion": precaucion, "alerta": alerta})
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/export")
def api_export():
    """Exporta mediciones a CSV y descarga el archivo."""
    ruta = exportar_csv()
    return send_file(ruta, as_attachment=True, download_name="airguard_datos.csv")


@app.route("/api/clear_demo", methods=["POST"])
def api_clear_demo():
    """Elimina todos los datos de sesiones DEMO."""
    n = limpiar_datos_demo()
    return jsonify({"ok": True, "sesiones_eliminadas": n})


@app.route("/api/reset_baseline", methods=["POST"])
def api_reset_baseline():
    """Reinicia el cálculo de la línea base."""
    _procesador.resetear_linea_base()
    return jsonify({"ok": True, "mensaje": "Línea base reiniciada."})


# ── Inicio del servidor ────────────────────────────────────

def main():
    global _sesion_id

    # Crear carpeta data si no existe
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
                exist_ok=True)

    # Inicializar base de datos
    inicializar_db()

    # Iniciar gestor serial en hilo de fondo
    _serial.iniciar()

    logger.info("=" * 55)
    logger.info("  %s v%s", NOMBRE_SISTEMA, VERSION_SISTEMA)
    logger.info("  Dashboard:  http://%s:%d", HOST, PORT)
    logger.info("  API:        http://%s:%d/api/status", HOST, PORT)
    logger.info("=" * 55)

    # Iniciar Flask (use_reloader=False es necesario porque ya
    # tenemos un hilo de fondo; el reloader crearía dos instancias)
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
