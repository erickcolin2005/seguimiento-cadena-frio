"""Apagar una pieza y ver que cae.

La unidad de comparacion es la CONCLUSION COMPLETA en sus tres niveles, cada
nivel con su identificador de regla. Comparar solo la aptitud final haria que
un caso cuyo desenlace es permisivo -"dentro de rango", "apto", "valida"- no
pudiera caer nunca: quien ya pasaba, sigue pasando.

Un caso CAE si difiere cualquier campo de cualquier nivel, y difiere incluye
que el campo o su regla desaparezcan. Se distinguen dos formas de caer:

- **eco**: lo unico que cambia es que el identificador de la pieza apagada
  desaparece, y con el su veredicto. Es lo esperado al apagarla.
- **valor**: cambia un veredicto, una imputacion, una duracion, una clase de
  accion o una marca de secuencia. Esto es lo que la mutacion busca.

Las cuatro condiciones que se miden aqui son las de `cinturon-calidad.md` §4.4,
reabierto tras G3. Dos de ellas cambiaron de redaccion en esa reapertura y
conviene saber por que antes de leer el codigo:

- **(b) discriminacion** ya no exige que el discriminante caiga "con esta pieza
  y con ninguna otra". En un dominio encadenado eso es insatisfacible: apagar
  RC-04 deja sin excursiones a medio banco y tumba tambien el discriminante de
  RC-08. Lo que se exige es lo que la condicion siempre quiso decir: que la
  mutacion diga CUAL pieza falta. Se mide como firma unica.
- **(c) no contaminacion** se parte en dos. La lista de banco §8 es un limite
  INFERIOR por construccion -dice "casos que deben caer"-, asi que usarla
  ademas como limite superior era leerla en las dos direcciones a la vez.
  (c1) mide que la mutacion no se salga de su regla; (c2) mediria hasta donde
  llega su cascada, y NO es evaluable mientras el banco no declare la relacion
  regla->regla. No evaluable no es verde: sale INVALIDA con su motivo.
"""

import json
from pathlib import Path

from . import motor, verificar
from .piezas import Interruptores, regla_de
from .verificar import REGLA_DE_CAMPO

MAPA = Path(__file__).parent / "mapa-mutacion.json"

# Campo de veredicto -> campo de regla, y al reves.
CAMPO_DE_REGLA = {v: k for k, v in REGLA_DE_CAMPO.items()}


def _plano(conclusion):
    """La conclusion como un diccionario plano de ruta -> valor."""
    salida = {}
    for i, evaluacion in enumerate(conclusion.evaluaciones):
        for lote in evaluacion.lotes:
            base = "ev%d/%s" % (i, lote.lote_id)
            for campo, valor in lote.campos().items():
                salida["%s/%s" % (base, campo)] = valor
            for j, exc in enumerate(lote.excursiones):
                for campo, valor in exc.campos().items():
                    salida["%s/exc%d/%s" % (base, j, campo)] = valor
            for ver in lote.veredictos:
                for campo, valor in ver.campos().items():
                    salida["%s/lec%d/%s" % (base, ver.indice, campo)] = valor
    for k, accion in enumerate(conclusion.acciones):
        for campo, valor in accion.campos().items():
            salida["accion%d/%s" % (k, campo)] = valor
    return salida


def diferencias(conclusion_a, conclusion_b):
    """Lista de (ruta, valor con la pieza encendida, valor con ella apagada)."""
    a, b = _plano(conclusion_a), _plano(conclusion_b)
    salida = []
    for ruta in sorted(set(a) | set(b)):
        va, vb = a.get(ruta, "<ausente>"), b.get(ruta, "<ausente>")
        if va != vb:
            salida.append((ruta, va, vb))
    return salida


def _es_eco(ruta, va, vb, pieza, plano_apagado):
    """El eco es la desaparicion del identificador de la pieza apagada."""
    regla = regla_de(pieza)
    campo = ruta.rsplit("/", 1)[1]
    if campo.startswith("regla"):
        # El identificador de la pieza desaparece o se queda sin su mitad.
        return (isinstance(va, str) and regla in va.split("+")
                and (vb is None or vb == "<ausente>"
                     or (isinstance(vb, str) and regla not in vb.split("+"))))
    campo_regla = REGLA_DE_CAMPO.get(campo)
    if campo_regla and vb is None:
        # El veredicto desaparece junto con su regla, que era la de la pieza.
        ruta_regla = ruta.rsplit("/", 1)[0] + "/" + campo_regla
        return plano_apagado.get(ruta_regla) is None
    return False


def _reglas_que_firman(ruta, plano_conclusion):
    """Que reglas firman el valor de esa ruta, leidas de su campo de regla.

    Devuelve el conjunto vacio para los campos que no llevan regla pareja
    -`duracion`, `abierta`, `provisional`, `conocido_hasta`-. Un campo sin
    firma no se atribuye a nadie: inventarle un dueno seria la clase de
    supuesto que este banco existe para no hacer.
    """
    campo = ruta.rsplit("/", 1)[1]
    prefijo = ruta.rsplit("/", 1)[0]
    candidatas = []
    if campo.startswith("regla"):
        candidatas.append(ruta)
    else:
        campo_regla = REGLA_DE_CAMPO.get(campo)
        if campo_regla:
            candidatas.append(prefijo + "/" + campo_regla)
    if prefijo.startswith("accion"):
        candidatas.append(prefijo + "/regla_id")
    salida = set()
    for candidata in candidatas:
        valor = plano_conclusion.get(candidata)
        if isinstance(valor, str):
            salida.update(valor.split("+"))
    return salida


