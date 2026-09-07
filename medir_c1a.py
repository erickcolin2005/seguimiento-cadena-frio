"""C1-A · ¿se respeta el orden de los eventos de un mismo envio?

    python medir_c1a.py

Levanta el sistema, le entrega las lecturas **barajadas**, y compara lo que
concluye contra la referencia calculada sobre el guion en su orden real. La
afirmacion que se mide es la mitad de orden de D2:

    El orden de los eventos de un mismo envio se respeta siempre.

## Los dos numeros, y por que nunca se publica uno solo

**Inversiones observadas** son los pares que llegaron al reves. **Inversiones
decisivas** son las que, procesadas tal como llegan, produciran una conclusion
distinta. Barajar cuatrocientas lecturas puede no cambiar ninguna conclusion:
publicar solo el primer numero seria publicar algo que no se midio.

**El denominador de C1-A son las decisivas.** El otro se imprime al lado para que
se vea la diferencia, nunca en su lugar.

## Cuando esto NO es un aprobado

Si el instrumento no consiguio desordenar de forma que importara —menos de 30
inversiones decisivas, o en menos de 5 envios, o cubriendo menos de 3 clases—
el desenlace es **MEDICION INVALIDA (MI-1)**, no aprobado, por muy cero que sea
el numero de divergencias. Una corrida verde con cero inversiones decisivas no
vale: es el mismo error que seria contar «solicitudes lanzadas» como
«solicitudes simultaneas».

Codigos de salida:
    0  APROBADO
    1  FALLO              hay divergencias
    2  MEDICION INVALIDA  la corrida no consiguio medir
"""

import argparse
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

from levantar import Orquesta, SEMILLA_POR_DEFECTO
from sistema import desorden, protocolo, referencia, transporte

ANCHO = 78

# Umbrales de C1-A. No se tocan aqui: vienen de requerimientos §1.1 y del
# cinturon (U-03). Bajarlos requiere una excepcion firmada, no una edicion.
MINIMO_DECISIVAS = 30
MINIMO_ENVIOS = 5
MINIMO_CLASES = 3

# Los campos que se comparan. Son los que el sistema publica y la referencia
# calcula: si se comparara solo la aptitud, un lote con el acumulado equivocado
# y la misma aptitud pasaria por bueno.
CAMPOS = ("aptitud", "regla_aptitud", "acumulado_min", "clase_accion",
          "regla_clase_accion", "marca_secuencia", "provisional",
          "umbral_superado", "irreversible_activa")


def _normal(valor):
    """El almacen guarda los booleanos como enteros. Se comparan como enteros."""
    if isinstance(valor, bool):
        return int(valor)
    return valor


def emitir_desordenado(orquesta, ordenes, semilla):
    """Entrega las lecturas barajadas, y ademas entremezcladas entre envios.

    Dentro de cada envio se respeta el orden de llegada sorteado; entre envios,
    todo va entrelazado. RF-04 exige que el resultado sea el mismo aunque las
    lecturas de envios distintos se mezclen de cualquier manera.
    """
    cola = []
    for crudo in orquesta.guion["envios"]:
        lecturas = sorted(crudo["lecturas"], key=lambda l: l["produccion_min"])
        for posicion, origen in enumerate(ordenes[crudo["envio_id"]]):
            cola.append((crudo["envio_id"], posicion, lecturas[origen]))
    # Entrelazado global, estable dentro de cada envio: se baraja la cola entera
    # y despues se reordena solo por (envio, posicion de llegada).
    az = random.Random(semilla + 2)
    az.shuffle(cola)
    orden_interno = {}
    entrelazada = []
    for envio_id, posicion, lectura in cola:
        orden_interno.setdefault(envio_id, []).append((posicion, lectura))
    for envio_id in orden_interno:
        orden_interno[envio_id].sort(key=lambda x: x[0])
    punteros = {e: 0 for e in orden_interno}
    az2 = random.Random(semilla + 3)
    while any(punteros[e] < len(orden_interno[e]) for e in punteros):
        vivos = [e for e in punteros if punteros[e] < len(orden_interno[e])]
        elegido = az2.choice(vivos)
        posicion, lectura = orden_interno[elegido][punteros[elegido]]
        punteros[elegido] += 1
        entrelazada.append((elegido, lectura))

    emisor = transporte.construir_emisor(orquesta.clase_entrada, orquesta.url_sv1)
    enviadas = 0
    try:
        for envio_id, lectura in entrelazada:
            emisor.enviar({
                "corrida_id": orquesta.corrida_id, "envio_id": envio_id,
                "secuencia": lectura["secuencia"],
                "produccion_min": lectura["produccion_min"],
                "valor_c": lectura["valor_c"]})
            enviadas += 1
    finally:
        emisor.cerrar()
    if not emisor.entrega_veredicto:
        # Sin esto, C1-A compararia las conclusiones contra un prefijo de las
        # lecturas y contaria divergencias que solo dicen «todavia no habia
        # llegado». Seria el instrumento midiendose a si mismo.
        llego, cuantas = transporte.esperar_ingesta(orquesta.url_sv1, enviadas)
        if not llego:
            raise RuntimeError(
                "la ingesta no alcanzo las %d lecturas (llego a %d). MEDICION "
                "INVALIDA: no es que el sistema concluyera mal, es que la "
                "corrida no se completo." % (enviadas, cuantas))
    return enviadas


