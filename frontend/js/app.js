/**
 * AIRGUARD — Aplicación web del dashboard
 * Consulta la API Flask cada 500 ms y actualiza la interfaz.
 */

"use strict";

// ── Configuración ────────────────────────────────────────
const API_BASE      = "http://127.0.0.1:5000";
const INTERVALO_MS  = 600;   // Intervalo de polling
const PUNTOS_GRAFICA = 120;  // Puntos visibles en la gráfica

// ── Estado local del dashboard ───────────────────────────
let estadoApp = {
  conectado:        false,
  modo:             "ESPERANDO",
  estado:           "NORMAL",
  lectura:          0,
  linea_base:       1200,
  umbral_precaucion: 1800,
  umbral_alerta:    2500,
  contador:         0,
  alertas_vistas:   0,
};

// ── Canvas / Gráfica ─────────────────────────────────────
let canvas, ctx;
let puntosGrafica = [];   // Array de {ts, lectura}

// ── Inicialización ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  inicializarCanvas();
  cargarPuertos();
  cargarHistorial();
  cargarAlertas();

  // Polling principal
  setInterval(actualizarDashboard, INTERVALO_MS);
  actualizarDashboard();

  // Polling secundario más lento para alertas e historial
  setInterval(cargarAlertas,   3000);
  setInterval(cargarHistorial, 10000);

  // Eventos de botones
  document.getElementById("btn-aplicar-umbrales")
    .addEventListener("click", aplicarUmbrales);
  document.getElementById("btn-exportar-csv")
    .addEventListener("click", exportarCSV);
  document.getElementById("btn-limpiar-demo")
    .addEventListener("click", limpiarDemo);
  document.getElementById("btn-reset-base")
    .addEventListener("click", resetearBase);
  document.getElementById("btn-cambiar-puerto")
    .addEventListener("click", cambiarPuerto);
  document.getElementById("btn-refresh-puertos")
    .addEventListener("click", cargarPuertos);
});