def comparar(conclusion_encendida, conclusion_apagada, pieza):
    """Todo lo que hace falta saber de un caso con una pieza apagada.

    Devuelve un diccionario con:
      cae          si difiere algo
      forma        "eco", "valor" o None
      movio        si algun campo firmado por la regla de la pieza difiere;
                   es lo que (c1) pregunta: la pieza dejo de producir algo AQUI
      firmados     lista de (ruta, reglas que la firman) por CADA campo que
                   cambio de VALOR, sin contar los ecos. Es la entrada de (c2),
                   y va campo a campo a proposito: la condicion dice "ningun
                   VALOR cambiado", no "ningun caso". Agregarlo por caso dejaria
                   que un valor acoplado se escondiera detras de los cambios
                   legitimos del mismo caso.
    """
    difs = diferencias(conclusion_encendida, conclusion_apagada)
    if not difs:
        return {"cae": False, "forma": None, "movio": False, "firmados": []}

    regla = regla_de(pieza)
    plano_a = _plano(conclusion_encendida)
    plano_b = _plano(conclusion_apagada)
    forma = "eco"
    movio = False
    firmados = []
    for ruta, va, vb in difs:
        firman = _reglas_que_firman(ruta, plano_a) | _reglas_que_firman(ruta, plano_b)
        if regla in firman:
            movio = True
        if not _es_eco(ruta, va, vb, pieza, plano_b):
            forma = "valor"
            if firman:
                firmados.append((ruta, firman))
    return {"cae": True, "forma": forma, "movio": movio, "firmados": firmados}


def clasificar(caso, pieza):
    """(cae, forma) para un caso suelto. Evalua dos veces; para la matriz
    completa usa `matriz`, que evalua 64 + 13x64 en vez de 13x64x2."""
    encendida = motor.evaluar_caso(caso, Interruptores())
    apagada = motor.evaluar_caso(caso, Interruptores([pieza]))
    resultado = comparar(encendida, apagada, pieza)
    return resultado["cae"], resultado["forma"]


def matriz(casos, piezas):
    """Una evaluacion con todo encendido y una por pieza.

    Devuelve (base, apagadas). `base` es imprescindible aparte porque (b)
    compara el discriminante de una pieza contra el de TODAS las demas, y eso
    no se puede hacer pieza a pieza.
    """
    base = {c.caso_id: motor.evaluar_caso(c, Interruptores()) for c in casos}
    apagadas = {}
    for pieza in piezas:
        interruptores = Interruptores([pieza])
        apagadas[pieza] = {c.caso_id: motor.evaluar_caso(c, interruptores)
                           for c in casos}
    return base, apagadas


def mapa_declarado():
    """La tabla de mutacion del banco (§8), transcrita como dato."""
    return json.loads(MAPA.read_text(encoding="utf-8"))


def revisar_pieza(pieza, casos, mapa, base, apagadas):
    """Las condiciones del criterio estricto de §4.4, para una pieza.

    (a)  sensibilidad   caen todos los casos de la lista de §8 de la pieza.
    (b)  discriminacion el discriminante cae Y su conclusion con esta pieza
                        apagada es distinta de la que da cualquier otra pieza.
    (c1) localizacion   todo caso que cambia de VALOR es un caso donde la propia
                        regla de la pieza dejo de firmar algo. Los tres
                        controles quedan fuera: no pertenecen a ninguna pieza
                        (§4.4 punto 1).
    (c2) extension      hasta donde puede llegar la cascada. Devuelve None
                        -no evaluable- mientras `cascada_declarada` sea null en
                        el mapa. None NO es verde.
    """
    esperados = mapa["piezas"][pieza]
    lista = esperados["casos"]
    discriminante = esperados["discriminante"]
    cascada = mapa.get("cascada_declarada")

    lecturas = {}
    for caso in casos:
        lecturas[caso.caso_id] = comparar(
            base[caso.caso_id], apagadas[pieza][caso.caso_id], pieza)

    caidos = {cid: r["forma"] for cid, r in lecturas.items() if r["cae"]}

    # (a) ---------------------------------------------------------------------
    faltan = [c for c in lista if c not in caidos]

    # (b) ---------------------------------------------------------------------
    mia = verificar.digesto(apagadas[pieza][discriminante])
    cae_el_discriminante = mia != verificar.digesto(base[discriminante])
    colisiones = sorted(otra for otra in apagadas
                        if otra != pieza
                        and verificar.digesto(apagadas[otra][discriminante]) == mia)

    # (c1) --------------------------------------------------------------------
    controles = {c.caso_id for c in casos if c.control}
    sin_localizar = sorted(
        cid for cid, r in lecturas.items()
        if cid not in controles and r["forma"] == "valor" and not r["movio"])

    # (c2) --------------------------------------------------------------------
    if cascada is None:
        extension, fuera_de_cascada = None, []
    else:
        permitidas = {regla_de(pieza)} | set(cascada.get(regla_de(pieza), ()))
        # Campo a campo: basta UN valor firmado solo por reglas que la cascada
        # declarada no alcanza para que la pieza no cumpla (c2).
        fuera_de_cascada = sorted(
            cid for cid, r in lecturas.items()
            if cid not in controles
            and any(not (firman & permitidas) for _, firman in r["firmados"]))
        extension = not fuera_de_cascada

    return {
        "pieza": pieza,
        "caidos": caidos,
        "sensibilidad": not faltan,
        "faltan": faltan,
        "discriminante": discriminante,
        "discriminacion": cae_el_discriminante and not colisiones,
        "cae_el_discriminante": cae_el_discriminante,
        "colisiones": colisiones,
        "localizacion": not sin_localizar,
        "sin_localizar": sin_localizar,
        "extension": extension,
        "fuera_de_cascada": fuera_de_cascada,
        "fuera_de_lista": sorted(cid for cid, forma in caidos.items()
                                 if cid not in lista and forma == "valor"
                                 and cid not in controles),
    }


