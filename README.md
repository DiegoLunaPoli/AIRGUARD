# AIRGUARD — Sistema Experimental de Monitoreo Ambiental

**Versión:** 1.0.0  
**Tipo:** Prototipo universitario  
**Plataforma:** Windows (local, sin internet)

---

## Descripción del proyecto

AIRGUARD es un prototipo experimental que recopila la respuesta analógica del sensor MQ-2 mediante un ESP32, transmite los datos a una computadora por USB y los presenta en un dashboard web local con gráficas en tiempo real, estadísticas, sistema de alertas e historial persistente.

> **Aviso importante:** Este sistema es experimental y educativo. Los datos mostrados **no** constituyen mediciones certificadas de calidad del aire. El sensor MQ-2 entrega una respuesta analógica general ante múltiples sustancias y no permite identificar gases individuales ni concentraciones sin calibración específica.

---

## Objetivo general

Demostrar la integración de hardware embebido (ESP32 + MQ-2), comunicación serial USB, backend Python y visualización web en un sistema de monitoreo ambiental local.

## Objetivos específicos

1. Recopilar la respuesta analógica del sensor MQ-2 mediante el ADC del ESP32.
2. Transmitir los datos al computador mediante protocolo serial USB en formato JSON.
3. Procesar y almacenar las lecturas en SQLite mediante un backend Python/Flask.
4. Presentar los datos en un dashboard web profesional con gráficas, estadísticas y alertas.
5. Implementar un modo DEMO funcional para demostración sin sensor físico.

---

## Componentes de hardware

| Componente | Descripción |
|---|---|
| ESP32 DevKit | Microcontrolador con ADC de 12 bits |
| Sensor MQ-2 Flying Fish | Sensor semiconductor de gases |
| Cable USB | Comunicación y alimentación |
| Protoboard + cables Dupont | Conexiones del circuito |
| Computador Windows | Servidor local y dashboard |

---

## Arquitectura del sistema

```
MQ-2
 │
 ▼
ESP32 (firmware Arduino C++)
 │  USB / Serial 115200 bps  JSON
 ▼
Python / Flask (backend)
 │  API REST HTTP local
 ▼
Dashboard web (HTML + CSS + JS)
http://127.0.0.1:5000
```

---

## Estructura de archivos

```
AIRGUARD/
├── firmware/
│   └── esp32_sensor.ino      ← Firmware del ESP32
├── backend/
│   ├── servidor.py           ← Servidor Flask principal
│   ├── serial_manager.py     ← Comunicación serial (hilo)
│   ├── database.py           ← SQLite
│   ├── processor.py          ← Procesamiento y estadísticas
│   ├── config.py             ← Configuración central
│   └── requirements.txt      ← Dependencias Python
├── frontend/
│   ├── index.html            ← Dashboard principal
│   ├── css/styles.css        ← Estilos
│   └── js/app.js             ← Lógica del dashboard
├── data/                     ← Base de datos SQLite y CSV
├── tests/                    ← Scripts de prueba
├── iniciar_airguard.bat      ← Inicio con doble clic
└── README.md
```

---

## Instalación

### Requisitos previos

- Python 3.8 o superior (con `pip`)
- Arduino IDE 2.x con ESP32 Arduino Core instalado

### Pasos

1. **Verificar Python:**
   ```
   python --version
   ```

2. **Instalar dependencias Python:**
   ```
   pip install flask pyserial
   ```

3. **Cargar firmware al ESP32:**
   - Abrir `firmware/esp32_sensor.ino` en Arduino IDE
   - Seleccionar placa: `ESP32 Dev Module`
   - Seleccionar puerto: `COM5` (o el que aparezca)
   - Compilar y subir
   - Por defecto el firmware inicia en **MODO DEMO** (sin sensor)

4. **Iniciar el sistema:**
   - Doble clic en `iniciar_airguard.bat`
   - O desde terminal: `python backend/servidor.py`

5. **Abrir el dashboard:**
   - Navegar a `http://127.0.0.1:5000`

---

## Modos de operación del firmware

### MODO DEMO (predeterminado)

```cpp
#define MODO_DEMO true
```

Genera datos simulados con línea base estable y picos periódicos para activar los tres estados (NORMAL, PRECAUCIÓN, ALERTA). **No requiere sensor conectado.** Usar siempre durante desarrollo y demostración mientras no se verifique el circuito.

### MODO SENSOR

```cpp
#define MODO_DEMO false
```

