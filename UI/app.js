const API_TRANSACCIONES = "http://localhost:8002";
const WS_IA = "ws://localhost:8001/ws/recomendaciones";
const moneda = "USD";

// obtiene referencias a los controles de la pantalla
const $ = (id) => document.getElementById(id);
const form = $("formTransferencia");
const origen = $("cuentaOrigen");
const destino = $("cuentaDestino");
const descripcion = $("descripcion");
const monto = $("monto");
const resumen = $("resumen");
const estado = $("estado");
const mensajeIa = $("mensajeIa");
const wsEstado = $("wsEstado");

let claveIdempotencia = crearClave();
let ultimaTransaccionId = null;
let temporizadorEstado = null;

// genera una clave unica para evitar procesar dos veces la misma transferencia
function crearClave() {
  return `ui-${crypto.randomUUID ? crypto.randomUUID() : Date.now() + "-" + Math.random().toString(16).slice(2)}`;
}

// arma el contrato requerido por la api de transacciones
function contrato() {
  return {
    cuenta_origen_id: Number(origen.value || 0),
    cuenta_destino_id: Number(destino.value || 0),
    monto: Number(monto.value || 0),
    moneda,
    descripcion: descripcion.value || "Transferencia desde UI",
    clave_idempotencia: claveIdempotencia,
  };
}

function pintarResumen(data = contrato()) {
  resumen.textContent = JSON.stringify(data, null, 2);
}

// limpia los mensajes temporales despues de terminar la operacion
function limpiarEstadoDespues() {
  clearTimeout(temporizadorEstado);
  temporizadorEstado = setTimeout(() => {
    estado.className = "alert alert-light border small";
    estado.textContent = "Listo para enviar.";
  }, 5000);
}

// carga las cuentas disponibles en los selectores
function llenarSelect(select, cuentas) {
  select.innerHTML = cuentas
    .map((cuenta) => `<option value="${cuenta.id_cuenta}">${cuenta.id_cuenta} - ${cuenta.cliente}</option>`)
    .join("");
}

async function cargarCuentas() {
  try {
    const respuesta = await fetch(`${API_TRANSACCIONES}/api/cuentas`);
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    const cuentas = await respuesta.json();
    llenarSelect(origen, cuentas);
    llenarSelect(destino, cuentas);
    destino.selectedIndex = cuentas.length > 1 ? 1 : 0;
    pintarResumen();
  } catch (error) {
    estado.className = "alert alert-danger small";
    estado.textContent = `No se pudieron cargar las cuentas: ${error.message}`;
  }
}

async function enviarTransferencia(evento) {
  evento.preventDefault();

  const payload = contrato();
  if (payload.cuenta_origen_id === payload.cuenta_destino_id) {
    estado.className = "alert alert-warning small";
    estado.textContent = "La cuenta de origen y destino deben ser diferentes.";
    return;
  }

  estado.className = "alert alert-info small";
  estado.textContent = "Enviando transferencia...";
  clearTimeout(temporizadorEstado);
  pintarResumen(payload);

  try {
    const respuesta = await fetch(`${API_TRANSACCIONES}/api/transacciones`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await respuesta.json();
    ultimaTransaccionId = data.transaccion_id;
    pintarResumen(data);
    estado.className = data.estado === "COMPLETADA" ? "alert alert-success small" : "alert alert-warning small";
    estado.textContent = `${data.estado}: ${data.motivo}`;
    limpiarEstadoDespues();
    // si la api respondio, la siguiente operacion debe usar otra clave
    claveIdempotencia = crearClave();
  } catch {
    estado.className = "alert alert-danger small";
    estado.textContent = "No se pudo confirmar la transferencia. Reintenta con la misma clave.";
    limpiarEstadoDespues();
  }
}

// escucha las recomendaciones generadas por el worker de ia
function conectarIa() {
  const socket = new WebSocket(WS_IA);
  socket.onopen = () => {
    wsEstado.textContent = "conectado";
    setInterval(() => socket.readyState === WebSocket.OPEN && socket.send("ping"), 25000);
  };
  socket.onclose = () => {
    wsEstado.textContent = "desconectado";
    setTimeout(conectarIa, 3000);
  };
  socket.onerror = () => {
    wsEstado.textContent = "sin conexion";
  };
  socket.onmessage = (evento) => {
    const data = JSON.parse(evento.data);
    const esActual = !ultimaTransaccionId || data.transaccion_id === ultimaTransaccionId;
    if (esActual) {
      mensajeIa.textContent = data.recomendacion || "Recomendacion recibida.";
    }
  };
}

[origen, destino, descripcion, monto].forEach((campo) => {
  campo.addEventListener("input", () => pintarResumen());
});
form.addEventListener("submit", enviarTransferencia);

cargarCuentas();
conectarIa();
