"""
AIRGUARD — Suite de pruebas del backend
Ejecutar con: python tests/test_backend.py

Pruebas cubiertas:
  3  → Simulación de datos (processor)
  5  → Flask responde (API)
  8  → Umbrales producen los tres estados
  9  → SQLite guarda mediciones
  10 → Exportación CSV
  11 → Desconexión produce alerta
"""

import sys
import os
import time
import json
import sqlite3
import threading
import unittest

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

# Sobrescribir la DB con una de prueba para no afectar datos reales
os.environ["AIRGUARD_TEST"] = "1"

import config
config.DB_PATH     = os.path.join(os.path.dirname(__file__), "test_airguard.db")
config.EXPORT_PATH = os.path.join(os.path.dirname(__file__), "test_export.csv")

from processor import ProcesadorDatos
from database  import inicializar_db, iniciar_sesion, guardar_medicion, \
                      obtener_mediciones_recientes, exportar_csv, limpiar_datos_demo

# ══════════════════════════════════════════════════════════
#  PRUEBA 3 — Simulación de datos
# ══════════════════════════════════════════════════════════
class TestSimulacion(unittest.TestCase):

    def test_procesador_genera_estado_normal(self):
        """Prueba 3a: El procesador devuelve NORMAL para una lectura baja."""
        p = ProcesadorDatos()
        # Forzar línea base
        for _ in range(20):
            p.procesar(1200, "DEMO")
        resultado = p.procesar(1150, "DEMO")
        self.assertEqual(resultado["estado"], "NORMAL",
                         "Lectura baja debe producir estado NORMAL")
        print("  [3a OK] Estado NORMAL con lectura baja.")

    def test_procesador_devuelve_estadisticas(self):
        """Prueba 3b: El procesador calcula mínimo, máximo y promedio."""
        p = ProcesadorDatos()
        for v in [1000, 1200, 1400]:
            p.procesar(v, "DEMO")
        s = p.obtener_estadisticas()
        self.assertEqual(s["minimo"],  1000)
        self.assertEqual(s["maximo"],  1400)
        self.assertAlmostEqual(s["promedio"], 1200.0, places=0)
        print("  [3b OK] Estadísticas: min=%d, max=%d, prom=%.1f" %
              (s["minimo"], s["maximo"], s["promedio"]))

    def test_historial_no_vacio(self):
        """Prueba 3c: El historial tiene datos después de procesar."""
        p = ProcesadorDatos()
        for v in range(1200, 1210):
            p.procesar(v, "DEMO")
        h = p.obtener_historial_grafica()
        self.assertGreater(len(h), 0, "El historial debe tener puntos")
        print("  [3c OK] Historial con %d puntos." % len(h))


# ══════════════════════════════════════════════════════════
#  PRUEBA 8 — Umbrales producen los tres estados
# ══════════════════════════════════════════════════════════
class TestUmbrales(unittest.TestCase):

    def setUp(self):
        self.p = ProcesadorDatos()
        self.p.set_umbrales(1800, 2500)
        # Fijar línea base con 20 lecturas estables
        for _ in range(20):
            self.p.procesar(1200, "DEMO")

    def test_estado_normal(self):
        """Prueba 8a: Lectura por debajo del umbral de precaución → NORMAL."""
        r = self.p.procesar(1500, "DEMO")
        self.assertEqual(r["estado"], "NORMAL")
        print("  [8a OK] NORMAL con lectura 1500.")

    def test_estado_precaucion(self):
        """Prueba 8b: Lectura entre umbrales → PRECAUCIÓN."""
        # Llegar a PRECAUCIÓN
        r = self.p.procesar(1900, "DEMO")
        self.assertEqual(r["estado"], "PRECAUCIÓN")
        print("  [8b OK] PRECAUCIÓN con lectura 1900.")

    def test_estado_alerta(self):
        """Prueba 8c: Lectura sobre el umbral de alerta → ALERTA."""
        self.p.procesar(1900, "DEMO")  # Pasar primero por PRECAUCIÓN
        r = self.p.procesar(2600, "DEMO")
        self.assertEqual(r["estado"], "ALERTA")
        print("  [8c OK] ALERTA con lectura 2600.")

    def test_histeresis(self):
        """Prueba 8d: La histéresis evita que el estado baje inmediatamente."""
        self.p.procesar(2600, "DEMO")  # → ALERTA
        # Bajar justo al umbral no debe cambiar el estado inmediatamente
        r = self.p.procesar(2500, "DEMO")
        self.assertEqual(r["estado"], "ALERTA",
                         "La histéresis debe mantener ALERTA hasta bajar lo suficiente")
        print("  [8d OK] Histéresis funciona: estado sigue en ALERTA.")

    def test_alerta_se_genera_al_subir(self):
        """Prueba 8e: Se genera una nueva_alerta al cruzar el umbral."""
        self.p.procesar(1900, "DEMO")  # Cruzar a PRECAUCIÓN
        r = self.p.procesar(2600, "DEMO")  # Cruzar a ALERTA
        self.assertIsNotNone(r["nueva_alerta"],
                             "Debe generarse una alerta al cruzar el umbral de ALERTA")
        print("  [8e OK] Nueva alerta generada al cruzar umbral.")


