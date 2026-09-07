"""SV-2 · el testigo. Guarda el libro de acciones y sabe contarlas.

Es el proceso que **no** muere en la medicion de C1-B, y por eso el recuento
vive aqui: RF-10 dice que el testigo no puede ser la victima. SV-1 puede caerse
entre decidir y registrar tantas veces como haga falta; `GET /recuentos` sigue
contestando porque lo contesta otro proceso, con otro almacen y otro ciclo de
vida.

Tres cosas que este servicio NO hace, y las tres son deliberadas:

  * **No evalua reglas.** No conoce umbrales ni duraciones. Su maquina de
    custodia es monotona y sin numeros (ADR-27): si reimplementara RC-08, habria
    dos implementaciones de la misma regla y la mutacion dejaria media viva.
  * **No pregunta nada a SV-1.** Conoce los lotes de la corrida porque se los
    siembra el guion, no porque los consulte. No existe en este modulo ninguna
    linea capaz de abrir el almacen de SV-1.
  * **No cuenta con un contador.** El recuento es `count(*)` sobre la tabla de
    acciones (ADR-24). Una columna que cuenta se puede desincronizar del hecho
    que dice contar; unas filas con clave primaria, no.

El desenlace de una entrega tiene **tres valores distinguibles**, y esa
distincion es SEC-1 (i):

    registrada                  la terna no estaba y ahora esta
    ya_registrada               la terna ya estaba: el efecto es uno, no dos
    rechazada_lote_no_sembrado  el lote no existe en esta corrida

Confundir el tercero con el primero haria que una accion sobre un lote
inventado engordara el recuento. Confundirlo con el segundo lo escondería
detras de un duplicado legitimo.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone

from . import almacen, protocolo, transporte

# La maquina de custodia, monotona y sin un solo umbral. El orden es el que
# manda: nunca se retrocede.
ORDEN_CUSTODIA = {"SIN_ACCIONES": 0, "EN_RESCATE": 1, "PERDIDO": 2}
CUSTODIA_DE_CLASE = {"RESCATE": "EN_RESCATE", "DISPOSICION": "PERDIDO"}

CAMPOS_ACCION = ("corrida_id", "lote_id", "secuencia_apertura", "clase",
                 "t_d_min", "regla_id", "instantanea_conclusion",
                 "sustituye_rescate_imposible")


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Servicio:
    def __init__(self, con, clase_entrada="http", grupo_entrada=None):
        self.con = con
        # El testigo tambien consume cuando el transporte es por eventos: si la
        # accion se produce a un tema, alguien tiene que sacarla de ahi. La
        # idempotencia sigue viviendo aqui -- en la terna--, no en el adaptador.
        self.entrada = transporte.construir_entrada(
            clase_entrada, tema=transporte.TEMA_ACCIONES,
            grupo=grupo_entrada or "p1.sv2")

    # --- siembra -------------------------------------------------------------

    def sembrar(self, cuerpo):
        """SEC-1 (ii): sembrar es un acto propio y anterior a toda entrega.

        Sin siembra previa, el rechazo de una entrega no distinguiria «este lote
        no existe» de «todavia no me han dicho que existe», y esa confusion es
        justo la que produce un B-2 rojo sobre un sistema correcto.
        """
        corrida = cuerpo["corrida_id"]
        lotes = cuerpo["lotes"]
        con = self.con
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                "INSERT OR REPLACE INTO siembra (corrida_id, sembrada_pared, "
                "lotes_sembrados) VALUES (?, ?, ?)",
                (corrida, _ahora(), len(lotes)))
            for lote in lotes:
                con.execute(
                    "INSERT OR IGNORE INTO siembra_lote (corrida_id, lote_id, "
                    "tipo_id) VALUES (?, ?, ?)",
                    (corrida, lote["lote_id"], lote["tipo_id"]))
                con.execute(
                    "INSERT OR IGNORE INTO lote_custodia (corrida_id, lote_id, "
                    "estado_custodia) VALUES (?, ?, 'SIN_ACCIONES')",
                    (corrida, lote["lote_id"]))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        return 201, {"desenlace": "sembrada", "corrida_id": corrida,
                     "lotes_sembrados": len(lotes)}

    # --- el receptor idempotente ---------------------------------------------

    def recibir_accion(self, cuerpo):
        faltan = [c for c in CAMPOS_ACCION if c not in cuerpo]
        if faltan:
            return 400, {"desenlace": "peticion_incompleta", "faltan": faltan}

        corrida = cuerpo["corrida_id"]
        lote_id = cuerpo["lote_id"]
        terna = (lote_id, cuerpo["secuencia_apertura"], cuerpo["clase"])

        sembrado = self.con.execute(
            "SELECT 1 FROM siembra_lote WHERE corrida_id = ? AND lote_id = ?",
            (corrida, lote_id)).fetchone()
        if sembrado is None:
            # SEC-1 (i). No es un error del transporte y no es un duplicado:
            # es un rechazo de dominio, y se dice con su propio nombre.
            return 409, {"desenlace": "rechazada_lote_no_sembrado",
                         "lote_id": lote_id, "terna": terna}

        con = self.con
        con.execute("BEGIN IMMEDIATE")
        try:
            try:
                con.execute(
                    "INSERT INTO accion (corrida_id, lote_id, secuencia_apertura, "
                    "clase, t_d_min, regla_id, instantanea_conclusion, "
                    "sustituye_rescate_imposible, instante_registro_pared) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (corrida, lote_id, cuerpo["secuencia_apertura"],
                     cuerpo["clase"], cuerpo["t_d_min"], cuerpo["regla_id"],
                     json.dumps(cuerpo["instantanea_conclusion"], sort_keys=True),
                     int(bool(cuerpo["sustituye_rescate_imposible"])), _ahora()))
            except sqlite3.IntegrityError:
                # La terna ya estaba. El efecto es UNO. Se cuenta la repeticion
                # aparte, porque «cuantas veces llego» es dato de operacion y no
                # puede contaminar «cuantas acciones hay».
                con.execute(
                    "INSERT INTO entrega_repetida (corrida_id, lote_id, "
                    "secuencia_apertura, clase, veces) VALUES (?, ?, ?, ?, 1) "
                    "ON CONFLICT (corrida_id, lote_id, secuencia_apertura, clase) "
                    "DO UPDATE SET veces = veces + 1",
                    (corrida,) + terna)
                con.execute("COMMIT")
                return 200, {"desenlace": "ya_registrada", "terna": terna}

            self._avanzar_custodia(corrida, lote_id, cuerpo)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        return 201, {"desenlace": "registrada", "terna": terna}

    def _avanzar_custodia(self, corrida, lote_id, cuerpo):
        """Monotona: al estado mas avanzado de los dos, nunca hacia atras."""
        fila = self.con.execute(
            "SELECT estado_custodia FROM lote_custodia "
            "WHERE corrida_id = ? AND lote_id = ?", (corrida, lote_id)).fetchone()
        actual = fila["estado_custodia"] if fila else "SIN_ACCIONES"
        propuesto = CUSTODIA_DE_CLASE.get(cuerpo["clase"], actual)
        destino = actual if ORDEN_CUSTODIA[actual] >= ORDEN_CUSTODIA[propuesto] \
            else propuesto
        self.con.execute(
            "UPDATE lote_custodia SET estado_custodia = ?, ultima_instantanea = ?, "
            "instante_ultima_accion_pared = ? WHERE corrida_id = ? AND lote_id = ?",
            (destino, json.dumps(cuerpo["instantanea_conclusion"], sort_keys=True),
             _ahora(), corrida, lote_id))

    # --- el recuento ---------------------------------------------------------

    def recuentos(self, corrida):
        """`count(*)` sobre el libro. Ninguna columna cuenta por su cuenta."""
        filas = self.con.execute(
            "SELECT lote_id, secuencia_apertura, clase FROM accion "
            "WHERE corrida_id = ? ORDER BY lote_id, secuencia_apertura, clase",
            (corrida,)).fetchall()
        por_clase = {}
        for f in filas:
            por_clase[f["clase"]] = por_clase.get(f["clase"], 0) + 1
        repetidas = self.con.execute(
            "SELECT coalesce(sum(veces), 0) AS n FROM entrega_repetida "
            "WHERE corrida_id = ?", (corrida,)).fetchone()["n"]
        sembrados = self.con.execute(
            "SELECT count(*) AS n FROM siembra_lote WHERE corrida_id = ?",
            (corrida,)).fetchone()["n"]
        custodia = {f["lote_id"]: f["estado_custodia"] for f in self.con.execute(
            "SELECT lote_id, estado_custodia FROM lote_custodia "
            "WHERE corrida_id = ?", (corrida,)).fetchall()}
        return 200, {
            "corrida_id": corrida,
            "acciones": len(filas),
            "por_clase": por_clase,
            "ternas": [[f["lote_id"], f["secuencia_apertura"], f["clase"]]
                       for f in filas],
            "entregas_repetidas": repetidas,
            "lotes_sembrados": sembrados,
            "custodia": custodia,
            "contado_como": "count(*) sobre la tabla accion · sin columna contador",
        }

    # --- enrutado ------------------------------------------------------------

    def manejar(self, metodo, ruta, cuerpo):
        camino = ruta.split("?")[0].rstrip("/") or "/"
        consulta = {}
        if "?" in ruta:
            for par in ruta.split("?", 1)[1].split("&"):
                if "=" in par:
                    k, v = par.split("=", 1)
                    consulta[k] = v

        if metodo == "GET" and camino == "/salud":
            return 200, {"servicio": "SV-2", "papel": "testigo", "estado": "vivo"}
        if metodo == "GET" and camino == "/recuentos":
            corrida = consulta.get("corrida_id")
            if not corrida:
                return 400, {"desenlace": "falta_corrida_id"}
            return self.recuentos(corrida)
        if metodo == "POST" and camino == "/siembra":
            return self.sembrar(cuerpo)
        if metodo == "POST" and camino == "/acciones":
            return self.recibir_accion(cuerpo)
        return 404, {"desenlace": "ruta_desconocida", "ruta": camino}


def main(argv=None):
    partes = argparse.ArgumentParser(description="SV-2 · el testigo")
    partes.add_argument("--puerto", type=int, required=True)
    partes.add_argument("--directorio", required=True)
    partes.add_argument("--receptor-no-idempotente", action="store_true",
                        help="MUTANTE: la terna deja de ser clave. Existe para la "
                             "calibracion de C1-B, no para operar.")
    partes.add_argument("--entrada", default="http",
                        help="que adaptador trae las acciones al receptor")
    partes.add_argument("--grupo-entrada", default=None,
                        help="grupo de consumo del receptor")
    args = partes.parse_args(argv)

    con = almacen.abrir_al2(almacen.ruta_al2(args.directorio),
                            idempotente=not args.receptor_no_idempotente)
    if args.receptor_no_idempotente:
        print("SV-2 ARRANCA MUTADO: receptor no idempotente", flush=True)
    servicio = Servicio(con, clase_entrada=args.entrada,
                        grupo_entrada=args.grupo_entrada)
    # La ruta /acciones sigue ABIERTA aunque la entrada sea por eventos, y la
    # asimetria con SV-1 es deliberada: alli cerrarla evita una medicion
    # silenciosamente falsa -- entrada por eventos con emisor por HTTP seguiria
    # funcionando y mentiria--. Aqui no evita nada parecido: si el transporte y
    # la entrada no casaran, nadie consumiria el tema y el recuento saldria
    # cero, que es un fallo a gritos. Y cerrarla romperia las sondas que
    # comprueban el vocabulario del receptor posteando directo.
    servicio.entrada.arrancar(servicio.recibir_accion)
    servidor = protocolo.crear_servidor(args.puerto, servicio.manejar)
    print("SV-2 escuchando en %s" % protocolo.base(args.puerto), flush=True)
    try:
        if servicio.entrada.necesita_bombeo:
            servidor.timeout = 0.02
            while True:
                servidor.handle_request()
                servicio.entrada.bombear()
        else:
            servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servicio.entrada.parar()
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
