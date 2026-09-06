"""El veredicto de la corrida, en el formato que exige DP-02.

    python veredicto.py

Consolida las dos mitades de C1 y publica el resultado con el veredicto en la
PRIMERA linea, los denominadores siempre impresos, y —si la corrida no midio—
que falto y la frase de que **una medicion invalida no es un defecto del sistema
medido**.

## SEC-5 · el veredicto tiene que ser computable con SV-1 detenido

Es una prueba negativa barata sobre RF-10: **si el veredicto no se puede emitir
sin SV-1, el recuento vive donde no debe** — en el proceso que muere—. Aqui el
recuento sale **solo** de `GET /recuentos` de SV-2.

`GET /bandeja` existe y es legitimo, pero **solo para B-2**. Contar ahi es la
tentacion y esta prohibido (T-06): el recuento pasaria a vivir en la victima y
C1-B dejaria de medir nada. Esta comprobacion se hace sobre el codigo, no de
palabra: se recorre el arbol sintactico de este fichero.

## B-2 cruza la frontera, y por eso puede quedarse sin comprobar

**B-2 · no pierde:** que una intencion comprometida no deje de ser accion. Se
comprueba cruzando la bandeja de SV-1 contra el libro de SV-2, asi que **ningun
almacen puede imponerla** — si uno pudiera, seria porque los dos almacenes son
uno, que es justo lo que RF-10 prohibe—.

Con SV-1 detenido, ese cruce **no se puede hacer**. La regla es explicita: su
indisponibilidad **no invalida la corrida** —MI-5 solo mira al receptor— **pero
se publica que no se pudo comprobar**, con esas palabras. Un APROBADO con lineas
sin comprobar es mas debil y **tiene que verse**.

Codigos de salida:
    0  APROBADO
    1  FALLO
    2  MEDICION INVALIDA
"""

import argparse
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from levantar import Orquesta, RAIZ, SEMILLA_POR_DEFECTO
from sistema import protocolo

ANCHO = 78

NO_COMPROBADA = "no se pudo comprobar"


def titulo(texto):
    print()
    print("=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


# --- SEC-5 · de donde sale el recuento ---------------------------------------

def de_donde_sale_el_recuento(fichero):
    """Rutas HTTP que este fichero pide, para ver de cual saca el numero.

    Se lee el arbol sintactico y no el texto: importa que se LLAME a `/recuentos`
    y que no se llame a `/bandeja` para contar. Es la misma disciplina que la
    comprobacion de umbrales de PL-2 -- un raspado de cadenas se encuentra a si
    mismo y da rojo sobre codigo correcto--.
    """
    arbol = ast.parse(Path(fichero).read_text(encoding="utf-8"), filename=str(fichero))
    rutas = set()
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "pedir" and len(nodo.args) >= 2):
            destino = nodo.args[1]
            # Una ruta con parametros se escribe con un formato, asi que el
            # literal esta a la izquierda del operador. Sin desenvolverlo, la
            # unica ruta cuyo nombre importa -- /recuentos-- apareceria como
            # «(compuesta)» y la afirmacion no se podria comprobar.
            if isinstance(destino, ast.BinOp):
                destino = destino.left
            if isinstance(destino, ast.Constant) and isinstance(destino.value, str):
                rutas.add(destino.value.split("?")[0])
            else:
                rutas.add("(no resuelta)")
    return sorted(rutas)


# --- B-2 · el cruce que atraviesa la frontera --------------------------------

