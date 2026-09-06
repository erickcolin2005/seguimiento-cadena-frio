"""C1-B · ¿se actua un hecho actuable exactamente una vez, aunque el proceso muera?

    python medir_c1b.py

La otra mitad de D2:

    Una excursion se actua exactamente una vez, incluso si el proceso muere
    entre decidir y registrar.

## El hecho actuable, y por que el denominador es ese

La unidad es **la terna**: `(lote, secuencia de apertura de la excursion, clase
de accion)`. Es de dominio, no de transporte, asi que sobrevive a cambiar de
transporte. **Exactamente 1** significa exactamente uno: **0 y 2 son fallos del
mismo rango**, y una accion sobre un hecho que NO era actuable tambien lo es.

## La ventana no se observa: se refuta

La ventana es el intervalo entre que la decision **queda comprometida** y que su
efecto **queda registrado en el receptor**, que es donde se cuenta. Por
definicion, en ese intervalo la decision **no ha dejado rastro donde se mide**.
Asi que preguntarle al receptor si la muerte cayo dentro no sirve: si hubiera
rastro, no habria ventana.

**Por eso la tanda se corre tres veces con las mismas muertes:**

| | Que es | Que tiene que pasar |
|---|---|---|
| **El sistema correcto** | Bandeja de salida + receptor idempotente | **Exactamente 1** accion por hecho actuable |
| **M-1 · marca antes de enviar** | Marca la entrada como entregada ANTES de entregarla | Pierde acciones: aparecen hechos con **0** |
| **M-2 · receptor no idempotente** | La terna deja de ser clave en el receptor | Duplica: aparecen hechos con **2** |

Si los mutantes **sobreviven limpios**, la tanda no entro en la ventana —mato
antes o despues— y **la medicion sobre el sistema correcto no vale aunque haya
salido verde**. Eso es MI-3, y es el equivalente exacto de *«si no hubo carrera,
la medicion es invalida aunque el sistema respondiera perfecto»*.

Hacen falta los **dos** mutantes, no uno: con uno solo se demostraria que la
tanda alcanza una de las dos formas de romperse, y la otra mitad quedaria sin
ejercer.

## Los dos instantes de muerte, y por que se alternan

    antes_de_enviar     comprometida la intencion, aun no ha salido a la red
    despues_de_enviar   el receptor ya contesto, la entrada sigue PENDIENTE

El segundo es el peor instante posible: los dos lados discrepan. Cada uno muerde
a un mutante distinto, asi que se alternan.

Codigos de salida:
    0  APROBADO
    1  FALLO              algun hecho actuable con 0 o con >= 2 acciones
    2  MEDICION INVALIDA  la tanda no demostro haber entrado en la ventana
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from levantar import Orquesta, SEMILLA_POR_DEFECTO
from sistema import protocolo, referencia

ANCHO = 78

# Umbrales de C1-B. Vienen de requerimientos §1.2 y del cinturon (U-04, U-05).
MINIMO_MUERTES = 50
MINIMO_HECHOS = 50
MINIMO_EN_VENTANA = 20
MINIMO_ANOMALIAS_POR_MUTANTE = 5      # U-05

INSTANTES = ("antes_de_enviar", "despues_de_enviar")


VERBOSO = False


def traza(texto):
    if VERBOSO:
        print("    · %s" % texto, flush=True)


def _recuento(orquesta):
    _, cuerpo = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % orquesta.corrida_id)
    return cuerpo


def correr_tanda(directorio, semilla, repeticiones, etiqueta,
                 marca_antes=False, receptor_no_idempotente=False):
    """Ingesta completa, tanda de muertes en la ventana, y recuento final.

    Devuelve (recuento, muertes, sin_nada_en_curso). `sin_nada_en_curso` cuenta
    las muertes que ocurrieron sin ningun hecho comprometido y pendiente de
    registrar: esas no interrumpieron nada y son MI-4.
    """
    carpeta = Path(tempfile.mkdtemp(prefix="c1b-%s-" % etiqueta))
    o = Orquesta(carpeta, semilla, silencioso=True, repeticiones=repeticiones,
                 marca_antes=marca_antes,
                 receptor_no_idempotente=receptor_no_idempotente)
    muertes = []
    sin_nada_en_curso = 0
    try:
        o.crear_almacenes()
        o.arrancar()
        o.sembrar_sv2()
        # Fase 1 · ingesta completa. Nadie drena todavia: al terminar, la bandeja
        # tiene una entrada comprometida por cada hecho actuable.
        o.emitir()

        # Fase 2 · la tanda. UNA muerte por hecho actuable, y despues se le
        # deja terminar. Matar en cada intento dejaria entradas que no llegan
        # nunca a marcarse entregadas -- la bandeja no se vaciaria jamas-- y la
        # tanda no mediria «se actua una vez», mediria «no se llega a actuar».
        _, inicial = protocolo.pedir(o.url_sv1, "/bandeja", tiempo=60.0)
        objetivos = [(e["lote_id"], e["secuencia_apertura"], e["clase"])
                     for e in inicial["entradas"] if e["estado"] == "PENDIENTE"]
        traza("hechos comprometidos en la bandeja: %d" % len(objetivos))

        for indice, objetivo in enumerate(objetivos):
            _, bandeja = protocolo.pedir(o.url_sv1, "/bandeja", tiempo=60.0)
            # MI-4 se registra por muerte, no se supone: cuantos hechos habia
            # comprometidos y sin registrar en el instante de matar.
            en_curso = bandeja["pendientes"]
            if en_curso == 0:
                sin_nada_en_curso += 1
            instante = INSTANTES[indice % len(INSTANTES)]
            try:
                # Espera corta a proposito: se le acaba de pedir al proceso que
                # se mate, asi que lo normal es que esta llamada NO reciba
                # respuesta. La peticion ya llego y SV-1 la esta ejecutando.
                protocolo.pedir(o.url_sv1, "/drenar",
                                {"una": True, "morir": instante,
                                 "terna": list(objetivo)}, tiempo=5.0)
            except Exception:                        # noqa: BLE001
                pass
            o.proceso_sv1.wait(timeout=30)
            muertes.append({"n": indice + 1, "instante": instante,
                            "en_curso": en_curso, "terna": objetivo,
                            "codigo": o.proceso_sv1.returncode})
            o.arrancar_sv1()                         # un proceso NUEVO
            # Y ahora se le deja terminar, sin matar. Si el mutante ya dio la
            # entrada por entregada, aqui no hay nada que entregar -- y ese
            # silencio es justo la anomalia que la calibracion busca.
            protocolo.pedir(o.url_sv1, "/drenar",
                            {"una": True, "terna": list(objetivo)}, tiempo=60.0)
            traza("muerte %d/%d en %s · %s" % (indice + 1, len(objetivos),
                                               instante, objetivo[0]))

        # Lo que quede pendiente tras la ultima muerte se entrega sin matar:
        # C1-B mide el estado final, no el estado a mitad de la tanda.
        protocolo.pedir(o.url_sv1, "/drenar", {}, tiempo=120.0)
        recuento = _recuento(o)
    finally:
        o.parar()
        shutil.rmtree(carpeta, ignore_errors=True)
    return recuento, muertes, sin_nada_en_curso


def acciones_por_hecho(recuento, hechos_esperados):
    """Cuantas acciones tiene cada hecho actuable, y los hechos que sobran."""
    cuenta = {}
    for terna in recuento["ternas"]:
        clave = tuple(terna)
        cuenta[clave] = cuenta.get(clave, 0) + 1
    con_cero = sorted(h for h in hechos_esperados if cuenta.get(h, 0) == 0)
    con_dos = sorted(h for h in hechos_esperados if cuenta.get(h, 0) >= 2)
    no_actuables = sorted(k for k in cuenta if k not in hechos_esperados)
    return cuenta, con_cero, con_dos, no_actuables


def main(argv=None):
    partes = argparse.ArgumentParser(description="Mide C1-B · exactamente una vez")
    partes.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    partes.add_argument("--repeticiones", type=int, default=14,
                        help="vueltas a la baraja · hacen falta >= 50 hechos actuables")
    partes.add_argument("--traza", action="store_true")
    args = partes.parse_args(argv)
    global VERBOSO
    VERBOSO = args.traza

    guion_ref = Orquesta(Path(tempfile.gettempdir()), args.semilla,
                         silencioso=True, repeticiones=args.repeticiones)
    ref = referencia.calcular(guion_ref.guion)
    hechos = referencia.ternas_como_conjunto(ref)

    print("Midiendo C1-B. Tres tandas con las mismas muertes: el sistema y sus dos")
    print("mutantes. Esto tarda -- son muchos procesos que nacen y mueren.", flush=True)

    correcto, muertes, sin_curso = correr_tanda(
        None, args.semilla, args.repeticiones, "correcto")
    m1, muertes_m1, _ = correr_tanda(
        None, args.semilla, args.repeticiones, "m1", marca_antes=True)
    m2, muertes_m2, _ = correr_tanda(
        None, args.semilla, args.repeticiones, "m2",
        receptor_no_idempotente=True)

    _, cero, dos, sobrantes = acciones_por_hecho(correcto, hechos)
    _, cero_m1, dos_m1, _ = acciones_por_hecho(m1, hechos)
    _, cero_m2, dos_m2, _ = acciones_por_hecho(m2, hechos)

    anomalias_m1 = len(cero_m1) + len(dos_m1)
    anomalias_m2 = len(cero_m2) + len(dos_m2)
    anomalias = anomalias_m1 + anomalias_m2

    # --- desenlace -----------------------------------------------------------
    faltas = []
    if len(muertes) < MINIMO_MUERTES:
        faltas.append("muertes ejecutadas: %d, hacen falta %d"
                      % (len(muertes), MINIMO_MUERTES))
    if len(hechos) < MINIMO_HECHOS:
        faltas.append("hechos actuables distintos: %d, hacen falta %d"
                      % (len(hechos), MINIMO_HECHOS))
    if anomalias < MINIMO_EN_VENTANA:
        faltas.append("MI-3 · anomalias en los mutantes: %d, hacen falta %d. La "
                      "tanda no demostro haber entrado en la ventana"
                      % (anomalias, MINIMO_EN_VENTANA))
    if anomalias_m1 < MINIMO_ANOMALIAS_POR_MUTANTE:
        faltas.append("U-05 · M-1 aporto %d anomalias, hacen falta %d"
                      % (anomalias_m1, MINIMO_ANOMALIAS_POR_MUTANTE))
    if anomalias_m2 < MINIMO_ANOMALIAS_POR_MUTANTE:
        faltas.append("U-05 · M-2 aporto %d anomalias, hacen falta %d"
                      % (anomalias_m2, MINIMO_ANOMALIAS_POR_MUTANTE))
    if sin_curso:
        faltas.append("MI-4 · %d muertes ocurrieron sin nada en curso" % sin_curso)

    if faltas:
        veredicto, codigo = "MEDICION INVALIDA", 2
    elif cero or dos or sobrantes:
        veredicto, codigo = "FALLO", 1
    else:
        veredicto, codigo = "APROBADO", 0

    print()
    print("VEREDICTO C1-B: %s" % veredicto)
    print("=" * ANCHO)
    print("C1-B · una excursion se actua exactamente una vez, incluso si el")
    print("proceso muere entre decidir y registrar.")
    print("Medido sobre un mecanismo directo. NO sobre ningun otro.")
    print("=" * ANCHO)
    print("semilla: %d · digesto del guion: %s" % (args.semilla, guion_ref.digesto))
    print("envios: %d · lotes: %d" % (len(guion_ref.guion["envios"]), len(ref["lotes"])))

    print()
    print("-- LOS DENOMINADORES %s" % ("-" * 56))
    print("  hechos actuables distintos ... %d   (hacen falta %d)"
          % (len(hechos), MINIMO_HECHOS))
    print("  muertes ejecutadas ........... %d   (hacen falta %d)"
          % (len(muertes), MINIMO_MUERTES))
    print("  muertes sin nada en curso .... %d   (MI-4: tienen que ser 0)" % sin_curso)
    for instante in INSTANTES:
        print("    en %-18s %d" % (instante,
                                   sum(1 for m in muertes if m["instante"] == instante)))

    print()
    print("-- EL SISTEMA CORRECTO %s" % ("-" * 54))
    print("  acciones contadas en SV-2 .... %d" % correcto["acciones"])
    print("  hechos con 0 acciones ........ %d %s"
          % (len(cero), cero[:4] if cero else ""))
    print("  hechos con >= 2 acciones ..... %d %s"
          % (len(dos), dos[:4] if dos else ""))
    print("  acciones sobre hechos NO actuables %d %s"
          % (len(sobrantes), sobrantes[:4] if sobrantes else ""))
    print("  entregas repetidas absorbidas . %d  (llegaron dos veces, cuentan una)"
          % correcto.get("entregas_repetidas", 0))

    print()
    print("-- LA CALIBRACION · la ventana se refuta, no se observa %s" % ("-" * 21))
    print("  %-30s %7s %7s %8s %9s"
          % ("TANDA", "ACCIONES", "0 ACC.", ">=2 ACC.", "ANOMALIAS"))
    print("  " + "-" * (ANCHO - 4))
    print("  %-30s %7d %7s %8s %9s" % ("el sistema correcto",
                                       correcto["acciones"], len(cero), len(dos), "-"))
    print("  %-30s %7d %7d %8d %9d" % ("M-1 · marca antes de enviar",
                                       m1["acciones"], len(cero_m1), len(dos_m1),
                                       anomalias_m1))
    print("  %-30s %7d %7d %8d %9d" % ("M-2 · receptor no idempotente",
                                       m2["acciones"], len(cero_m2), len(dos_m2),
                                       anomalias_m2))
    print("  " + "-" * (ANCHO - 4))
    print("  anomalias totales: %d  (hacen falta %d para demostrar la ventana)"
          % (anomalias, MINIMO_EN_VENTANA))
    print("  por mutante hacen falta %d (U-05): M-1 %s · M-2 %s"
          % (MINIMO_ANOMALIAS_POR_MUTANTE,
             "si" if anomalias_m1 >= MINIMO_ANOMALIAS_POR_MUTANTE else "NO",
             "si" if anomalias_m2 >= MINIMO_ANOMALIAS_POR_MUTANTE else "NO"))
    print()
    print("  Si los dos mutantes sobrevivieran limpios, la tanda habria matado")
    print("  antes o despues de la ventana y el verde del sistema correcto no")
    print("  significaria nada. Por eso esto no es un extra: es parte de la medida.")

    print()
    print("=" * ANCHO)
    print("VEREDICTO C1-B: %s" % veredicto)
    if faltas:
        print()
        print("Que falto:")
        for falta in faltas:
            print("  · %s" % falta)
        print()
        print("MEDICION INVALIDA NO ES UN DEFECTO DEL SISTEMA MEDIDO. Es que esta")
        print("corrida no consiguio matar donde tenia que matar, y por tanto no puede")
        print("decir nada -- ni bueno ni malo-- sobre si se actua exactamente una vez.")
    print("=" * ANCHO)
    print()
    print("Lo que esta corrida NO mide: la mitad de orden de D2. Aqui las lecturas")
    print("llegan en orden. Eso es C1-A.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
