"""
AIRGUARD — Validación visual del dashboard con Playwright.

Abre el dashboard en un navegador visible, espera a que lleguen
datos del ESP32, guarda una captura y un JSON con los valores
mostrados en pantalla. Mantiene la ventana abierta 10 minutos.
"""

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:5000"
BASE = Path(__file__).resolve().parent.parent
CAPTURA = BASE / "data" / "dashboard_playwright.png"
RESULTADO = BASE / "tests" / "resultado_playwright.json"


def texto(page, selector):
    try:
        return page.locator(selector).inner_text(timeout=3000).strip()
    except Exception:
        return None


with sync_playwright() as p:
    navegador = p.chromium.launch(headless=False, args=["--start-maximized"])
    contexto = navegador.new_context(viewport={"width": 1600, "height": 1000})
    pagina = contexto.new_page()
    pagina.goto(URL, wait_until="domcontentloaded", timeout=30000)
    pagina.wait_for_timeout(7000)  # Tiempo para que lleguen lecturas del ESP32

    datos = {
        "titulo": pagina.title(),
        "url": pagina.url,
        "conexion": texto(pagina, "#pill-conexion .pill-texto"),
        "modo": texto(pagina, "#modo-badge"),
        "estado": texto(pagina, "#estado-label"),
        "banner_alarma_visible": pagina.locator("#banner-alarma").is_visible(),
        "ultima_alerta": texto(pagina, "#ultima-alerta"),
        "lectura": texto(pagina, "#valor-adc-numero"),
        "porcentaje": texto(pagina, "#valor-porcentaje-numero"),
        "umbrales_resumen": texto(pagina, "#umbrales-resumen"),
        "variacion": texto(pagina, "#valor-variacion"),
        "min": texto(pagina, "#stat-min"),
        "max": texto(pagina, "#stat-max"),
        "promedio": texto(pagina, "#stat-prom"),
        "linea_base": texto(pagina, "#stat-linea"),
        "contador": texto(pagina, "#stat-contador"),
        "duracion": texto(pagina, "#stat-duracion"),
        "umbral_precaucion": pagina.locator("#inp-precaucion").input_value(),
        "umbral_alerta": pagina.locator("#inp-alerta").input_value(),
        "filas_historial": pagina.locator("#tabla-historial tr").count(),
    }

    CAPTURA.parent.mkdir(parents=True, exist_ok=True)
    pagina.screenshot(path=str(CAPTURA), full_page=True)
    RESULTADO.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(datos, indent=2, ensure_ascii=False))
    print("CAPTURA:", CAPTURA)

    # Mantener la ventana abierta para que el usuario pueda verla en vivo.
    time.sleep(600)
    navegador.close()