def cruzar_b2(orquesta, sv1_vivo):
    """B-2 · que una intencion comprometida no deje de ser accion.

    Devuelve (estado, detalle). `estado` es "cumplida", "rota" o NO_COMPROBADA.
    """
    if not sv1_vivo:
        return NO_COMPROBADA, ("SV-1 esta detenido y la bandeja vive en su "
                               "almacen. El cruce atraviesa la frontera entre "
                               "AL-1 y AL-2, asi que no hay forma de hacerlo "
                               "desde fuera. No invalida la corrida (MI-5 solo "
                               "mira al receptor), pero se publica.")
    _, bandeja = protocolo.pedir(orquesta.url_sv1, "/bandeja", tiempo=60.0)
    _, recuento = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % orquesta.corrida_id)
    en_libro = {tuple(t) for t in recuento["ternas"]}
    pendientes = [e for e in bandeja["entradas"] if e["estado"] == "PENDIENTE"]
    entregadas_sin_fila = [
        e for e in bandeja["entradas"]
        if e["estado"] == "ENTREGADA"
        and (e["lote_id"], e["secuencia_apertura"], e["clase"]) not in en_libro]
    if pendientes or entregadas_sin_fila:
        return "rota", ("%d entradas PENDIENTE tras el drenaje · %d ENTREGADA sin "
                        "su fila en el libro" % (len(pendientes),
                                                 len(entregadas_sin_fila)))
    return "cumplida", ("%d entradas de bandeja, todas entregadas y con su fila "
                        "en el libro" % len(bandeja["entradas"]))


def demostrar_sec5(semilla):
    """Levanta una corrida, la drena, MATA SV-1 y emite el veredicto sin el.

    Devuelve un diccionario con el recuento obtenido con SV-1 detenido y el
    estado de B-2 en las dos situaciones.
    """
    carpeta = Path(tempfile.mkdtemp(prefix="sec5-"))
    o = Orquesta(carpeta, semilla, silencioso=True, repeticiones=1)
    try:
        o.crear_almacenes()
        o.arrancar()
        o.sembrar_sv2()
        o.emitir()
        protocolo.pedir(o.url_sv1, "/drenar", {}, tiempo=120.0)

        b2_con_sv1, detalle_con = cruzar_b2(o, sv1_vivo=True)
        o.detener_sv1()
        _, recuento = protocolo.pedir(
            o.url_sv2, "/recuentos?corrida_id=%s" % o.corrida_id)
        b2_sin_sv1, detalle_sin = cruzar_b2(o, sv1_vivo=False)
        return {
            "acciones_con_sv1_detenido": recuento["acciones"],
            "recuento_obtenido": True,
            "contado_como": recuento["contado_como"],
            "sv1_detenido": o.proceso_sv1.poll() is not None,
            "puerto_sv1_cerrado": not protocolo.puerto_ocupado(o.puerto_sv1),
            "b2_con_sv1": (b2_con_sv1, detalle_con),
            "b2_sin_sv1": (b2_sin_sv1, detalle_sin),
        }
    finally:
        o.parar()
        shutil.rmtree(carpeta, ignore_errors=True)


# --- la corrida de las dos mitades -------------------------------------------

def medir(script, argumentos, destino):
    orden = [sys.executable, "-u", script] + argumentos + ["--json", str(destino)]
    proceso = subprocess.run(orden, cwd=str(RAIZ), capture_output=True, text=True)
    if not Path(destino).exists():
        return None, proceso
    return json.loads(Path(destino).read_text(encoding="utf-8")), proceso


