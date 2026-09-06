"""Ejecuta el banco de reglas de cadena de frio entero.

    python ejecutar.py

Sin argumentos, sin instalar nada, sin imagen y sin credencial. Publica la
tabla de resultados con los fallos dentro: no se promedia ni se descarta.

Codigos de salida:
    0  VERDE     los 64 casos pasan y las cinco comprobaciones tambien
    1  ROJO      algun caso falla, o falla una comprobacion del sistema
    2  INVALIDO  el banco pasa, pero una comprobacion no se puede evaluar con
                 el mapa de mutacion vigente. No es un verde y no es un rojo.
"""
# La comprobacion 3 mide las cuatro condiciones de cinturon-calidad.md §4.4
# tras su reapertura: (a) sensibilidad, (b) discriminacion por firma unica,
# (c1) localizacion y (c2) extension de la cascada. La (c2) NO es evaluable
# hoy y por eso esta corrida sigue terminando en INVALIDO, con un motivo mas
# estrecho que antes: falta un dato del banco, no falla el codigo.

import dataclasses
import sys

from banco import casos as modulo_casos
from banco import comprobaciones, motor, mutacion, reloj, verificar
from banco.piezas import PIEZAS, Interruptores

ANCHO = 78

# Los tres controles corren y tienen que dar su desenlace como cualquier otro
# caso, pero no se atribuyen a ninguna regla: por eso la corrida publica dos
# numeros y nunca uno solo.
CONTROLES = ("O-07", "X-05", "X-06")


