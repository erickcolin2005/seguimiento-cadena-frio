"""SV-1 · el nucleo de reglas, la bandeja de salida y su drenaje.

Es el proceso que muere. Todo lo que aqui se decide tiene que sobrevivir a que
lo maten en el peor instante, y por eso hay dos mecanismos y no uno:

  * **Persistir antes de evaluar** (ADR-01). La lectura se compromete a disco y
    se acusa ANTES de que ninguna regla la mire. Si el proceso muere durante la
    evaluacion, la lectura ya esta; si muriera al reves, se habria acusado algo
    que no existe.
  * **La bandeja de salida** (ADR-04). La conclusion y la intencion de actuar se
    escriben en **la misma transaccion local**. O estan las dos o no esta
    ninguna. El envio por la red ocurre despues y fuera de la transaccion,
    porque una llamada de red dentro de una transaccion es la transaccion
    esperando a algo que no controla.

**Las reglas no estan aqui.** Se importan de `banco`, que es el mismo codigo que
el banco de 64 casos ejerce y que la mutacion apaga pieza a pieza. Una segunda
implementacion produciria la regla escrita dos veces con media viva -- el defecto
real que la mutacion estricta encontro en P4-- y ninguna de las dos copias
quedaria cubierta por CT-3.

Lo que SV-1 NO hace: no cuenta acciones. Cuando drena, pregunta el desenlace y
lo obedece, pero **el numero vive en SV-2** (RF-10). Si el recuento viviera
aqui, moriria con el proceso justo cuando hace falta.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone

from banco import dominio, motor, reloj
from banco.motor import RegistroAcciones
from banco.piezas import Interruptores

from . import almacen, guion as modulo_guion, protocolo

CLASES_ACTUABLES = ("RESCATE", "DISPOSICION")


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Servicio:
    def __init__(self, con, guion, corrida_id, url_sv2, reconstruye_orden=True):
        self.con = con
        # El mutante de C1-A. Apagarlo hace que SV-1 trate la posicion de LLEGADA
        # como si fuera el instante en que ocurrio -- que es lo que hace un
        # sistema que no reconstruye el orden--. No es una opcion de operacion:
        # existe para que la medicion pueda VERSE fallar. Si con esto apagado
        # C1-A siguiera saliendo verde, C1-A no estaria midiendo nada.
        self.reconstruye_orden = reconstruye_orden
        self.guion = guion
        self.corrida_id = corrida_id
        self.url_sv2 = url_sv2
        self.sw = Interruptores()
        self.lotes_por_envio = {e["envio_id"]: e["lotes"] for e in guion["envios"]}
        self._sembrar_catalogo()

    # --- arranque ------------------------------------------------------------

    def _sembrar_catalogo(self):
        """Corrida, tipos, envios y lotes del guion. Sin una sola lectura."""
        con = self.con
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                "INSERT OR REPLACE INTO corrida (corrida_id, semilla, "
                "digesto_guion, instante_arranque_pared, donde_corrio, parametros) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.corrida_id, self.guion["semilla"],
                 modulo_guion.digesto(self.guion), _ahora(), sys.platform,
                 json.dumps({"version_guion": self.guion["version_guion"]})))
            for codigo, p in dominio.TIPOS.items():
                con.execute(
                    "INSERT OR REPLACE INTO tipo_producto (tipo_id, rango_min_c, "
                    "rango_max_c, duracion_minima_min, duracion_tolerada_min, "
                    "granularidad_muestreo_s, retencion_meses, origen_umbral) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (codigo, p.minimo, p.maximo, p.duracion_minima,
                     p.duracion_tolerada, p.granularidad, 24,
                     "banco/dominio.py · DN-02, DN-05, DN-06, DN-09 · valores de "
                     "trabajo NO validados por el negocio"))
            for envio in self.guion["envios"]:
                con.execute(
                    "INSERT OR REPLACE INTO envio (corrida_id, envio_id, "
                    "secuencia_total_declarada, estado) VALUES (?, ?, ?, ?)",
                    (self.corrida_id, envio["envio_id"], len(envio["lecturas"]),
                     envio["estado"]))
                con.execute(
                    "INSERT OR REPLACE INTO envio_proyeccion (corrida_id, envio_id, "
                    "mac, secuencia_sellada_hasta, t_d_vigente_min, version) "
                    "VALUES (?, ?, -1, -1, NULL, 0)",
                    (self.corrida_id, envio["envio_id"]))
                for lote in envio["lotes"]:
                    con.execute(
                        "INSERT OR REPLACE INTO lote (corrida_id, lote_id, envio_id, "
                        "tipo_id, carga_min, entrega_min, carga_secuencia, "
                        "entrega_secuencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (self.corrida_id, lote["lote_id"], envio["envio_id"],
                         lote["tipo_id"], lote["carga_min"], lote["entrega_min"],
                         lote["carga_secuencia"], lote["entrega_secuencia"]))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    # --- ingesta -------------------------------------------------------------

    def recibir_lectura(self, cuerpo):
        """ADR-01: primero se compromete, despues se evalua."""
        envio_id = cuerpo["envio_id"]
        secuencia = cuerpo["secuencia"]

        # --- paso 1 · persistir. Transaccion propia, y termina aqui.
        con = self.con
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                "INSERT OR IGNORE INTO lectura (corrida_id, envio_id, secuencia, "
                "produccion_min, valor_c, validez, emision_pared, recepcion_pared) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.corrida_id, envio_id, secuencia, cuerpo["produccion_min"],
                 cuerpo["valor_c"], "SIN_VALOR" if cuerpo["valor_c"] is None
                 else "CON_VALOR", cuerpo.get("emision_pared", _ahora()), _ahora()))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        if envio_id not in self.lotes_por_envio:
            # RC-01: la lectura queda conservada aunque no se pueda atribuir.
            # No evaluarla no es descartarla, y por eso el paso 1 ya termino.
            return 202, {"desenlace": "conservada_no_atribuible", "envio_id": envio_id,
                         "regla_id": "RC-01"}

        # --- paso 2 · evaluar sobre el prefijo persistido, y decidir.
        # El instante de decision NO es el de la lectura que acaba de llegar: es
        # la marca de agua del envio, el mayor instante de produccion que consta.
        # Usar el de la recien llegada haria que una lectura tardia y antigua
        # hiciera RETROCEDER la conclusion -- el sistema olvidaria lo que ya
        # sabia-- y eso es depender del orden de entrega, que es justo lo que
        # D2 dice que no pasa. Lo encontro C1-A.
        propuestas = self._evaluar(envio_id, self._marca_de_agua(envio_id))
        return 200, {"desenlace": "evaluada", "envio_id": envio_id,
                     "secuencia": secuencia, "acciones_en_bandeja": propuestas}

    def _marca_de_agua(self, envio_id):
        """El mayor instante de produccion que consta para este envio.

        Se deriva del prefijo PERSISTIDO, no de la ultima peticion, asi que es
        monotona por construccion y no depende del orden en que lleguen las
        lecturas. Es lo unico que puede hacer que la conclusion sea la misma
        vengan como vengan.
        """
        if not self.reconstruye_orden:
            # Sin reconstruccion, «ahora» es la ultima que llego, venga de cuando
            # venga: el instante de decision pasa a depender del transporte.
            fila = self.con.execute(
                "SELECT count(*) AS n FROM lectura WHERE corrida_id = ? AND envio_id = ?",
                (self.corrida_id, envio_id)).fetchone()
            return fila["n"] - 1
        fila = self.con.execute(
            "SELECT max(produccion_min) AS tope FROM lectura "
            "WHERE corrida_id = ? AND envio_id = ?",
            (self.corrida_id, envio_id)).fetchone()
        return fila["tope"]

    def _envio_del_prefijo(self, envio_id):
        """El envio tal como SV-1 lo conoce: lo que tiene PERSISTIDO."""
        orden = ("produccion_min, secuencia" if self.reconstruye_orden else "rowid")
        filas = self.con.execute(
            "SELECT secuencia, produccion_min, valor_c FROM lectura "
            "WHERE corrida_id = ? AND envio_id = ? ORDER BY " + orden,
            (self.corrida_id, envio_id)).fetchall()
        if self.reconstruye_orden:
            lecturas = tuple(
                dominio.Lectura(indice=f["secuencia"],
                                produccion=reloj.instante(f["produccion_min"]),
                                valor=f["valor_c"], envio_id=envio_id)
                for f in filas)
        else:
            lecturas = tuple(
                dominio.Lectura(indice=posicion,
                                produccion=reloj.instante(posicion),
                                valor=f["valor_c"], envio_id=envio_id)
                for posicion, f in enumerate(filas))
        lotes = tuple(
            dominio.Lote(lote_id=l["lote_id"], tipo_producto=l["tipo_id"],
                         carga=reloj.instante(l["carga_min"]),
                         entrega=reloj.instante(l["entrega_min"]))
            for l in self.lotes_por_envio[envio_id])
        return dominio.Envio(envio_id, lotes, lecturas)

    def _evaluar(self, envio_id, t_d_min):
        envio = self._envio_del_prefijo(envio_id)
        t_d = reloj.instante(t_d_min)
        puestas = []

        con = self.con
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                "UPDATE envio_proyeccion SET secuencia_sellada_hasta = ?, "
                "t_d_vigente_min = ?, version = version + 1 "
                "WHERE corrida_id = ? AND envio_id = ?",
                (max((l.indice for l in envio.lecturas), default=-1), t_d_min,
                 self.corrida_id, envio_id))

            for lote in envio.lotes:
                # Un registro nuevo por evaluacion: SV-1 PROPONE el hecho
                # actuable cada vez que lo decide. Quien deduplica es la clave
                # primaria de la bandeja, que sobrevive a la muerte del proceso;
                # una memoria de proceso no sobreviviria.
                registro = RegistroAcciones(self.sw)
                conclusion = motor.evaluar_lote(envio, lote, t_d, self.sw, registro)
                self._escribir_conclusion(conclusion)
                for accion in registro.acciones:
                    if accion.clase not in CLASES_ACTUABLES:
                        continue
                    if self._poner_en_bandeja(accion, conclusion, t_d_min):
                        puestas.append([accion.lote_id,
                                        reloj.desplazamiento(accion.apertura_excursion),
                                        accion.clase])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        return puestas

    def _escribir_conclusion(self, c):
        lote_id = c.lote_id
        con = self.con
        for v in c.veredictos:
            con.execute(
                "INSERT OR REPLACE INTO veredicto_lectura (corrida_id, envio_id, "
                "secuencia, lote_id, evaluada, situacion, regla_id, mensaje_llano) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.corrida_id, self._envio_de_lote(lote_id), v.indice, lote_id,
                 int(v.atribucion == "evaluada"), v.situacion or "no_evaluada",
                 v.regla_situacion or v.regla_validez or v.regla_atribucion or "RC-01",
                 "lectura %d del lote %s" % (v.indice, lote_id)))
        for e in c.excursiones:
            con.execute(
                "INSERT OR REPLACE INTO excursion (corrida_id, lote_id, "
                "secuencia_apertura, apertura_min, secuencia_cierre, cierre_min, "
                "duracion_min, transitoria, estado, regla_apertura_id, "
                "regla_cierre_id, sellada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.corrida_id, lote_id, reloj.desplazamiento(e.apertura),
                 reloj.desplazamiento(e.apertura), reloj.desplazamiento(e.cierre),
                 reloj.desplazamiento(e.cierre), e.duracion, int(e.transitoria),
                 "ABIERTA" if e.abierta else "CERRADA", e.regla_apertura,
                 e.regla_cierre, 1))
        con.execute(
            "INSERT OR REPLACE INTO conclusion_lote (corrida_id, lote_id, aptitud, "
            "regla_aptitud, acumulado_min, clase_accion, regla_clase_accion, "
            "marca_secuencia, provisional, t_d_min, umbral_superado, "
            "irreversible_activa, cerrada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.corrida_id, lote_id, c.aptitud or "sin_evaluar", c.regla_aptitud,
             c.acumulado or 0, c.clase_accion or "NINGUNA", c.regla_clase_accion,
             c.marca_secuencia or "sin_evaluar", int(c.provisional),
             reloj.desplazamiento(c.t_d), int(c.umbral_superado),
             int(c.irreversible_activa), int(c.cerrada_en is not None)))

    def _envio_de_lote(self, lote_id):
        for envio_id, lotes in self.lotes_por_envio.items():
            if any(l["lote_id"] == lote_id for l in lotes):
                return envio_id
        return "?"

    def _poner_en_bandeja(self, accion, conclusion, t_d_min):
        """Devuelve True si la terna no estaba. La clave primaria ES la terna."""
        instantanea = json.dumps({
            "aptitud": conclusion.aptitud,
            "regla_aptitud": conclusion.regla_aptitud,
            "acumulado_min": conclusion.acumulado,
            "umbral_superado": conclusion.umbral_superado,
            "irreversible_activa": conclusion.irreversible_activa,
            "marca_secuencia": conclusion.marca_secuencia,
        }, sort_keys=True)
        cursor = self.con.execute(
            "INSERT OR IGNORE INTO bandeja_salida (corrida_id, lote_id, "
            "secuencia_apertura, clase, t_d_min, regla_id, instantanea_conclusion, "
            "sustituye_rescate_imposible, estado, intentos, commit_pared) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'PENDIENTE', 0, ?)",
            (self.corrida_id, accion.lote_id,
             reloj.desplazamiento(accion.apertura_excursion), accion.clase,
             t_d_min, accion.regla_id or "RC-09", instantanea, _ahora()))
        return cursor.rowcount > 0

    # --- drenaje -------------------------------------------------------------

    def drenar(self):
        """Entrega al-menos-una-vez. El efecto exactamente uno lo pone SV-2.

        Fuera de toda transaccion a proposito: una llamada de red dentro de una
        transaccion la deja esperando a algo que no controla.
        """
        pendientes = self.con.execute(
            "SELECT * FROM bandeja_salida WHERE corrida_id = ? AND estado = 'PENDIENTE' "
            "ORDER BY commit_pared, lote_id, secuencia_apertura",
            (self.corrida_id,)).fetchall()
        entregadas, rechazadas, fallidas = 0, [], []
        for fila in pendientes:
            cuerpo = {
                "corrida_id": fila["corrida_id"],
                "lote_id": fila["lote_id"],
                "secuencia_apertura": fila["secuencia_apertura"],
                "clase": fila["clase"],
                "t_d_min": fila["t_d_min"],
                "regla_id": fila["regla_id"],
                "instantanea_conclusion": json.loads(fila["instantanea_conclusion"]),
                "sustituye_rescate_imposible": bool(
                    fila["sustituye_rescate_imposible"]),
            }
            self.con.execute(
                "UPDATE bandeja_salida SET intentos = intentos + 1 WHERE "
                "corrida_id = ? AND lote_id = ? AND secuencia_apertura = ? AND clase = ?",
                (fila["corrida_id"], fila["lote_id"], fila["secuencia_apertura"],
                 fila["clase"]))
            try:
                codigo, respuesta = protocolo.pedir(self.url_sv2, "/acciones", cuerpo)
            except Exception as error:              # noqa: BLE001
                fallidas.append({"terna": [fila["lote_id"],
                                           fila["secuencia_apertura"], fila["clase"]],
                                 "motivo": type(error).__name__})
                continue
            desenlace = respuesta.get("desenlace")
            if desenlace in ("registrada", "ya_registrada"):
                self.con.execute(
                    "UPDATE bandeja_salida SET estado = 'ENTREGADA', entrega_pared = ? "
                    "WHERE corrida_id = ? AND lote_id = ? AND secuencia_apertura = ? "
                    "AND clase = ?",
                    (_ahora(), fila["corrida_id"], fila["lote_id"],
                     fila["secuencia_apertura"], fila["clase"]))
                entregadas += 1
            else:
                # Un rechazo de dominio NO se reintenta: reintentarlo seria
                # confundir «no debe entrar» con «no llego».
                rechazadas.append({"terna": [fila["lote_id"],
                                             fila["secuencia_apertura"], fila["clase"]],
                                   "desenlace": desenlace, "codigo": codigo})
        return 200, {"desenlace": "drenada", "pendientes_al_empezar": len(pendientes),
                     "entregadas": entregadas, "rechazadas": rechazadas,
                     "fallidas": fallidas}

    def conclusiones(self):
        """Lo que SV-1 concluyo, por lote. Es lo que C1-A compara.

        Se publica el mismo juego de campos que la referencia calcula sobre el
        guion, para que la comparacion sea campo a campo y no «parece que si».
        """
        filas = self.con.execute(
            "SELECT lote_id, aptitud, regla_aptitud, acumulado_min, clase_accion, "
            "regla_clase_accion, marca_secuencia, provisional, umbral_superado, "
            "irreversible_activa FROM conclusion_lote WHERE corrida_id = ? "
            "ORDER BY lote_id", (self.corrida_id,)).fetchall()
        return 200, {"corrida_id": self.corrida_id,
                     "lotes": {f["lote_id"]: dict(f) for f in filas},
                     "total": len(filas)}

    def bandeja(self):
        filas = self.con.execute(
            "SELECT lote_id, secuencia_apertura, clase, estado, intentos "
            "FROM bandeja_salida WHERE corrida_id = ? "
            "ORDER BY lote_id, secuencia_apertura, clase",
            (self.corrida_id,)).fetchall()
        return 200, {"corrida_id": self.corrida_id, "entradas": [dict(f) for f in filas],
                     "total": len(filas),
                     "pendientes": sum(1 for f in filas if f["estado"] == "PENDIENTE")}

    # --- enrutado ------------------------------------------------------------

    def manejar(self, metodo, ruta, cuerpo):
        camino = ruta.split("?")[0].rstrip("/") or "/"
        if metodo == "GET" and camino == "/salud":
            return 200, {"servicio": "SV-1", "papel": "nucleo de reglas",
                         "estado": "vivo", "corrida_id": self.corrida_id,
                         "digesto_guion": modulo_guion.digesto(self.guion)}
        if metodo == "GET" and camino == "/bandeja":
            return self.bandeja()
        if metodo == "GET" and camino == "/conclusiones":
            return self.conclusiones()
        if metodo == "POST" and camino == "/lecturas":
            return self.recibir_lectura(cuerpo)
        if metodo == "POST" and camino == "/drenar":
            return self.drenar()
        return 404, {"desenlace": "ruta_desconocida", "ruta": camino}


def main(argv=None):
    partes = argparse.ArgumentParser(description="SV-1 · el nucleo de reglas")
    partes.add_argument("--puerto", type=int, required=True)
    partes.add_argument("--directorio", required=True)
    partes.add_argument("--semilla", type=int, required=True)
    partes.add_argument("--digesto", required=True)
    partes.add_argument("--corrida", required=True)
    partes.add_argument("--sv2", required=True, help="URL base de SV-2")
    partes.add_argument("--repeticiones", type=int, default=1)
    partes.add_argument("--sin-reconstruccion-de-orden", action="store_true",
                        help="MUTANTE: trata el orden de llegada como el real. "
                             "Existe para que C1-A pueda verse fallar.")
    args = partes.parse_args(argv)

    g = modulo_guion.generar(args.semilla, args.repeticiones)
    try:
        modulo_guion.exigir_digesto(g, args.digesto)
    except ValueError as error:
        print("SV-1 NO ARRANCA: %s" % error, file=sys.stderr, flush=True)
        return 3

    con = almacen.abrir_al1(almacen.ruta_al1(args.directorio))
    servicio = Servicio(con, g, args.corrida, args.sv2,
                        reconstruye_orden=not args.sin_reconstruccion_de_orden)
    if args.sin_reconstruccion_de_orden:
        print("SV-1 ARRANCA MUTADO: sin reconstruccion de orden", flush=True)
    servidor = protocolo.crear_servidor(args.puerto, servicio.manejar)
    print("SV-1 escuchando en %s" % protocolo.base(args.puerto), flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