def main(argv=None):
    partes = argparse.ArgumentParser(description="El veredicto de la corrida · DP-02")
    partes.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    partes.add_argument("--repeticiones-c1a", type=int, default=2)
    partes.add_argument("--repeticiones-c1b", type=int, default=14)
    partes.add_argument("--sin-calibracion", action="store_true",
                        help="OMITE la calibracion a proposito. Tiene que salir "
                             "MEDICION INVALIDA, jamas APROBADO (T-23).")
    partes.add_argument("--evidencia", default=None,
                        help="carpeta donde guardar la salida de esta corrida")
    args = partes.parse_args(argv)

    trabajo = Path(tempfile.mkdtemp(prefix="veredicto-"))
    print("Midiendo las dos mitades de C1. Esto tarda: C1-B mata procesos de "
          "verdad.", flush=True)

    c1a, salida_a = medir("medir_c1a.py",
                          ["--semilla", str(args.semilla),
                           "--repeticiones", str(args.repeticiones_c1a)],
                          trabajo / "c1a.json")
    print("  C1-A: %s" % (c1a["veredicto"] if c1a else "NO PRODUJO RESUMEN"),
          flush=True)
    c1b, salida_b = medir("medir_c1b.py",
                          ["--semilla", str(args.semilla),
                           "--repeticiones", str(args.repeticiones_c1b)]
                          + (["--sin-calibracion"] if args.sin_calibracion else []),
                          trabajo / "c1b.json")
    print("  C1-B: %s" % (c1b["veredicto"] if c1b else "NO PRODUJO RESUMEN"),
          flush=True)
    print("  SEC-5: deteniendo SV-1 y pidiendo el veredicto sin el...", flush=True)
    sec5 = demostrar_sec5(args.semilla)

    faltas = []
    if c1a is None or c1b is None:
        faltas.append("MI-6 · alguna mitad no produjo resumen: la corrida no "
                      "puede decir que midio")
    else:
        faltas.extend("C1-A · " + f for f in c1a["faltas"])
        if c1b.get("calibracion") is None:
            faltas.append("MI-3 · la corrida no trae calibracion. Sin ella no "
                          "consta que la tanda entrara en la ventana, y una "
                          "ausencia de calibracion es MEDICION INVALIDA, jamas "
                          "APROBADO (T-23)")
        else:
            faltas.extend("C1-B · " + f for f in c1b["faltas"])
    if not sec5["recuento_obtenido"]:
        faltas.append("MI-5 · el recuento no se pudo leer en el receptor")

    hay_fallo = bool(c1a and c1b
                     and (c1a["divergencias"] or c1b["hechos_con_cero"]
                          or c1b["hechos_con_dos"] or c1b["acciones_no_actuables"]))

    if faltas:
        veredicto, codigo = "MEDICION INVALIDA", 2
    elif hay_fallo:
        veredicto, codigo = "FALLO", 1
    else:
        veredicto, codigo = "APROBADO", 0

    # ---------------------------------------------------------------- salida
    print()
    print("VEREDICTO DE LA CORRIDA: %s" % veredicto)
    print("=" * ANCHO)
    print("C1 · el orden de los eventos de un mismo envio se respeta siempre; y una")
    print("excursion se actua exactamente una vez, incluso si el proceso muere")
    print("entre decidir y registrar.")
    print()
    print("C1 MEDIDO SOBRE UN MECANISMO DIRECTO. Esta corrida no dice nada sobre")
    print("ningun otro mecanismo, y no lo dira hasta que exista y se mida.")
    print("=" * ANCHO)

    if c1a and c1b:
        print("semilla: %d" % args.semilla)
        print("digesto del guion · C1-A: %s" % c1a["digesto_guion"])
        print("digesto del guion · C1-B: %s" % c1b["digesto_guion"])

        titulo("LOS DENOMINADORES · se imprimen siempre, midiera o no")
        print("  C1-A · inversiones OBSERVADAS ....... %d"
              % c1a["inversiones_observadas"])
        print("  C1-A · inversiones DECISIVAS ........ %d   <- el denominador"
              % c1a["inversiones_decisivas"])
        print("  C1-A · envios con decisiva .......... %d" % c1a["envios_con_decisivas"])
        print("  C1-A · clases cubiertas ............. %d de 5" % c1a["clases_cubiertas"])
        for clase in sorted(c1a["por_clase"]):
            print("           %-6s %4d" % (clase, c1a["por_clase"][clase]))
        print("  C1-B · hechos actuables distintos ... %d" % c1b["hechos_actuables"])
        print("  C1-B · muertes ejecutadas ........... %d" % c1b["muertes"])
        print("  C1-B · muertes sin nada en curso .... %d" % c1b["muertes_sin_nada_en_curso"])

        titulo("LO MEDIDO")
        print("  C1-A · divergencias contra la referencia ....... %d"
              % c1a["divergencias"])
        print("  C1-B · acciones contadas en el receptor ........ %d" % c1b["acciones"])
        print("  C1-B · hechos con 0 acciones ................... %d"
              % c1b["hechos_con_cero"])
        print("  C1-B · hechos con >= 2 acciones ................ %d"
              % c1b["hechos_con_dos"])
        print("  C1-B · acciones sobre hechos NO actuables ...... %d"
              % c1b["acciones_no_actuables"])
        print("  C1-B · entregas repetidas absorbidas ........... %d"
              % c1b["entregas_repetidas"])

        titulo("LA CALIBRACION · sin ella no hay aprobado, solo invalidez")
        if c1b.get("calibracion") is None:
            print("  AUSENTE. Se omitio a proposito en esta corrida.")
            print("  Una ausencia de calibracion NO es un aprobado con reservas:")
            print("  es MEDICION INVALIDA. Sin ella no consta que las muertes")
            print("  cayeran dentro de la ventana, y un 100%% limpio no")
            print("  distinguiria «no pierde ni duplica» de «no se mato donde dolia».")
        else:
            cal = c1b["calibracion"]
            print("  C1-A · divergencias con el orden sin reconstruir ... %d"
                  % c1a["divergencias_calibracion"])
            print("  C1-B · M-1 marca antes de enviar · anomalias ....... %d"
                  % cal["M-1"]["anomalias"])
            print("  C1-B · M-2 receptor no idempotente · anomalias ..... %d"
                  % cal["M-2"]["anomalias"])
            print("  C1-B · anomalias totales .......................... %d"
                  % cal["anomalias_totales"])

    titulo("SEC-5 · el veredicto es computable con SV-1 DETENIDO")
    print("  SV-1 detenido ................ %s"
          % ("si" if sec5["sv1_detenido"] else "NO"))
    print("  su puerto ya no acepta ....... %s"
          % ("si" if sec5["puerto_sv1_cerrado"] else "NO"))
    print("  recuento obtenido sin el ..... %s (%d acciones)"
          % ("si" if sec5["recuento_obtenido"] else "NO",
             sec5["acciones_con_sv1_detenido"]))
    print("  contado como ................. %s" % sec5["contado_como"])
    rutas = de_donde_sale_el_recuento(RAIZ / "veredicto.py")
    print("  rutas que este veredicto pide: %s" % ", ".join(rutas))
    print("  el numero sale de /recuentos, que es de SV-2. Contar en /bandeja")
    print("  esta prohibido (T-06): pondria el recuento en el proceso que muere.")

    print()
    print("  B-2 · que una intencion comprometida no deje de ser accion")
    estado_con, detalle_con = sec5["b2_con_sv1"]
    estado_sin, detalle_sin = sec5["b2_sin_sv1"]
    print("     con SV-1 en pie ... %s · %s" % (estado_con.upper(), detalle_con))
    print("     con SV-1 detenido . %s" % estado_sin.upper())
    print("        %s" % detalle_sin)
    if estado_sin == NO_COMPROBADA:
        print("     Esta linea queda como NO COMPROBADA y se publica con esas")
        print("     palabras. Un APROBADO con lineas sin comprobar es mas debil")
        print("     y tiene que verse.")

    titulo("VEREDICTO DE LA CORRIDA: %s" % veredicto)
    if faltas:
        print("Que falto:")
        for falta in faltas:
            print("  · %s" % falta)
        print()
        print("UNA MEDICION INVALIDA NO ES UN DEFECTO DEL SISTEMA MEDIDO. Es que")
        print("esta corrida no consiguio medir, y por tanto no puede decir nada")
        print("-- ni bueno ni malo-- sobre si la afirmacion se sostiene.")
    elif hay_fallo:
        print("Hay divergencias o hechos actuables con 0 o con dos acciones.")
        print("Eso SI es un defecto del sistema medido.")

    print()
    print("Lo que esta corrida NO permite afirmar: nada sobre ningun mecanismo que")
    print("no sea el medido, y nada fuera de C1. No hay carga, no hay concurrencia")
    print("externa y no hay lector externo.")

    if args.evidencia:
        carpeta = Path(args.evidencia)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, dato in (("c1a.json", c1a), ("c1b.json", c1b),
                             ("sec5.json", sec5)):
            if dato is not None:
                (carpeta / nombre).write_text(
                    json.dumps(dato, indent=2, sort_keys=True), encoding="utf-8")
        if salida_a.stdout:
            (carpeta / "c1a-salida.txt").write_text(salida_a.stdout, encoding="utf-8")
        if salida_b.stdout:
            (carpeta / "c1b-salida.txt").write_text(salida_b.stdout, encoding="utf-8")
        print()
        print("Evidencia guardada en %s" % carpeta)

    shutil.rmtree(trabajo, ignore_errors=True)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