Lee el ADC en GPIO34. **Solo usar cuando el divisor de tensión esté instalado y verificado eléctricamente.**

---

## Conexión eléctrica — ADVERTENCIA DE SEGURIDAD

El ESP32 opera a 3.3 V. El pin GPIO34 acepta como máximo 3.3 V.

El módulo MQ-2 Flying Fish alimentado a 5 V (pin VIN del ESP32) puede producir hasta 5 V en su salida analógica (A0). Conectar directamente A0 a GPIO34 **puede dañar el ESP32 de forma permanente**.

### Circuito seguro con divisor de tensión

```
VIN (5V) ──────────────────── VCC del MQ-2
GND ────────────────────────── GND del MQ-2

A0 del MQ-2 ─── R1 (10kΩ) ─── Nodo ─── GPIO34 del ESP32
                                 │
                               R2 (20kΩ)
                                 │
                                GND
```

Con R1=10kΩ y R2=20kΩ, una señal de 5V queda reducida a 3.33V en GPIO34. Las resistencias deben instalarse sobre la protoboard antes de conectar el sensor y cambiar a MODO_SENSOR.

**El sistema funciona completamente en MODO DEMO sin necesidad de conectar el sensor.**

---

## API REST

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Dashboard web |
| `/api/status` | GET | Estado del sistema |
| `/api/data` | GET | Lectura actual + gráfica |
| `/api/history` | GET | Mediciones y sesiones |
| `/api/statistics` | GET | Estadísticas de sesión |
| `/api/alerts` | GET | Alertas recientes |
| `/api/ports` | GET | Puertos COM disponibles |
| `/api/set_port` | POST | Cambiar puerto serial |
| `/api/set_thresholds` | POST | Cambiar umbrales |
| `/api/export` | GET | Descargar CSV |
| `/api/clear_demo` | POST | Limpiar datos DEMO |
| `/api/reset_baseline` | POST | Reiniciar línea base |

---

## Aclaraciones técnicas sobre el sensor MQ-2

| Término | Definición en este prototipo |
|---|---|
| **Sensibilidad del sensor** | El MQ-2 cambia su resistencia interna ante GLP, propano, metano, humo y alcohol. No distingue cuál de ellos está presente. |
| **Respuesta del sensor** | El valor ADC que entrega el ESP32 (0–4095), proporcional a la conductividad del elemento sensor. |
| **Detección de cambios** | El sistema detecta variaciones respecto a la línea base, no la presencia de un gas específico. |
| **Identificación de gases** | **No es posible** con este sensor sin calibración multivariable y múltiples sensores. |
| **Concentración en ppm** | **No disponible** en este prototipo. Requiere calibración con gas de referencia conocido, medición de R₀ y curva Rs/R₀. |
| **Calidad del aire** | Este sistema **no** mide ni certifica calidad del aire. Es un prototipo educativo. |

---

## Estados experimentales

Los tres estados del sistema son **umbrales experimentales configurables**, no parámetros normativos:

| Estado | Condición | Significado |
|---|---|---|
| **NORMAL** | Lectura < umbral precaución | Respuesta cercana a la línea base |
| **PRECAUCIÓN** | Umbral precaución ≤ lectura < umbral alerta | Variación significativa detectada |
| **ALERTA** | Lectura ≥ umbral alerta | Variación alta de la respuesta del sensor |

Los umbrales por defecto son 1800 (precaución) y 2500 (alerta) en unidades ADC. Se pueden ajustar desde el dashboard.

---

## Limitaciones del prototipo

1. No identifica gases individualmente.
2. No calcula ppm sin calibración previa.
3. No certifica calidad del aire.
4. El sensor MQ-2 requiere entre 24 y 48 horas de calentamiento para estabilizarse.
5. La respuesta del sensor varía con temperatura y humedad ambiental.
6. Los umbrales son experimentales y deben ajustarse para cada entorno.

---

## Trabajo futuro

- Implementar calibración con gas de referencia y cálculo de R₀.
- Agregar sensor de temperatura/humedad (DHT22) para compensación.
- Exportar datos en formato JSON además de CSV.
- Agregar autenticación básica al servidor.
- Implementar notificaciones por correo o SMS (modo en línea).
- Evaluar migración a sensor MQ-135 para calidad de aire general.

---

## Pruebas realizadas

Ver archivo `tests/resultados_pruebas.md` para el detalle completo.

---

*AIRGUARD — Prototipo universitario. Solo uso educativo y demostrativo.*
