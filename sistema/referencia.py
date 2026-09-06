"""IN · la calculadora de referencia. Sobre el GUION, nunca sobre el sistema.

RF-18. Si la conclusion de referencia se leyera del sistema, seria el sistema
comparandose consigo mismo y no mediria nada. Por eso este modulo:

  * **no importa nada de red y nada de almacenamiento.** No hay ninguna linea
    aqui capaz de preguntarle algo a SV-1 ni a SV-2. La comprobacion 3 lo mide
    de dos formas: ejecutando este modulo **con SV-1 apagado**, y leyendo su
    cierre de importaciones.
  * **usa el mismo nucleo de reglas que SV-1**, y esa circularidad esta
    declarada (arquitectura §3.2): C1-A no compara dos implementaciones de las
    reglas, compara la misma regla aplicada a dos ordenes. La correccion de las
    reglas la miden el banco y su mutacion, que son instrumento distinto.

Lo que calcula es lo que las reglas producen sobre el guion **en orden de
produccion**, redecidiendo en cada instante de decision, que es como SV-1
trabaja cuando su marca de agua avanza.
"""

import argparse
import json
import sys

from banco import dominio, motor, reloj
from banco.motor import RegistroAcciones
from banco.piezas import Interruptores

from . import guion as modulo_guion


def _envio_de(crudo):
    """Traduce un envio del guion a las piezas del banco."""
    lotes = tuple(
        dominio.Lote(lote_id=l["lote_id"],
                     tipo_producto=l["tipo_id"],
                     carga=reloj.instante(l["carga_min"]),
                     entrega=reloj.instante(l["entrega_min"]))
        for l in crudo["lotes"])
    lecturas = tuple(
        dominio.Lectura(indice=lec["secuencia"],
                        produccion=reloj.instante(lec["produccion_min"]),
                        valor=lec["valor_c"],
                        envio_id=crudo["envio_id"])
        for lec in crudo["lecturas"])
    return dominio.Envio(crudo["envio_id"], lotes, lecturas)


def conclusiones_del_envio(envio, envio_id=None):
    """Evalua un envio entero redecidiendo en cada instante, y devuelve
    (conclusiones por lote, acciones registradas).

    Lo usa la referencia y lo usa C1-A para evaluar el mismo envio con los
    instantes de produccion reasignados por orden de llegada. **Tiene que ser la
    misma funcion en los dos casos**: si cada lado evaluara con su propio codigo,
    una divergencia podria venir del instrumento y no del sistema.
    """
    sw = Interruptores()
    registro = RegistroAcciones(sw)
    instantes = [lec.produccion for lec in
                 sorted(envio.lecturas, key=lambda l: l.produccion)]
    ultima = {}
    for t_d in instantes:
        for lote in envio.lotes:
            ultima[lote.lote_id] = motor.evaluar_lote(envio, lote, t_d, sw, registro)

    conclusiones = {}
    for lote_id, c in ultima.items():
        # `imputadas` y `fuera_de_rango` no son adorno: son lo que hace
        # distinguibles las clases IV-4 y IV-5, que a nivel de aptitud podrian
        # no verse.
        conclusiones[lote_id] = {
            "envio_id": envio_id or envio.envio_id,
            "tipo_id": c.tipo_producto,
            "aptitud": c.aptitud,
            "regla_aptitud": c.regla_aptitud,
            "acumulado_min": c.acumulado,
            "clase_accion": c.clase_accion,
            "regla_clase_accion": c.regla_clase_accion,
            "marca_secuencia": c.marca_secuencia,
            "provisional": c.provisional,
            "t_d_min": reloj.desplazamiento(c.t_d),
            "umbral_superado": c.umbral_superado,
            "irreversible_activa": c.irreversible_activa,
            "imputadas": sum(1 for v in c.veredictos if v.imputacion == "imputada"),
            "fuera_de_rango": sum(1 for v in c.veredictos
                                  if v.situacion == "fuera_de_rango"),
        }
    return conclusiones, registro.acciones


def calcular(guion):
    """La referencia: conclusion final por lote y ternas actuables del guion."""
    conclusiones = {}
    ternas = []
    for crudo in guion["envios"]:
        envio = _envio_de(crudo)
        del_envio, acciones = conclusiones_del_envio(envio, crudo["envio_id"])
        conclusiones.update(del_envio)
        for accion in acciones:
            ternas.append({
                "lote_id": accion.lote_id,
                "secuencia_apertura": reloj.desplazamiento(accion.apertura_excursion),
                "clase": accion.clase,
                "regla_id": accion.regla_id,
            })
    return {"semilla": guion["semilla"],
            "digesto_guion": modulo_guion.digesto(guion),
            "resumen": modulo_guion.resumen(guion),
            "lotes": conclusiones,
            "ternas": ternas}


def ternas_como_conjunto(referencia):
    return {(t["lote_id"], t["secuencia_apertura"], t["clase"])
            for t in referencia["ternas"]}


def imprimir(referencia, salida=sys.stdout):
    r = referencia
    print("CONCLUSION DE REFERENCIA · calculada sobre el GUION (RF-18)", file=salida)
    print("semilla: %d · digesto del guion: %s" % (r["semilla"], r["digesto_guion"]),
          file=salida)
    print("envios: %(envios)d · lotes: %(lotes)d · lecturas: %(lecturas)d" % r["resumen"],
          file=salida)
    print(file=salida)
    print("%-16s %-6s %-20s %6s %-12s %-22s" %
          ("LOTE", "TIPO", "APTITUD", "ACUM", "ACCION", "REGLAS"), file=salida)
    print("-" * 86, file=salida)
    for lote_id in sorted(r["lotes"]):
        c = r["lotes"][lote_id]
        print("%-16s %-6s %-20s %6s %-12s %s / %s" %
              (lote_id, c["tipo_id"], c["aptitud"], c["acumulado_min"],
               c["clase_accion"], c["regla_aptitud"], c["regla_clase_accion"]),
              file=salida)
    print(file=salida)
    print("TERNAS ACTUABLES QUE EL GUION DECLARA (lote, secuencia de apertura, clase)",
          file=salida)
    if not r["ternas"]:
        print("  ninguna", file=salida)
    for t in sorted(ternas_como_conjunto(r)):
        print("  %s · %s · %s" % t, file=salida)
    print(file=salida)
    print("Esta salida NO se leyo del sistema. Se calculo sobre el guion.", file=salida)


def main(argv=None):
    partes = argparse.ArgumentParser(
        description="Calcula la conclusion de referencia sobre el guion. "
                    "No contacta con ningun servicio.")
    partes.add_argument("--semilla", type=int, required=True)
    partes.add_argument("--digesto", default=None,
                        help="digesto fijado por la corrida; si no coincide, se niega")
    partes.add_argument("--json", action="store_true")
    args = partes.parse_args(argv)

    g = modulo_guion.generar(args.semilla)
    try:
        modulo_guion.exigir_digesto(g, args.digesto)
    except ValueError as error:
        print("REFERENCIA NO CALCULADA: %s" % error)
        return 3
    referencia = calcular(g)
    if args.json:
        print(json.dumps(referencia, sort_keys=True))
    else:
        imprimir(referencia)
    return 0


if __name__ == "__main__":
    sys.exit(main())
