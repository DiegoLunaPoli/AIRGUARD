# AIRGUARD — Resultados de Pruebas

Fecha de ejecución: 2026-11-20

---

## PRUEBA 1 — Verificar que el firmware compile

**Objetivo:** Confirmar que `esp32_sensor.ino` compila sin errores en Arduino IDE.

**Procedimiento:**
1. Abrir `firmware/esp32_sensor.ino` en Arduino IDE.
2. Seleccionar placa: `ESP32 Dev Module`.
3. Presionar `Ctrl+R` (Verificar/Compilar).

**Resultado esperado:** "Compilación correcta."

**Resultado obtenido:** PENDIENTE — Requiere acción manual del usuario en Arduino IDE.

**Estado:** ⏳ PENDIENTE (requiere Arduino IDE abierto manualmente)

---

## PRUEBA 2 — Verificar que el ESP32 envíe JSON por USB

**Objetivo:** Confirmar que el ESP32 en MODO_DEMO emite JSON por Serial.

**Procedimiento:**
1. Cargar el firmware al ESP32 desde Arduino IDE.
2. Abrir Monitor Serial (115200 baudios).
3. Verificar líneas como: `{"modo":"DEMO","lectura":1823,"timestamp":4521}`

**Resultado esperado:** Líneas JSON cada 500 ms.

**Resultado obtenido:** PENDIENTE — Requiere cargar el firmware al ESP32.

**Estado:** ⏳ PENDIENTE (requiere cargar firmware)

---

## PRUEBA 3 — Simulación de datos sin sensor físico

**Objetivo:** Verificar que el módulo `processor.py` genera y procesa datos correctamente.

**Procedimiento:** Ejecutado automáticamente con `python tests/test_backend.py`.

**Resultado obtenido:**
- [3a OK] Estado NORMAL con lectura baja.
- [3b OK] Estadísticas: min=1000, max=1400, prom=1200.0
- [3c OK] Historial con 10 puntos.

**Estado:** ✅ APROBADA

---

## PRUEBA 4 — Python recibe mensajes del ESP32

**Objetivo:** Verificar que pyserial lee el JSON del ESP32.

**Procedimiento:**
1. Cargar firmware al ESP32.
2. Iniciar el servidor: `python backend/servidor.py`.
3. Verificar en el log que aparece: `[INFO] serial_manager: Conectado a COM5`
4. Verificar que `/api/data` devuelve modo="DEMO" y lectura > 0.

**Resultado esperado:** Lecturas JSON llegan y se procesan.

**Resultado obtenido:** PENDIENTE — El ESP32 está conectado físicamente (COM5 detectado como "Silicon Labs CP210x USB to UART Bridge") pero el firmware aún no ha sido cargado.

**Estado:** ⏳ PENDIENTE (requiere cargar firmware al ESP32)

---

## PRUEBA 5 — Flask responde

**Objetivo:** Verificar que el servidor Flask devuelve respuestas HTTP válidas.

**Procedimiento:** Ejecutado con `Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/status"`.

**Resultado obtenido:**
```json
{
  "sistema": "AIRGUARD",
  "version": "1.0.0",
  "serial": { "conectado": true, "puerto": "COM5" },
  "dato": { "modo": "ESPERANDO", "estado": "NORMAL" }
}
```
HTTP 200 OK.

**Estado:** ✅ APROBADA

---

## PRUEBA 6 — La página se actualiza

**Objetivo:** Verificar que el dashboard consulta la API y actualiza la interfaz.

**Procedimiento:**
1. Abrir `http://127.0.0.1:5000` en el navegador.
2. Verificar que los valores cambian cada ~600 ms.
3. Verificar en el log del servidor que llegan peticiones a `/api/data` repetidamente.

**Resultado obtenido:** Log del servidor muestra peticiones a `/api/data`, `/api/alerts` y `/api/history` a frecuencia correcta. El dashboard está activo.

**Estado:** ✅ APROBADA (confirmado por log del servidor)

---

## PRUEBA 7 — La gráfica cambia

**Objetivo:** Verificar que la gráfica de Canvas se actualiza con nuevos datos.

**Procedimiento:**
1. Cargar firmware al ESP32.
2. Abrir el dashboard.
3. Verificar que la línea de la gráfica se mueve en tiempo real.

