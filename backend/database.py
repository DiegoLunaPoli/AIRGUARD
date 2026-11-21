"""
AIRGUARD — Módulo de base de datos (SQLite)
Gestiona la creación de tablas, inserción y consulta de datos.
"""

import sqlite3
import os
import csv
import logging
from datetime import datetime
from config import DB_PATH, DATA_DIR, EXPORT_PATH

logger = logging.getLogger(__name__)


def _conectar():
    """Abre una conexión a la base de datos SQLite."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder por nombre de columna
    return conn


def inicializar_db():
    """Crea las tablas si no existen."""
    conn = _conectar()
    cur  = conn.cursor()

    # ── Tabla de sesiones ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            inicio      TEXT    NOT NULL,
            fin         TEXT,
            modo        TEXT    NOT NULL DEFAULT 'DEMO',
            total_meds  INTEGER DEFAULT 0
        )
    """)

    # ── Tabla de mediciones ────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mediciones (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id  INTEGER NOT NULL,
            timestamp  TEXT    NOT NULL,
            lectura    INTEGER NOT NULL,
            modo       TEXT    NOT NULL,
            estado     TEXT    NOT NULL DEFAULT 'NORMAL',
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)

    # ── Tabla de alertas ───────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id  INTEGER NOT NULL,
            timestamp  TEXT    NOT NULL,
            tipo       TEXT    NOT NULL,
            valor      INTEGER NOT NULL,
            mensaje    TEXT,
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente en: %s", DB_PATH)


def iniciar_sesion(modo: str) -> int:
    """Registra el inicio de una sesión. Devuelve el ID de sesión."""
    conn = _conectar()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO sesiones (inicio, modo) VALUES (?, ?)",
        (datetime.now().isoformat(), modo)
    )
    sesion_id = cur.lastrowid
    conn.commit()
    conn.close()
    logger.info("Sesión iniciada. ID=%d, Modo=%s", sesion_id, modo)
    return sesion_id


def cerrar_sesion(sesion_id: int):
    """Registra el fin de una sesión."""
    conn = _conectar()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE sesiones SET fin = ? WHERE id = ?",
        (datetime.now().isoformat(), sesion_id)
    )
    conn.commit()
    conn.close()


def guardar_medicion(sesion_id: int, lectura: int, modo: str, estado: str):
    """Inserta una medición en la base de datos."""
    conn = _conectar()
    cur  = conn.cursor()
    ts   = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO mediciones (sesion_id, timestamp, lectura, modo, estado) VALUES (?, ?, ?, ?, ?)",
        (sesion_id, ts, lectura, modo, estado)
    )
    # Actualizar contador de mediciones en la sesión
    cur.execute(
        "UPDATE sesiones SET total_meds = total_meds + 1 WHERE id = ?",
        (sesion_id,)
    )
    conn.commit()
    conn.close()


def guardar_alerta(sesion_id: int, tipo: str, valor: int, mensaje: str):
    """Registra una alerta en la base de datos."""
    conn = _conectar()
    cur  = conn.cursor()
    ts   = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO alertas (sesion_id, timestamp, tipo, valor, mensaje) VALUES (?, ?, ?, ?, ?)",
        (sesion_id, ts, tipo, valor, mensaje)
    )
    conn.commit()
    conn.close()
    logger.info("Alerta registrada: %s — valor=%d", tipo, valor)


def obtener_mediciones_recientes(limite: int = 200) -> list:
    """Devuelve las últimas N mediciones como lista de diccionarios."""
    conn = _conectar()
    cur  = conn.cursor()
    cur.execute(
        "SELECT timestamp, lectura, modo, estado FROM mediciones ORDER BY id DESC LIMIT ?",
        (limite,)
    )
    filas = [dict(f) for f in cur.fetchall()]
    conn.close()
    return list(reversed(filas))  # Orden cronológico


def obtener_alertas_recientes(limite: int = 50) -> list:
    """Devuelve las últimas N alertas."""
    conn = _conectar()
    cur  = conn.cursor()
    cur.execute(
        "SELECT timestamp, tipo, valor, mensaje FROM alertas ORDER BY id DESC LIMIT ?",
        (limite,)
    )
    filas = [dict(f) for f in cur.fetchall()]
    conn.close()
    return filas


def obtener_sesiones(limite: int = 20) -> list:
    """Devuelve las últimas N sesiones."""
    conn = _conectar()
    cur  = conn.cursor()
    cur.execute(
        "SELECT id, inicio, fin, modo, total_meds FROM sesiones ORDER BY id DESC LIMIT ?",
        (limite,)
    )
    filas = [dict(f) for f in cur.fetchall()]
    conn.close()
    return filas


def exportar_csv() -> str:
    """Exporta todas las mediciones a un archivo CSV. Devuelve la ruta del archivo."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = _conectar()
    cur  = conn.cursor()
    cur.execute(
        "SELECT m.id, m.timestamp, m.lectura, m.modo, m.estado, m.sesion_id "
        "FROM mediciones m ORDER BY m.id"
    )
    filas = cur.fetchall()
    conn.close()

    with open(EXPORT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "timestamp", "lectura", "modo", "estado", "sesion_id"])
        for fila in filas:
            writer.writerow(list(fila))

    logger.info("CSV exportado: %s (%d filas)", EXPORT_PATH, len(filas))
    return EXPORT_PATH


def limpiar_datos_demo():
    """Elimina todas las mediciones, alertas y sesiones marcadas como DEMO."""
    conn = _conectar()
    cur  = conn.cursor()

    # Obtener IDs de sesiones DEMO
    cur.execute("SELECT id FROM sesiones WHERE modo = 'DEMO'")
    ids = [str(r[0]) for r in cur.fetchall()]

    if ids:
        marcadores = ",".join(ids)
        cur.execute(f"DELETE FROM mediciones WHERE sesion_id IN ({marcadores})")
        cur.execute(f"DELETE FROM alertas    WHERE sesion_id IN ({marcadores})")
        cur.execute(f"DELETE FROM sesiones   WHERE id         IN ({marcadores})")
        conn.commit()
        logger.info("Datos DEMO eliminados. Sesiones: %s", marcadores)

    conn.close()
    return len(ids)