def titulo(texto):
    print()
    print("=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


def apartado(texto):
    print()
    print("-- %s %s" % (texto, "-" * max(0, ANCHO - len(texto) - 4)))


def ejecutar_banco():
    """Evalua los 64 casos con las trece piezas encendidas."""
    casos = modulo_casos.cargar()
    conclusiones = {}
    resultados = []
    for caso in casos:
        conclusion = motor.evaluar_caso(caso, Interruptores())
        conclusiones[caso.caso_id] = conclusion
        por_llegada = None
        if "difiere_por_llegada" in caso.esperado:
            variante = dataclasses.replace(
                caso, envio=modulo_casos.envio_por_orden_de_llegada(caso.envio))
            por_llegada = motor.evaluar_caso(variante, Interruptores())
        fallos = verificar.verificar(caso, conclusion, por_llegada)
        resultados.append((caso, conclusion, fallos))
    return casos, conclusiones, resultados


def resumen_de(caso, conclusion):
    """Una linea con lo que concluyo el caso, con sus reglas."""
    lote = conclusion.evaluaciones[-1].lotes[0]
    partes = []
    if lote.aptitud:
        partes.append("%s·%s" % (lote.aptitud, lote.regla_aptitud))
    if lote.acumulado is not None:
        partes.append("acum %s min" % lote.acumulado)
    if lote.clase_accion:
        partes.append("%s·%s" % (lote.clase_accion, lote.regla_clase_accion))
    if conclusion.acciones:
        partes.append("%d accion(es)" % len(conclusion.acciones))
    return " · ".join(partes)


def imprimir_tabla(resultados):
    print()
    print("%-6s %-8s %-46s %s" % ("CASO", "DESENL.", "CONCLUSION DEL PRIMER LOTE",
                                  "REGLAS DECLARADAS"))
    print("-" * ANCHO)
    for caso, conclusion, fallos in resultados:
        marca = "PASA" if not fallos else "FALLA"
        reglas = ",".join(caso.reglas) if caso.reglas else "(control)"
        print("%-6s %-8s %-46s %s"
              % (caso.caso_id, marca, resumen_de(caso, conclusion)[:46], reglas))
    print("-" * ANCHO)

    con_fallo = [(c, f) for c, _, f in resultados if f]
    if con_fallo:
        apartado("LOS FALLOS, DENTRO DE LA TABLA Y SIN PROMEDIAR")
        for caso, fallos in con_fallo:
            print("  %s · %s" % (caso.caso_id, caso.titulo))
            for f in fallos:
                print("      %s" % f)
    else:
        print("  Ningun caso fallo en esta corrida.")


def main():
    rojo = []
    invalido = []

    titulo("BANCO DE REGLAS DE CADENA DE FRIO · PL-1 · M1")
    print("T0 de esta corrida: %s (instante de referencia, truncado al minuto)"
          % reloj.T0.strftime("%Y-%m-%d %H:%M"))
    print("Todos los tiempos de los casos son T0 + n minutos, derivados aqui.")
    print("Runtime: Python %s · solo biblioteca estandar" % sys.version.split()[0])

    # --- 1 · los casos --------------------------------------------------------
    titulo("1 · LOS 64 CASOS, COMO DATOS")
    casos, conclusiones, resultados = ejecutar_banco()
    imprimir_tabla(resultados)

    fallidos = [c.caso_id for c, _, f in resultados if f]
    atribuibles = [c for c in casos if not c.control]
    apartado("LOS DOS DENOMINADORES · publicar uno solo seria inflar o desinflar")
    print("  casos ejecutados ............ %d" % len(casos))
    print("  atribuibles a una regla ..... %d" % len(atribuibles))
    print("  controles (no atribuibles) .. %d  (%s)"
          % (len(casos) - len(atribuibles), ", ".join(CONTROLES)))
    print("  superados ................... %d" % (len(casos) - len(fallidos)))
    print("  fallidos .................... %d %s"
          % (len(fallidos), ("· " + ", ".join(fallidos)) if fallidos else ""))
    if fallidos:
        rojo.append("%d casos del banco fallan" % len(fallidos))

    # --- 2 · determinismo -----------------------------------------------------
    titulo("2 · COMPROBACION 1 · DETERMINISMO")
    pasa, lineas = comprobaciones.determinismo(casos, conclusiones)
    for l in lineas:
        print("  %s" % l)
    print("  -> %s" % ("PASA" if pasa else "FALLA"))
    if not pasa:
        rojo.append("el banco no es determinista")

    # --- 3 · ninguna conclusion sin su regla ----------------------------------
    titulo("3 · COMPROBACION 2 · NINGUNA CONCLUSION PASA SIN NOMBRAR SU REGLA")
    pasa, lineas = comprobaciones.conclusion_nombra_su_regla(casos, conclusiones)
    for l in lineas:
        print("  %s" % l)
    print("  -> %s" % ("PASA" if pasa else "FALLA"))
    if not pasa:
        rojo.append("una conclusion sin regla cuenta como conclusion")

    # --- 4 · discriminacion ---------------------------------------------------
    titulo("4 · COMPROBACION 3 · DISCRIMINACION AL APAGAR PIEZAS")
    pasa_piezas, lineas = comprobaciones.piezas_declaradas()
    for l in lineas:
        print("  %s" % l)
    if not pasa_piezas:
        rojo.append("las piezas apagables no son trece")

    mapa = mutacion.mapa_declarado()
    base, apagadas = mutacion.matriz(casos, PIEZAS)
    revisiones = []
    print()
    print("  %-24s %-5s %-5s %-5s %-5s %s"
          % ("PIEZA APAGADA", "(a)", "(b)", "(c1)", "(c2)", "CAEN · FUERA DE §8"))
    print("  " + "-" * (ANCHO - 2))
    for pieza in PIEZAS:
        revision = mutacion.revisar_pieza(pieza, casos, mapa, base, apagadas)
        revisiones.append(revision)
        print("  %-24s %-5s %-5s %-5s %-5s %d de la lista, %d fuera por valor"
              % (pieza,
                 "SI" if revision["sensibilidad"] else "NO",
                 "SI" if revision["discriminacion"] else "NO",
                 "SI" if revision["localizacion"] else "NO",
                 "n/e" if revision["extension"] is None
                 else ("SI" if revision["extension"] else "NO"),
                 len(mapa["piezas"][pieza]["casos"]),
                 len(revision["fuera_de_lista"])))
    print("  " + "-" * (ANCHO - 2))
    print("  (a)  sensibilidad: caen TODOS los casos de la lista de §8 de la pieza")
    print("  (b)  discriminacion: el discriminante cae Y su conclusion con esta")
    print("       pieza apagada es distinta de la de las otras doce")
    print("  (c1) localizacion: todo caso que cambia de VALOR es un caso donde la")
    print("       propia regla de la pieza dejo de firmar algo")
    print("  (c2) extension: ningun valor cambiado lo firma una regla que la")
    print("       cascada declarada por el banco no alcanza")
    print("  La columna 'fuera de §8' es informativa: §8 es limite INFERIOR, no")
    print("  superior. Caer fuera de la lista no es, por si solo, un defecto.")

    sensibles = [r for r in revisiones if r["sensibilidad"]]
    discriminan = [r for r in revisiones if r["discriminacion"]]
    localizadas = [r for r in revisiones if r["localizacion"]]
    extendidas = [r for r in revisiones if r["extension"]]
    no_evaluables = [r for r in revisiones if r["extension"] is None]
    apartado("RESULTADO DE LAS TRECE PIEZAS")
    print("  (a)  sensibilidad ..... %d/13" % len(sensibles))
    print("  (b)  discriminacion ... %d/13" % len(discriminan))
    print("  (c1) localizacion ..... %d/13" % len(localizadas))
    print("  (c2) extension ........ %d/13 medidas · %d NO EVALUABLES"
          % (13 - len(no_evaluables), len(no_evaluables)))
    for revision in revisiones:
        if not revision["discriminacion"] and revision["colisiones"]:
            print("      %s: su discriminante %s da la misma conclusion que con %s"
                  % (revision["pieza"], revision["discriminante"],
                     ", ".join(revision["colisiones"])))
        if not revision["localizacion"]:
            print("      %s cambia valores en %d casos donde su regla no firma nada: %s"
                  % (revision["pieza"], len(revision["sin_localizar"]),
                     ", ".join(revision["sin_localizar"][:8])
                     + (" ..." if len(revision["sin_localizar"]) > 8 else "")))
    if no_evaluables:
        print("      motivo de (c2): %s" % mapa["por_que_null"].split(". ")[0] + ".")

    apartado("QUE LAS CONDICIONES PUEDAN PONERSE ROJAS · dientes del criterio")
    muerde_b, lineas_b = mutacion.diente_de_discriminacion(casos, mapa, PIEZAS)
    print("  (b) contra RC-08 implementada como UNA sola pieza:")
    for l in lineas_b:
        print("      %s" % l)
    print("      -> (b) se pone roja en las dos mitades: %s"
          % ("SI" if muerde_b else "NO"))
    muerde_c1, sueltos = mutacion.diente_de_localizacion(casos, base)
    print("  (c1) contra un acoplamiento fabricado (apagar RC-10 arrastra RC-03):")
    print("      %d casos cambian de valor sin que RC-10 firme nada: %s%s"
          % (len(sueltos), ", ".join(sueltos[:8]),
             " ..." if len(sueltos) > 8 else ""))
    print("      -> (c1) se pone roja: %s" % ("SI" if muerde_c1 else "NO"))
    muerde_c2, rojas_c2 = mutacion.diente_de_extension(
        casos, mapa, PIEZAS, base, apagadas)
    print("  (c2) contra una cascada declarada VACIA · con la cascada vacia")
    print("       ninguna regla alimenta a otra, asi que toda cascada real del")
    print("       dominio tiene que aparecer como fuera de lo declarado:")
    print("      %d piezas se ponen rojas: %s"
          % (len(rojas_c2), ", ".join("%s (%d)" % r for r in rojas_c2[:6])
             + (" ..." if len(rojas_c2) > 6 else "")))
    print("      -> (c2) se pone roja: %s" % ("SI" if muerde_c2 else "NO"))

    if len(sensibles) < 13 or len(discriminan) < 13 or len(localizadas) < 13:
        rojo.append("hay piezas sin sensibilidad, sin discriminante o sin localizacion")
    if not (muerde_b and muerde_c1 and muerde_c2):
        rojo.append("una condicion de mutacion no se pudo poner roja: no mide nada")
    if no_evaluables:
        invalido.append(
            "la condicion (c2) -extension de la cascada- no es evaluable: el banco "
            "no declara la relacion regla->regla que alimenta, y el orden numerico "
            "de §3 no sirve de sustituto (§3 y §7 lo dicen, y medirlo lo confirma). "
            "%d de 13 piezas sin (c2). Ver banco/NOTAS-IMPLEMENTACION.md"
            % len(no_evaluables))

    # --- 5 · el tipo de producto vive en el lote ------------------------------
    titulo("5 · COMPROBACION 4 · tipo_producto VIVE EN EL LOTE")
    pasa, lineas = comprobaciones.esquema_por_lote()
    for l in lineas:
        print("  %s" % l)
    print("  -> %s" % ("PASA" if pasa else "FALLA"))
    if not pasa:
        rojo.append("evaluar por envio se puede escribir")

    # --- 6 · un solo comando --------------------------------------------------
    titulo("6 · COMPROBACION 5 · UN SOLO COMANDO, SIN DEPENDENCIAS")
    pasa, lineas = comprobaciones.solo_biblioteca_estandar()
    for l in lineas:
        print("  %s" % l)
    print("  comando: python ejecutar.py")
    print("  -> %s" % ("PASA" if pasa else "FALLA"))
    if not pasa:
        rojo.append("el banco depende de algo que hay que instalar")

    # --- desenlace ------------------------------------------------------------
    titulo("DESENLACE")
    if rojo:
        print("DESENLACE: ROJO")
        for r in rojo:
            print("  · %s" % r)
        codigo = 1
    elif invalido:
        print("DESENLACE: INVALIDO  (no es un verde)")
        for i in invalido:
            print("  · %s" % i)
        codigo = 2
    else:
        print("DESENLACE: VERDE")
        codigo = 0
    print()
    print("Casos ejecutados: %d · atribuibles a regla: %d · superados: %d · fallidos: %d"
          % (len(casos), len(atribuibles), len(casos) - len(fallidos), len(fallidos)))
    print("Lo que esta corrida permite afirmar: que las reglas de cadena de frio")
    print("viven en el codigo y se ejecutan. NADA sobre orden ni sobre no-duplicacion.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
