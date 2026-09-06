"""El transporte: HTTP sincrono sobre el bucle local, y nada mas.

ADR-14. No sostiene ninguna garantia: no se le pide orden, ni exactamente una
vez, ni durabilidad. Todo eso vive a los lados -- la bandeja de salida en SV-1 y
la clave de la terna en SV-2--, y por eso en M11 sustituirlo es sustituir un
adaptador.

Dos decisiones que no son de estilo:

  * El cliente se construye con `ProxyHandler({})`. Sin eso, `urllib` leeria
    `http_proxy` del entorno y una peticion a 127.0.0.1 podria salir a la red.
    RNF-06 dice **sin red externa**, y esto es lo que lo hace cierto en vez de
    probable.
  * Los servidores escuchan **solo** en 127.0.0.1. No hay interfaz publica.
"""

import http.server
import json
import socket
import urllib.error
import urllib.request

MAQUINA = "127.0.0.1"

# Un cliente que ignora la configuracion de proxy del entorno.
_ABRIDOR = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def puerto_libre():
    """Un puerto que el sistema operativo declara libre en este instante.

    Lo pide el instrumento y se lo pasa al proceso hijo como parametro de
    lanzamiento (SEC-2 §3.2): no hay puerto fijo en el codigo para la corrida
    medida. Entre esta llamada y el `bind` del hijo hay una ventana en la que
    otro proceso podria tomarlo; si ocurre, el hijo no arranca y la corrida sale
    NC-2 declarandolo. [A] la ventana es estrecha y no se cierra aqui.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((MAQUINA, 0))
        return s.getsockname()[1]
    finally:
        s.close()


def puerto_ocupado(puerto):
    """Cierto si algo escucha ya en ese puerto. No lo toca y no lo mata."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex((MAQUINA, puerto)) == 0
    finally:
        s.close()


def base(puerto):
    return "http://%s:%d" % (MAQUINA, puerto)


def pedir(url_base, ruta, cuerpo=None, metodo=None, tiempo=20.0):
    """Una peticion. Devuelve (codigo, cuerpo) tambien cuando el codigo es 4xx.

    Un desenlace de dominio y un rechazo son respuestas, no excepciones: quien
    llama tiene que poder distinguir `registrada`, `ya_registrada` y
    `rechazada_lote_no_sembrado` sin atrapar nada.
    """
    datos = None
    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(
        url_base + ruta, data=datos,
        method=metodo or ("POST" if datos is not None else "GET"),
        headers={"Content-Type": "application/json"})
    try:
        with _ABRIDOR.open(peticion, timeout=tiempo) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        crudo = error.read().decode("utf-8")
        try:
            return error.code, json.loads(crudo)
        except ValueError:
            return error.code, {"desenlace": "respuesta_ilegible", "crudo": crudo[:200]}


def crear_servidor(puerto, manejar):
    """Un servidor de un solo hilo. `manejar(metodo, ruta, cuerpo)` responde
    `(codigo, dict)`.

    De un solo hilo a proposito: en el MVP no hay concurrencia externa, y un
    servidor secuencial hace el camino reproducible. La consecuencia se declara
    y no se disimula: **el control de concurrencia optimista por version
    (ADR-03) queda sin ejercitar en PL-2**.
    """

    class Manejador(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def _responder(self, codigo, cuerpo):
            datos = json.dumps(cuerpo).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            self._atender("GET", None)

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            crudo = self.rfile.read(largo) if largo else b"{}"
            try:
                cuerpo = json.loads(crudo.decode("utf-8"))
            except ValueError:
                self._responder(400, {"desenlace": "cuerpo_ilegible"})
                return
            self._atender("POST", cuerpo)

        def _atender(self, metodo, cuerpo):
            try:
                codigo, respuesta = manejar(metodo, self.path, cuerpo)
            except Exception as error:            # noqa: BLE001 - se declara, no se traga
                # Un fallo del servicio se dice con su clase, sin rastro
                # interno en el cuerpo (RNF-10). El detalle va al log del
                # proceso, que vive en el directorio de la corrida.
                self.log_error("fallo interno: %r", error)
                codigo, respuesta = 500, {"desenlace": "fallo_interno",
                                          "clase": type(error).__name__}
            self._responder(codigo, respuesta)

        def log_message(self, formato, *args):
            pass

    return http.server.HTTPServer((MAQUINA, puerto), Manejador)


def esperar_vivo(url_base, intentos=100, pausa=0.05):
    """Espera a que un servicio conteste /salud. Devuelve su cuerpo o None."""
    import time
    for _ in range(intentos):
        try:
            codigo, cuerpo = pedir(url_base, "/salud", tiempo=2.0)
            if codigo == 200:
                return cuerpo
        except Exception:                          # noqa: BLE001
            pass
        time.sleep(pausa)
    return None