// ═══════════════════════════════════════════════════════════
//  ACTUALIZACIÓN PRINCIPAL
// ═══════════════════════════════════════════════════════════
async function actualizarDashboard() {
  try {
    const res  = await fetch(`${API_BASE}/api/data`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();

    const dato  = json.dato;
    const stats = json.estadisticas;
    const umb   = json.umbrales;
    const graf  = json.grafica;

    // Actualizar estado local
    estadoApp.conectado         = dato.conectado;
    estadoApp.modo              = dato.modo;
    estadoApp.estado            = dato.estado;
    estadoApp.lectura           = dato.lectura;
    estadoApp.linea_base        = umb.linea_base;
    estadoApp.umbral_precaucion = umb.precaucion;
    estadoApp.umbral_alerta     = umb.alerta;
    estadoApp.contador          = stats.contador;

    // ── Header ───────────────────────────────────────────
    actualizarHeader(dato);

    // ── Estado ambiental ─────────────────────────────────
    actualizarEstado(dato.estado);

    // ── Valor ADC ────────────────────────────────────────
    actualizarValorADC(dato);

    // ── Estadísticas ─────────────────────────────────────
    actualizarEstadisticas(stats, dato);

    // ── Gráfica ──────────────────────────────────────────
    if (graf && graf.length > 0) {
      puntosGrafica = graf;
      dibujarGrafica();
    }

    // ── Umbrales (inputs, sin sobreescribir lo que el usuario esté editando) ──
    const inpPrec = document.getElementById("inp-precaucion");
    const inpAlrt = document.getElementById("inp-alerta");
    if (document.activeElement !== inpPrec) inpPrec.value = umb.precaucion;
    if (document.activeElement !== inpAlrt) inpAlrt.value = umb.alerta;

    // Actualizar hora
    document.getElementById("ultima-actualizacion").textContent =
      new Date().toLocaleTimeString("es-ES");

  } catch (err) {
    // No se puede llegar al servidor
    marcarDesconectado();
  }
}

// ═══════════════════════════════════════════════════════════
//  ACTUALIZACIÓN DE UI
// ═══════════════════════════════════════════════════════════
function actualizarHeader(dato) {
  const pill = document.getElementById("pill-conexion");
  const led  = document.getElementById("led-conexion");
  const modo = document.getElementById("modo-badge");

  const conectado = dato.conectado && dato.modo !== "DESCONECTADO" && dato.modo !== "ESPERANDO";

  if (conectado) {
    pill.className = "status-pill conectado";
    pill.querySelector(".pill-texto").textContent = "ESP32 CONECTADO";
    led.className  = "led parpadeo";
  } else if (dato.modo === "DESCONECTADO") {
    pill.className = "status-pill desconectado";
    pill.querySelector(".pill-texto").textContent = "ESP32 DESCONECTADO";
    led.className  = "led";
  } else {
    pill.className = "status-pill esperando";
    pill.querySelector(".pill-texto").textContent = "ESPERANDO ESP32";
    led.className  = "led parpadeo";
  }

  modo.className   = `modo-badge ${dato.modo}`;
  modo.textContent = dato.modo || "ESPERANDO";
}

function actualizarEstado(estado) {
  const circulo = document.getElementById("estado-circulo");
  const icono   = document.getElementById("estado-icono");
  const texto   = document.getElementById("estado-label");
  const desc    = document.getElementById("estado-descripcion");

  const cfg = {
    "NORMAL":    { icono: "✅", label: "NORMAL",    desc: "Respuesta del sensor cercana a la línea base. Sin variaciones significativas detectadas." },
    "PRECAUCIÓN":{ icono: "⚠️", label: "PRECAUCIÓN", desc: "Variación significativa respecto a la línea base. Monitorear evolución." },
    "ALERTA":    { icono: "🚨", label: "ALERTA",    desc: "Se superó el umbral experimental alto. Variación importante de la respuesta del sensor." },
  };

  const c = cfg[estado] || cfg["NORMAL"];
  circulo.className     = `estado-circulo ${estado}`;
  icono.textContent     = c.icono;
  texto.textContent     = c.label;
  desc.textContent      = c.desc;

  // Color del body según estado (efecto sutil)
  document.body.style.setProperty("--estado-glow",
    estado === "ALERTA"     ? "rgba(239,68,68,0.03)"    :
    estado === "PRECAUCIÓN" ? "rgba(245,158,11,0.02)"   : "transparent");
}

function actualizarValorADC(dato) {
  const numEl  = document.getElementById("valor-adc-numero");
  const varEl  = document.getElementById("valor-variacion");
  const barraEl= document.getElementById("barra-adc-relleno");
  const umbPEl = document.getElementById("barra-umbral-precaucion");
  const umbAEl = document.getElementById("barra-umbral-alerta");

  numEl.textContent  = dato.lectura || 0;
  numEl.className    = `valor-numero ${dato.estado || "NORMAL"}`;

  const pct = dato.variacion_pct || 0;
  varEl.textContent  = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% respecto a línea base`;
  varEl.className    = `valor-variacion ${pct >= 0 ? "positivo" : "negativo"}`;

  // Barra de progreso (0–4095)
  const porcentaje = Math.min((dato.lectura / 4095) * 100, 100);
  barraEl.style.width = `${porcentaje}%`;

  // Color de la barra según estado
  barraEl.style.background =
    dato.estado === "ALERTA"     ? "linear-gradient(90deg, #ef4444, #f97316)" :
    dato.estado === "PRECAUCIÓN" ? "linear-gradient(90deg, #f59e0b, #fbbf24)" :
                                   "linear-gradient(90deg, #10b981, #00d4ff)";

  // Marcadores de umbral sobre la barra
  const pctPrec = (estadoApp.umbral_precaucion / 4095) * 100;
  const pctAlrt = (estadoApp.umbral_alerta / 4095) * 100;
  umbPEl.style.left = `${pctPrec}%`;
  umbAEl.style.left = `${pctAlrt}%`;
}

function actualizarEstadisticas(stats, dato) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  set("stat-actual",    dato.lectura || 0);
  set("stat-min",       stats.minimo || 0);
  set("stat-max",       stats.maximo || 0);
  set("stat-prom",      stats.promedio || 0);
  set("stat-linea",     stats.linea_base || 0);
  set("stat-contador",  stats.contador || 0);
  set("stat-duracion",  formatearDuracion(stats.duracion_s || 0));
}

function marcarDesconectado() {
  const pill = document.getElementById("pill-conexion");
  if (pill) {
    pill.className = "status-pill desconectado";
    pill.querySelector(".pill-texto").textContent = "SERVIDOR NO DISPONIBLE";
  }
}

// ═══════════════════════════════════════════════════════════
//  GRÁFICA (Canvas 2D nativo)
// ═══════════════════════════════════════════════════════════
function inicializarCanvas() {
  canvas = document.getElementById("grafica-principal");
  if (!canvas) return;
  ctx    = canvas.getContext("2d");
  ajustarCanvas();
  window.addEventListener("resize", () => { ajustarCanvas(); dibujarGrafica(); });
}

function ajustarCanvas() {
  if (!canvas) return;
  const rect  = canvas.parentElement.getBoundingClientRect();
  canvas.width  = rect.width - 32;
  canvas.height = 220;
}

function dibujarGrafica() {
  if (!ctx || !canvas || puntosGrafica.length < 2) return;

  const W = canvas.width;
  const H = canvas.height;
  const PAD_L = 50, PAD_R = 16, PAD_T = 16, PAD_B = 30;
  const aW = W - PAD_L - PAD_R;
  const aH = H - PAD_T - PAD_B;

  ctx.clearRect(0, 0, W, H);

  // Fondo
  ctx.fillStyle = "#111827";
  ctx.fillRect(0, 0, W, H);

  const pts = puntosGrafica.slice(-PUNTOS_GRAFICA);
  const nPts = pts.length;
  if (nPts < 2) return;

  const yMax = 4095;
  const yMin = 0;

  const xDe = (i) => PAD_L + (i / (nPts - 1)) * aW;
  const yDe = (v) => PAD_T + aH - ((v - yMin) / (yMax - yMin)) * aH;

  // Cuadrícula horizontal
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth   = 1;
  for (let v = 0; v <= 4095; v += 1024) {
    const y = yDe(v);
    ctx.beginPath();
    ctx.moveTo(PAD_L, y);
    ctx.lineTo(PAD_L + aW, y);
    ctx.stroke();
  }

  // ── Línea base ───────────────────────────────────────
  const yBase = yDe(estadoApp.linea_base);
  ctx.strokeStyle = "rgba(16,185,129,0.6)";
  ctx.lineWidth   = 1;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.moveTo(PAD_L, yBase);
  ctx.lineTo(PAD_L + aW, yBase);
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Umbral precaución ────────────────────────────────
  const yPrec = yDe(estadoApp.umbral_precaucion);
  ctx.strokeStyle = "rgba(245,158,11,0.6)";
  ctx.lineWidth   = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(PAD_L, yPrec);
  ctx.lineTo(PAD_L + aW, yPrec);
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Umbral alerta ────────────────────────────────────
  const yAlrt = yDe(estadoApp.umbral_alerta);
  ctx.strokeStyle = "rgba(239,68,68,0.6)";
  ctx.lineWidth   = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(PAD_L, yAlrt);
  ctx.lineTo(PAD_L + aW, yAlrt);
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Área relleno ─────────────────────────────────────
  const grad = ctx.createLinearGradient(0, PAD_T, 0, PAD_T + aH);
  grad.addColorStop(0,   "rgba(0,212,255,0.25)");
  grad.addColorStop(1,   "rgba(0,212,255,0.0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(xDe(0), yDe(pts[0].lectura));
  for (let i = 1; i < nPts; i++) ctx.lineTo(xDe(i), yDe(pts[i].lectura));
  ctx.lineTo(xDe(nPts - 1), PAD_T + aH);
  ctx.lineTo(xDe(0),        PAD_T + aH);
  ctx.closePath();
  ctx.fill();

  // ── Línea de datos ───────────────────────────────────
  ctx.strokeStyle = "#00d4ff";
  ctx.lineWidth   = 2;
  ctx.lineJoin    = "round";
  ctx.beginPath();
  ctx.moveTo(xDe(0), yDe(pts[0].lectura));
  for (let i = 1; i < nPts; i++) {
    ctx.lineTo(xDe(i), yDe(pts[i].lectura));
  }
  ctx.stroke();

  // ── Etiquetas eje Y ───────────────────────────────────
  ctx.fillStyle = "rgba(148,163,184,0.7)";
  ctx.font      = "10px Consolas, monospace";
  ctx.textAlign = "right";
  for (let v = 0; v <= 4095; v += 1024) {
    ctx.fillText(v, PAD_L - 6, yDe(v) + 3);
  }

  // ── Etiquetas de referencia ───────────────────────────
  ctx.textAlign = "left";
  ctx.font      = "9px Segoe UI, sans-serif";

  ctx.fillStyle = "rgba(16,185,129,0.8)";
  ctx.fillText(`BASE ${Math.round(estadoApp.linea_base)}`, PAD_L + 4, yBase - 3);

  ctx.fillStyle = "rgba(245,158,11,0.8)";
  ctx.fillText(`PREC ${estadoApp.umbral_precaucion}`, PAD_L + 4, yPrec - 3);

  ctx.fillStyle = "rgba(239,68,68,0.8)";
  ctx.fillText(`ALERT ${estadoApp.umbral_alerta}`, PAD_L + 4, yAlrt - 3);
}

// ═══════════════════════════════════════════════════════════
//  ALERTAS
// ═══════════════════════════════════════════════════════════
async function cargarAlertas() {
  try {
    const res  = await fetch(`${API_BASE}/api/alerts?limite=20`);
    const json = await res.json();
    renderizarAlertas(json.alertas || []);
  } catch (_) {}
}

function renderizarAlertas(alertas) {
  const lista = document.getElementById("alertas-lista");
  if (!lista) return;
  if (!alertas.length) {
    lista.innerHTML = `<div style="color:var(--text-muted);font-size:12px;padding:12px;">Sin alertas registradas.</div>`;
    return;
  }

  const iconos = { "ALERTA": "🚨", "PRECAUCIÓN": "⚠️", "NORMAL": "✅", "DESCONEXIÓN": "🔌" };

  lista.innerHTML = alertas.map(a => `
    <div class="alerta-item ${a.tipo}">
      <span class="alerta-icono">${iconos[a.tipo] || "ℹ️"}</span>
      <div class="alerta-contenido">
        <div class="alerta-tipo">${a.tipo}</div>
        <div class="alerta-msg">${a.mensaje || ""} ${a.valor ? `— Valor: ${a.valor}` : ""}</div>
        <div class="alerta-ts">${formatearTimestamp(a.timestamp)}</div>
      </div>
    </div>
  `).join("");
}

// ═══════════════════════════════════════════════════════════
//  HISTORIAL
// ═══════════════════════════════════════════════════════════
async function cargarHistorial() {
  try {
    const res  = await fetch(`${API_BASE}/api/history?limite=50`);
    const json = await res.json();
    renderizarHistorial(json.mediciones || []);
    renderizarSesiones(json.sesiones || []);
  } catch (_) {}
}

function renderizarHistorial(meds) {
  const tabla = document.getElementById("tabla-historial");
  if (!tabla) return;
  if (!meds.length) {
    tabla.innerHTML = `<tr><td colspan="4" style="color:var(--text-muted);text-align:center;padding:16px;">Sin mediciones en la base de datos.</td></tr>`;
    return;
  }

  tabla.innerHTML = meds.slice().reverse().map(m => `
    <tr>
      <td style="font-family:var(--fuente-mono)">${formatearTimestamp(m.timestamp)}</td>
      <td style="font-family:var(--fuente-mono);color:var(--color-cian)">${m.lectura}</td>
      <td><span class="badge-estado ${m.estado}">${m.estado}</span></td>
      <td><span class="modo-badge ${m.modo}" style="font-size:10px">${m.modo}</span></td>
    </tr>
  `).join("");
}

function renderizarSesiones(sesiones) {
  const tabla = document.getElementById("tabla-sesiones");
  if (!tabla || !sesiones.length) return;
  tabla.innerHTML = sesiones.map(s => `
    <tr>
      <td style="font-family:var(--fuente-mono)">${s.id}</td>
      <td style="font-family:var(--fuente-mono)">${formatearTimestamp(s.inicio)}</td>
      <td style="font-family:var(--fuente-mono)">${s.fin ? formatearTimestamp(s.fin) : "Activa"}</td>
      <td><span class="modo-badge ${s.modo}" style="font-size:10px">${s.modo}</span></td>
      <td style="font-family:var(--fuente-mono)">${s.total_meds}</td>
    </tr>
  `).join("");
}

// ═══════════════════════════════════════════════════════════
//  PUERTOS SERIAL
// ═══════════════════════════════════════════════════════════
async function cargarPuertos() {
  try {
    const res  = await fetch(`${API_BASE}/api/ports`);
    const json = await res.json();
    const sel  = document.getElementById("select-puerto");
    if (!sel) return;

    sel.innerHTML = json.puertos.map(p =>
      `<option value="${p.puerto}">${p.puerto} — ${p.descripcion}</option>`
    ).join("") || `<option value="">Sin puertos detectados</option>`;

    // Marcar el puerto activo si ya está en la lista
    mostrarToast(`${json.puertos.length} puerto(s) detectado(s)`, "info");
  } catch (_) {}
}

async function cambiarPuerto() {
  const sel = document.getElementById("select-puerto");
  if (!sel || !sel.value) return;
  try {
    await fetch(`${API_BASE}/api/set_port`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ puerto: sel.value })
    });
    mostrarToast(`Puerto cambiado a ${sel.value}`, "ok");
  } catch (_) { mostrarToast("No se pudo cambiar el puerto", "error"); }
}

// ═══════════════════════════════════════════════════════════
//  ACCIONES
// ═══════════════════════════════════════════════════════════
async function aplicarUmbrales() {
  const prec = parseInt(document.getElementById("inp-precaucion").value);
  const alrt = parseInt(document.getElementById("inp-alerta").value);

  if (isNaN(prec) || isNaN(alrt) || prec <= 0 || alrt <= prec || alrt > 4095) {
    mostrarToast("Valores inválidos. Precaución debe ser menor que Alerta (máx 4095).", "warning");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/set_thresholds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ precaucion: prec, alerta: alrt })
    });
    const json = await res.json();
    if (json.ok) {
      estadoApp.umbral_precaucion = prec;
      estadoApp.umbral_alerta     = alrt;
      mostrarToast(`Umbrales actualizados: PRECAUCIÓN=${prec}, ALERTA=${alrt}`, "ok");
      dibujarGrafica();
    } else {
      mostrarToast("Error: " + (json.error || "desconocido"), "error");
    }
  } catch (_) { mostrarToast("No se pudo conectar al servidor", "error"); }
}

function exportarCSV() {
  window.location.href = `${API_BASE}/api/export`;
  mostrarToast("Descargando CSV...", "info");
}

async function limpiarDemo() {
  if (!confirm("¿Eliminar todos los datos de sesiones DEMO? Esta acción no se puede deshacer.")) return;
  try {
    const res  = await fetch(`${API_BASE}/api/clear_demo`, { method: "POST" });
    const json = await res.json();
    mostrarToast(`${json.sesiones_eliminadas} sesión(es) DEMO eliminadas.`, "ok");
    cargarHistorial();
  } catch (_) { mostrarToast("Error al limpiar datos.", "error"); }
}

async function resetearBase() {
  try {
    await fetch(`${API_BASE}/api/reset_baseline`, { method: "POST" });
    mostrarToast("Línea base reiniciada. Se recalculará con las próximas lecturas.", "ok");
  } catch (_) { mostrarToast("Error al reiniciar línea base.", "error"); }
}

// ═══════════════════════════════════════════════════════════
//  UTILIDADES
// ═══════════════════════════════════════════════════════════
function formatearTimestamp(ts) {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toLocaleString("es-ES", { dateStyle: "short", timeStyle: "medium" });
  } catch (_) { return ts; }
}

function formatearDuracion(segundos) {
  if (!segundos) return "0s";
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function mostrarToast(mensaje, tipo = "info") {
  const contenedor = document.getElementById("toast-container");
  if (!contenedor) return;

  const toast = document.createElement("div");
  toast.className  = `toast ${tipo}`;
  toast.textContent = mensaje;
  contenedor.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity   = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