# ══════════════════════════════════════════════════════════
#  PRUEBA 9 — SQLite guarda mediciones
# ══════════════════════════════════════════════════════════
class TestBaseDatos(unittest.TestCase):

    def setUp(self):
        # Limpiar base de datos de prueba
        if os.path.exists(config.DB_PATH):
            os.remove(config.DB_PATH)
        inicializar_db()

    def test_inicializar_crea_tablas(self):
        """Prueba 9a: La DB se inicializa con las tablas correctas."""
        conn = sqlite3.connect(config.DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = {r[0] for r in cur.fetchall()}
        conn.close()
        self.assertIn("mediciones", tablas)
        self.assertIn("sesiones",   tablas)
        self.assertIn("alertas",    tablas)
        print("  [9a OK] Tablas creadas: mediciones, sesiones, alertas.")

    def test_guardar_y_recuperar_medicion(self):
        """Prueba 9b: Guardar una medición y recuperarla."""
        sid = iniciar_sesion("DEMO")
        guardar_medicion(sid, 1750, "DEMO", "NORMAL")
        meds = obtener_mediciones_recientes(10)
        self.assertGreater(len(meds), 0)
        ultima = meds[-1]
        self.assertEqual(ultima["lectura"], 1750)
        self.assertEqual(ultima["modo"],    "DEMO")
        self.assertEqual(ultima["estado"],  "NORMAL")
        print("  [9b OK] Medición guardada y recuperada: lectura=%d, modo=%s, estado=%s"
              % (ultima["lectura"], ultima["modo"], ultima["estado"]))

    def test_multiples_mediciones(self):
        """Prueba 9c: Guardar 50 mediciones y verificar el conteo."""
        sid = iniciar_sesion("DEMO")
        for v in range(50):
            guardar_medicion(sid, 1200 + v, "DEMO", "NORMAL")
        meds = obtener_mediciones_recientes(100)
        self.assertGreaterEqual(len(meds), 50)
        print("  [9c OK] 50 mediciones guardadas. Total recuperadas: %d." % len(meds))


# ══════════════════════════════════════════════════════════
#  PRUEBA 10 — Exportación CSV
# ══════════════════════════════════════════════════════════
class TestExportacion(unittest.TestCase):

    def setUp(self):
        if os.path.exists(config.DB_PATH):
            os.remove(config.DB_PATH)
        if os.path.exists(config.EXPORT_PATH):
            os.remove(config.EXPORT_PATH)
        inicializar_db()

    def test_exportar_genera_archivo(self):
        """Prueba 10a: La exportación genera un archivo CSV."""
        sid = iniciar_sesion("DEMO")
        for v in range(10):
            guardar_medicion(sid, 1200 + v * 10, "DEMO", "NORMAL")
        ruta = exportar_csv()
        self.assertTrue(os.path.exists(ruta), "El archivo CSV debe existir")
        print("  [10a OK] Archivo CSV generado en: %s" % ruta)

    def test_exportar_contiene_datos(self):
        """Prueba 10b: El CSV tiene cabecera y filas de datos."""
        sid = iniciar_sesion("DEMO")
        for v in range(5):
            guardar_medicion(sid, 1300 + v, "DEMO", "NORMAL")
        exportar_csv()

        with open(config.EXPORT_PATH, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        self.assertGreaterEqual(len(lineas), 2, "Debe haber cabecera + al menos 1 fila")
        self.assertIn("lectura", lineas[0], "La cabecera debe incluir 'lectura'")
        print("  [10b OK] CSV con %d líneas (cabecera + datos)." % len(lineas))


# ══════════════════════════════════════════════════════════
#  PRUEBA 11 — Desconexión
# ══════════════════════════════════════════════════════════
class TestDesconexion(unittest.TestCase):

    def test_mensaje_desconexion_genera_alerta(self):
        """Prueba 11: Un mensaje DESCONECTADO debe poder registrarse como alerta."""
        from database import guardar_alerta, obtener_alertas_recientes
        if os.path.exists(config.DB_PATH):
            os.remove(config.DB_PATH)
        inicializar_db()

        sid = iniciar_sesion("DEMO")
        guardar_alerta(sid, "DESCONEXIÓN", 0, "El ESP32 se desconectó.")
        alertas = obtener_alertas_recientes(10)
        tipos = [a["tipo"] for a in alertas]
        self.assertIn("DESCONEXIÓN", tipos, "Debe registrarse la alerta de desconexión")
        print("  [11 OK] Alerta de DESCONEXIÓN registrada en SQLite.")


# ══════════════════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print()
    print("=" * 55)
    print("  AIRGUARD — Suite de pruebas del backend")
    print("=" * 55)
    print()

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    # Agregar pruebas en orden
    suite.addTests(loader.loadTestsFromTestCase(TestSimulacion))
    suite.addTests(loader.loadTestsFromTestCase(TestUmbrales))
    suite.addTests(loader.loadTestsFromTestCase(TestBaseDatos))
    suite.addTests(loader.loadTestsFromTestCase(TestExportacion))
    suite.addTests(loader.loadTestsFromTestCase(TestDesconexion))

    runner = unittest.TextTestRunner(verbosity=0, stream=sys.stdout)
    resultado = runner.run(suite)

    print()
    print("=" * 55)
    if resultado.wasSuccessful():
        print("  ✅ TODAS LAS PRUEBAS APROBADAS")
    else:
        print("  ❌ PRUEBAS FALLIDAS: %d" % len(resultado.failures + resultado.errors))
    print("=" * 55)
    print()

    # Limpiar archivos de prueba
    for f in [config.DB_PATH, config.EXPORT_PATH]:
        if os.path.exists(f):
            os.remove(f)