# --- Que las condiciones puedan ponerse ROJAS --------------------------------
#
# Una condicion que nunca ha fallado no esta demostrado que pueda fallar. Las
# dos que se reescribieron en la reapertura de §4.4 se ejercen aqui contra un
# defecto fabricado a proposito, y la corrida publica el resultado. Es el mismo
# principio del mecanismo 7 de §3.1, aplicado dentro de CT-3.

FUNDIR_RC08 = ("RC-08-umbral", "RC-08-irreversibilidad")


def diente_de_discriminacion(casos, mapa, piezas):
    """RC-08 implementada como UNA sola pieza: (b) tiene que ponerse roja.

    Es el defecto que P4 encontro -una regla implementada dos veces con la
    mutacion parcial dejando media viva- y es el unico que (b) existe para
    cazar. Se simula haciendo que apagar cualquiera de las dos mitades apague
    las dos.
    """
    por_id = {c.caso_id: c for c in casos}
    fundir = set(FUNDIR_RC08)

    def evaluar(caso, pieza):
        apagadas = fundir if pieza in fundir else {pieza}
        return motor.evaluar_caso(caso, Interruptores(apagadas))

    lineas = []
    rojas = 0
    for pieza in FUNDIR_RC08:
        discriminante = mapa["piezas"][pieza]["discriminante"]
        caso = por_id[discriminante]
        mia = verificar.digesto(evaluar(caso, pieza))
        colisiones = sorted(otra for otra in piezas if otra != pieza
                            and verificar.digesto(evaluar(caso, otra)) == mia)
        rojas += bool(colisiones)
        lineas.append("%s (disc %s): firma unica %s%s"
                      % (pieza, discriminante, "NO" if colisiones else "SI",
                         (" · colisiona con " + ", ".join(colisiones))
                         if colisiones else ""))
    return rojas == len(FUNDIR_RC08), lineas


def diente_de_extension(casos, mapa, piezas, base, apagadas):
    """(c2) contra una cascada declarada VACIA: tiene que ponerse roja.

    Se ejerce aunque `cascada_declarada` sea null, porque el diente trae su
    propia cascada. Sin esto, el dia que llegue el dato de `analyst-agent` la
    condicion saldria verde sin que nadie hubiera visto nunca que puede salir
    roja — y una condicion que no se ha visto fallar no esta demostrado que
    mida. Con la cascada vacia, NINGUNA regla alimenta a ninguna otra, asi que
    toda cascada real del dominio tiene que aparecer como fuera de lo declarado.
    """
    vacia = dict(mapa)
    vacia["cascada_declarada"] = {}
    rojas = []
    for pieza in piezas:
        revision = revisar_pieza(pieza, casos, vacia, base, apagadas)
        if revision["extension"] is False:
            rojas.append((pieza, len(revision["fuera_de_cascada"])))
    return bool(rojas), rojas


def diente_de_localizacion(casos, base, pieza="RC-10", arrastrada="RC-03"):
    """Apagar una pieza arrastra ademas a otra regla: (c1) tiene que ponerse roja.

    RC-10 solo firma acciones, asi que en los casos sin accion su salida no se
    mueve. Si al apagarla cambian valores de todas formas, la mutacion se salio
    de su regla, y eso es exactamente lo que (c1) mide.
    """
    interruptores = Interruptores([pieza, arrastrada])
    controles = {c.caso_id for c in casos if c.control}
    sueltos = []
    for caso in casos:
        if caso.caso_id in controles:
            continue
        resultado = comparar(base[caso.caso_id],
                             motor.evaluar_caso(caso, interruptores), pieza)
        if resultado["forma"] == "valor" and not resultado["movio"]:
            sueltos.append(caso.caso_id)
    return bool(sueltos), sueltos
