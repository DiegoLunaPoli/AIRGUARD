
#define MODO_DEMO true

// ── Configuración del ADC ──────────────────────────────────
#define PIN_SENSOR     34    // GPIO34 — solo lectura (input only)
#define ADC_RESOLUCION 12    // 12 bits → valores de 0 a 4095
#define MUESTRAS       10    // Número de muestras para promedio

// ── Configuración de tiempo ────────────────────────────────
#define INTERVALO_MS   500   // Intervalo entre lecturas (ms)

// ── Variables globales ─────────────────────────────────────
unsigned long ultimaLectura = 0;

// Variables para simulación DEMO
float angulo_demo     = 0.0;
int   nivel_base_demo = 1200;   // Línea base simulada
bool  pico_activo     = false;
int   contador_pico   = 0;

// ── Prototipo de función ───────────────────────────────────
int leerSensorPromedio();
int generarDatoDemo();
void enviarJSON(const char* modo, int lectura, unsigned long ts);

// ===========================================================
//  SETUP
// ===========================================================
void setup() {
  // Iniciar comunicación serial
  Serial.begin(115200);

  // Esperar a que el puerto serial esté listo
  // (necesario en algunas placas ESP32)
  delay(500);

  // Configurar resolución del ADC
  analogReadResolution(ADC_RESOLUCION);

  // En modo sensor, configurar atenuación del ADC para
  // cubrir el rango 0–3.3 V correctamente
  #if !MODO_DEMO
    analogSetAttenuation(ADC_11db);  // Rango: 0 a ~3.3 V
    pinMode(PIN_SENSOR, INPUT);
  #endif
}

// ===========================================================
//  LOOP PRINCIPAL
// ===========================================================
void loop() {
  unsigned long ahora = millis();

  // Solo enviar al cumplir el intervalo
  if (ahora - ultimaLectura >= INTERVALO_MS) {
    ultimaLectura = ahora;

    int lectura = 0;

    #if MODO_DEMO
      lectura = generarDatoDemo();
      enviarJSON("DEMO", lectura, ahora);
    #else
      lectura = leerSensorPromedio();
      enviarJSON("SENSOR", lectura, ahora);
    #endif
  }
}

// ===========================================================
//  FUNCIÓN: Leer sensor con promedio de muestras
//  Solo se usa en MODO_SENSOR
// ===========================================================
int leerSensorPromedio() {
  long suma = 0;
  for (int i = 0; i < MUESTRAS; i++) {
    suma += analogRead(PIN_SENSOR);
    delay(2);  // Pequeña pausa entre muestras
  }
  return (int)(suma / MUESTRAS);
}

// ===========================================================
//  FUNCIÓN: Generador de datos simulados (MODO DEMO)
//
//  Simula:
//    - Una línea base estable alrededor de 1200
//    - Ruido aleatorio pequeño (±30)
//    - Picos periódicos que suben hasta ~2800–3200
//      para activar los umbrales de PRECAUCIÓN y ALERTA
// ===========================================================
int generarDatoDemo() {
  // Ruido base aleatorio
  int ruido = random(-30, 31);
  int valor = nivel_base_demo + ruido;

  // Generar un pico cada ~30 ciclos (15 segundos a 500ms)
  contador_pico++;
  if (contador_pico >= 30 && !pico_activo) {
    pico_activo  = true;
    contador_pico = 0;
  }

  // Durante el pico, incrementar gradualmente hasta ~3000
  if (pico_activo) {
    angulo_demo += 0.15;
    int amplitud = (int)(1600.0 * sin(angulo_demo));
    valor = nivel_base_demo + amplitud;

    // Limitar al rango del ADC de 12 bits (0–4095)
    if (valor < 0)    valor = 0;
    if (valor > 4095) valor = 4095;

    // Fin del pico (medio ciclo seno)
    if (angulo_demo >= 3.14159) {
      pico_activo   = false;
      angulo_demo   = 0.0;
    }
  }

  return valor;
}

// ===========================================================
//  FUNCIÓN: Enviar datos por Serial en formato JSON
//
//  Formato:
//    {"modo":"DEMO","lectura":1823,"timestamp":4521}
//
//  IMPORTANTE:
//    No agregar ningún Serial.print() de depuración fuera
//    de esta función. El backend Python espera JSON puro
//    por cada línea recibida.
// ===========================================================
void enviarJSON(const char* modo, int lectura, unsigned long ts) {
  Serial.print("{\"modo\":\"");
  Serial.print(modo);
  Serial.print("\",\"lectura\":");
  Serial.print(lectura);
  Serial.print(",\"timestamp\":");
  Serial.print(ts);
  Serial.println("}");
}
