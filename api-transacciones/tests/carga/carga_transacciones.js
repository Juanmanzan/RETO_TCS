import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8002';

const RATE = Number(__ENV.RATE || 100);
const DURATION = __ENV.DURATION || '30s';
const VALIDAR_NEGOCIO =
  (__ENV.VALIDAR_NEGOCIO || 'true').toLowerCase() === 'true';

export const options = {
  discardResponseBodies: !VALIDAR_NEGOCIO,

  scenarios: {
    transacciones: {
      executor: 'constant-arrival-rate',

      // transacciones que k6 intentará iniciar por segundo
      rate: RATE,

      timeUnit: '1s',

      duration: DURATION,

      // VUs iniciales disponibles
      preAllocatedVUs: 500,

      // límite que k6 puede crear si las respuestas empiezan a tardar
      maxVUs: 10000,
    },
  },

  thresholds: {
    // menos del 1% de errores HTTP
    http_req_failed: ['rate<0.01'],

    // objetivos iniciales de latencia
    http_req_duration: [
      'p(95)<200',
      'p(99)<500',
    ],
  },
};


const cuentas = [
  1001,
  1002,
  1003,
  1004,
  1005,
];


export default function () {

  /*
    Se rota entre las cinco cuentas.

    Ejemplo:
      1001 -> 1002
      1002 -> 1003
      1003 -> 1004
      1004 -> 1005
      1005 -> 1001
  */

  const posicion = (__VU + __ITER) % cuentas.length;

  const cuentaOrigen = cuentas[posicion];

  const cuentaDestino =
    cuentas[(posicion + 1) % cuentas.length];


  /*
    Cada petición necesita una clave de idempotencia única.

    __VU    = usuario virtual
    __ITER  = iteración del usuario virtual
    Date.now() ayuda a evitar reutilización entre ejecuciones distintas.
  */
  const claveIdempotencia =
    `k6-${Date.now()}-${__VU}-${__ITER}`;


  const payload = JSON.stringify({
    cuenta_origen_id: cuentaOrigen,
    cuenta_destino_id: cuentaDestino,
    monto: 1,
    moneda: 'USD',
    descripcion: 'Prueba de carga k6',
    clave_idempotencia: claveIdempotencia,
  });


  const parametros = {
    headers: {
      'Content-Type': 'application/json',
    },
  };


  const respuesta = http.post(
    `${BASE_URL}/api/transacciones`,
    payload,
    parametros,
  );

  let cuerpo = {};

  if (VALIDAR_NEGOCIO) {
    try {
      cuerpo = respuesta.json();
    } catch {
      cuerpo = {};
    }
  }

  check(respuesta, {
    'respuesta HTTP 200': (r) => r.status === 200,
    'transaccion completada': () =>
      !VALIDAR_NEGOCIO || cuerpo.estado === 'COMPLETADA',
    'motivo OK': () =>
      !VALIDAR_NEGOCIO || cuerpo.motivo === 'OK',
  });
}