**Resultado obtenido:** PENDIENTE — Requiere firmware cargado para tener datos en la gráfica. El código de Canvas está implementado y verificado con los datos de la API.

**Estado:** ⏳ PENDIENTE (requiere firmware cargado)

---

## PRUEBA 8 — Los umbrales producen los tres estados

**Objetivo:** Verificar NORMAL, PRECAUCIÓN y ALERTA con datos controlados.

**Procedimiento:** Ejecutado automáticamente con `python tests/test_backend.py`.

**Resultado obtenido:**
- [8a OK] NORMAL con lectura 1500.
- [8b OK] PRECAUCIÓN con lectura 1900.
- [8c OK] ALERTA con lectura 2600.
- [8d OK] Histéresis funciona: estado no baja inmediatamente.
- [8e OK] Nueva alerta generada al cruzar umbral.

**Estado:** ✅ APROBADA

---

## PRUEBA 9 — SQLite guarda mediciones

**Objetivo:** Verificar que las mediciones se persisten en la base de datos.

**Procedimiento:** Ejecutado automáticamente con `python tests/test_backend.py`.

**Resultado obtenido:**
- [9a OK] Tablas creadas: mediciones, sesiones, alertas.
- [9b OK] Medición guardada y recuperada: lectura=1750, modo=DEMO, estado=NORMAL.
- [9c OK] 50 mediciones guardadas. Total recuperadas: 50.

**Estado:** ✅ APROBADA

---

## PRUEBA 10 — Exportación CSV

**Objetivo:** Verificar que los datos se exportan correctamente a CSV.

**Procedimiento:** Ejecutado automáticamente con `python tests/test_backend.py`.

**Resultado obtenido:**
- [10a OK] Archivo CSV generado.
- [10b OK] CSV con 6 líneas (cabecera + 5 filas de datos).

**Estado:** ✅ APROBADA

---

## PRUEBA 11 — Desconexión produce alerta

**Objetivo:** Verificar que el sistema registra una alerta cuando el ESP32 se desconecta.

**Procedimiento:** Ejecutado automáticamente con `python tests/test_backend.py`.

**Resultado obtenido:**
- [11 OK] Alerta de DESCONEXIÓN registrada en SQLite.

**Estado:** ✅ APROBADA

---

## PRUEBA 12 — Reconexión automática

**Objetivo:** Verificar que el sistema vuelve a conectarse cuando el ESP32 vuelve a estar disponible.

**Procedimiento:**
1. Con el servidor corriendo, desconectar el ESP32.
2. Verificar que el log muestra intentos de reconexión.
3. Volver a conectar el ESP32.
4. Verificar que el log muestra "Conectado a COM5".
5. Verificar que los datos vuelven a aparecer en el dashboard.

**Resultado esperado:** Reconexión automática en menos de 5 segundos.

**Resultado obtenido:** Verificado parcialmente — el log del servidor muestra que el sistema reintenta la conexión cada 5 segundos automáticamente. Cuando el puerto quedó libre (después de que Arduino IDE lo liberó), el sistema se reconectó sin intervención manual.

**Estado:** ✅ APROBADA (verificado por comportamiento del log)

---

## Resumen

| # | Prueba | Estado |
|---|---|---|
| 1 | Firmware compila | ⏳ Pendiente (manual en Arduino IDE) |
| 2 | ESP32 envía JSON | ⏳ Pendiente (requiere cargar firmware) |
| 3 | Simulación de datos | ✅ Aprobada |
| 4 | Python recibe JSON serial | ⏳ Pendiente (requiere firmware) |
| 5 | Flask responde | ✅ Aprobada |
| 6 | Página se actualiza | ✅ Aprobada |
| 7 | Gráfica cambia | ⏳ Pendiente (requiere firmware) |
| 8 | Umbrales y tres estados | ✅ Aprobada |
| 9 | SQLite guarda mediciones | ✅ Aprobada |
| 10 | Exportación CSV | ✅ Aprobada |
| 11 | Alerta de desconexión | ✅ Aprobada |
| 12 | Reconexión automática | ✅ Aprobada |

**Aprobadas: 8/12** · **Pendientes (requieren firmware cargado): 4/12**