def comparar(ref, del_sistema):
    """Divergencias campo a campo entre la referencia y lo que concluyo SV-1."""
    divergencias = []
    lotes = set(ref["lotes"]) | set(del_sistema["lotes"])
    for lote_id in sorted(lotes):
        a = ref["lotes"].get(lote_id)
        b = del_sistema["lotes"].get(lote_id)
        if a is None or b is None:
            divergencias.append((lote_id, "existencia",
                                 "en la referencia" if a else "ausente",
                                 "en el sistema" if b else "ausente"))
            continue
        for campo in CAMPOS:
            va, vb = _normal(a.get(campo)), _normal(b.get(campo))
            if va != vb:
                divergencias.append((lote_id, campo, va, vb))
    return divergencias


def main(argv=None):
    partes = argparse.ArgumentParser(description="Mide C1-A · la mitad de orden")
    partes.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    partes.add_argument("--repeticiones", type=int, default=2,
                        help="vueltas a la baraja de perfiles · 4 envios cada una")
    partes.add_argument("--json", default=None,
                        help="escribe el resumen en ese fichero, para consolidar")
    partes.add_argument("--transporte", default="directo",
                        choices=("directo", "eventos"),
                        help="sobre que transporte se mide esta mitad")
    args = partes.parse_args(argv)

    directorio = Path(tempfile.mkdtemp(prefix="c1a-"))
    orquesta = Orquesta(directorio, args.semilla, silencioso=True,
                        repeticiones=args.repeticiones,
                        modo_transporte=args.transporte)
    ordenes = desorden.ordenes_de_llegada(orquesta.guion, args.semilla)

    # --- el analisis del desorden, antes de tocar el sistema -----------------
    analisis = [desorden.analizar_envio(crudo, ordenes[crudo["envio_id"]])
                for crudo in orquesta.guion["envios"]]
    observadas = sum(a["observadas"] for a in analisis)
    decisivas = sum(a["decisivas"] for a in analisis)
    sin_clase = sum(a["sin_clase"] for a in analisis)
    envios_con_decisivas = sum(1 for a in analisis if a["decisivas"])
    por_clase = {c: sum(a["por_clase"][c] for a in analisis) for c in desorden.CLASES}
    clases_cubiertas = sum(1 for n in por_clase.values() if n)

    # --- la corrida ----------------------------------------------------------
    ref = referencia.calcular(orquesta.guion)

    def una_corrida(sin_orden):
        """Levanta, entrega barajado y compara. Devuelve (divergencias, emitidas)."""
        carpeta = Path(tempfile.mkdtemp(prefix="c1a-"))
        o = Orquesta(carpeta, args.semilla, silencioso=True,
                     repeticiones=args.repeticiones, sin_orden=sin_orden,
                     modo_transporte=args.transporte)
        try:
            o.crear_almacenes()
            o.arrancar()
            o.sembrar_sv2()
            n = emitir_desordenado(o, ordenes, args.semilla)
            _, concluido = protocolo.pedir(o.url_sv1, "/conclusiones")
            return comparar(ref, concluido), n
        finally:
            o.parar()
            shutil.rmtree(carpeta, ignore_errors=True)

    divergencias, emitidas = una_corrida(sin_orden=False)
    # Calibracion: la misma medicion contra un SV-1 que NO reconstruye el orden.
    # Tiene que ponerse roja. Si no se pone, la medicion no distingue los dos
    # estados del mundo y su verde no significa nada.
    divergencias_mutante, _ = una_corrida(sin_orden=True)
    shutil.rmtree(directorio, ignore_errors=True)

    # --- el desenlace, y va en la PRIMERA linea (DP-02) ----------------------
    faltas = []
    if decisivas < MINIMO_DECISIVAS:
        faltas.append("inversiones decisivas: %d, hacen falta %d"
                      % (decisivas, MINIMO_DECISIVAS))
    if envios_con_decisivas < MINIMO_ENVIOS:
        faltas.append("envios con inversion decisiva: %d, hacen falta %d"
                      % (envios_con_decisivas, MINIMO_ENVIOS))
    if clases_cubiertas < MINIMO_CLASES:
        faltas.append("clases de inversion cubiertas: %d, hacen falta %d"
                      % (clases_cubiertas, MINIMO_CLASES))

    if not divergencias_mutante:
        faltas.append("la calibracion no se puso roja: con SV-1 mutado para NO "
                      "reconstruir el orden, la medicion sigue dando 0 "
                      "divergencias, asi que no distingue los dos estados del mundo")

    if faltas:
        veredicto, codigo = "MEDICION INVALIDA", 2
    elif divergencias:
        veredicto, codigo = "FALLO", 1
    else:
        veredicto, codigo = "APROBADO", 0

    if args.json:
        Path(args.json).write_text(json.dumps({
            "criterio": "C1-A", "veredicto": veredicto, "codigo": codigo,
            # Sin este campo, dos resumenes con el mismo veredicto y distinto
            # transporte serian indistinguibles, y la tabla publicada no podria
            # decir cual es cual. Va en el artefacto, no solo en la pantalla.
            "transporte": args.transporte,
            "alcance": transporte.frase_de_alcance(args.transporte),
            "semilla": args.semilla, "digesto_guion": orquesta.digesto,
            "envios": len(orquesta.guion["envios"]), "lotes": len(ref["lotes"]),
            "lecturas_emitidas": emitidas,
            "inversiones_observadas": observadas,
            "inversiones_decisivas": decisivas,
            "envios_con_decisivas": envios_con_decisivas,
            "clases_cubiertas": clases_cubiertas,
            "por_clase": por_clase, "sin_clase": sin_clase,
            "divergencias": len(divergencias),
            "divergencias_calibracion": len(divergencias_mutante),
            "faltas": faltas,
        }, indent=2, sort_keys=True), encoding="utf-8")

    print("VEREDICTO C1-A: %s" % veredicto)
    print("=" * ANCHO)
    print("C1-A · el orden de los eventos de un mismo envio se respeta siempre")
    print(transporte.frase_de_alcance(args.transporte))
    print("=" * ANCHO)
    print("semilla: %d · digesto del guion: %s" % (args.semilla, orquesta.digesto))
    print("envios: %d · lotes: %d · lecturas emitidas: %d"
          % (len(orquesta.guion["envios"]), len(ref["lotes"]), emitidas))

    print()
    print("-- LOS DOS DENOMINADORES · el de C1-A es el segundo %s" % ("-" * 12))
    print("  inversiones OBSERVADAS ....... %d   (pares que llegaron al reves)" % observadas)
    print("  inversiones DECISIVAS ........ %d   (las que solas cambiarian la conclusion)"
          % decisivas)
    print("  envios con al menos una decisiva %d   (hacen falta %d)"
          % (envios_con_decisivas, MINIMO_ENVIOS))
    print("  clases cubiertas ............. %d de 5 (hacen falta %d)"
          % (clases_cubiertas, MINIMO_CLASES))

    print()
    print("-- INVERSIONES DECISIVAS POR CLASE %s" % ("-" * 42))
    for clase in desorden.CLASES:
        print("  %-6s %-16s %4d" % (clase, desorden.REGLA_DE_CLASE[clase],
                                    por_clase[clase]))
    print("  " + "-" * (ANCHO - 4))
    print("  Una inversion puede caer en varias clases: se cuenta una vez en el")
    print("  total y una vez en cada clase. Por eso la suma por clases (%d) puede"
          % sum(por_clase.values()))
    print("  ser mayor que el total (%d). Sumarlas seria inventarse un tercer numero."
          % decisivas)
    if sin_clase:
        print("  decisivas que ninguna de las cinco clases nombra: %d · se declaran"
              % sin_clase)
        print("  en vez de repartirlas: inventarles clase seria peor que decirlo.")

    print()
    print("-- POR ENVIO %s" % ("-" * 64))
    print("  %-16s %8s %11s %11s" % ("ENVIO", "LECTURAS", "OBSERVADAS", "DECISIVAS"))
    for a in analisis:
        print("  %-16s %8d %11d %11d"
              % (a["envio_id"], a["lecturas"], a["observadas"], a["decisivas"]))

    print()
    print("-- DIVERGENCIAS CONTRA LA REFERENCIA %s" % ("-" * 40))
    print("  lotes comparados: %d · campos por lote: %d"
          % (len(ref["lotes"]), len(CAMPOS)))
    print("  divergencias: %d" % (len(divergencias) if divergencias is not None else -1))
    if divergencias:
        for lote_id, campo, va, vb in divergencias:
            print("     %s · %s · referencia=%r sistema=%r" % (lote_id, campo, va, vb))

    print()
    print("-- CALIBRACION · que la medicion pueda VERSE fallar %s" % ("-" * 25))
    print("  la misma corrida contra un SV-1 mutado para NO reconstruir el orden")
    print("  (trata la posicion de llegada como el instante en que ocurrio)")
    print("  divergencias con el mutante: %d" % len(divergencias_mutante))
    print("  -> la medicion se pone roja: %s"
          % ("SI" if divergencias_mutante else "NO"))
    print("  Sin esto, un cero de divergencias no distingue «el orden se respeta»")
    print("  de «la medicion no mira».")

    print()
    print("=" * ANCHO)
    print("VEREDICTO C1-A: %s" % veredicto)
    if faltas:
        print()
        print("Que falto:")
        for falta in faltas:
            print("  · %s" % falta)
        print()
        print("MEDICION INVALIDA NO ES UN DEFECTO DEL SISTEMA MEDIDO. Es que esta")
        print("corrida no consiguio desordenar de forma que importara, y por tanto no")
        print("puede decir nada -- ni bueno ni malo-- sobre si el orden se respeta.")
    print("=" * ANCHO)
    print()
    print("Lo que esta corrida NO mide: la mitad de cardinalidad de D2. Aqui no")
    print("muere ningun proceso. Eso es C1-B.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
