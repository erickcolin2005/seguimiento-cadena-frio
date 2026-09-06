"""Compara la conclusion obtenida con el desenlace que declara el caso.

Dos exigencias que no son la misma:

1. El desenlace tiene que coincidir con el declarado.
2. **Tiene que nombrar su regla.** Un campo con el valor correcto y sin
   identificador de regla NO cuenta como conclusion, y el caso falla. Concluir
   bien por la regla equivocada tambien es fallo.
"""

from . import reloj

# Cada campo con veredicto tiene su campo de regla. Si el veredicto se afirma y
# la regla no esta, no hay conclusion.
REGLA_DE_CAMPO = {
    "atribucion": "regla_atribucion",
    "imputacion": "regla_imputacion",
    "validez": "regla_validez",
    "situacion": "regla_situacion",
    "aptitud": "regla_aptitud",
    "acumulado": "regla_acumulado",
    "clase_accion": "regla_clase_accion",
    "marca_secuencia": "regla_marca_secuencia",
    "marca_excursiones": "regla_marca_excursiones",
    "cerrada_en": "regla_cierre_conclusion",
    "apertura": "regla_apertura",
    "cierre": "regla_cierre",
}

# 'conocido_hasta' se compara como desplazamiento igual que los demas instantes,
# pero NO esta en REGLA_DE_CAMPO: no es un veredicto y no tiene regla que nombrar.
CAMPOS_INSTANTE = ("produccion", "apertura", "cierre", "cerrada_en",
                   "conocido_hasta")


def _valor(objeto, campo):
    valor = getattr(objeto, campo)
    if campo in CAMPOS_INSTANTE:
        return reloj.desplazamiento(valor)
    return valor


def _comparar(objeto, esperado, etiqueta, fallos, saltar=()):
    for campo, esperado_valor in esperado.items():
        if campo in saltar:
            continue
        if not hasattr(objeto, campo):
            fallos.append("%s: el campo '%s' no existe en la conclusion" % (etiqueta, campo))
            continue
        obtenido = _valor(objeto, campo)
        if obtenido != esperado_valor:
            fallos.append("%s: %s esperado %r, obtenido %r"
                          % (etiqueta, campo, esperado_valor, obtenido))
        # Criterio 2: el veredicto sin su regla no cuenta como conclusion. Un
        # campo que se espera ausente no tiene regla que nombrar.
        campo_regla = REGLA_DE_CAMPO.get(campo)
        if campo_regla and campo_regla not in esperado and esperado_valor is not None:
            if getattr(objeto, campo_regla) is None:
                fallos.append("%s: '%s' concluye sin nombrar su regla (%s ausente)"
                              % (etiqueta, campo, campo_regla))


def _reglas_nombradas(conclusion):
    nombradas = set()
    for evaluacion in conclusion.evaluaciones:
        for lote in evaluacion.lotes:
            for campo, valor in lote.campos().items():
                if campo.startswith("regla") and valor:
                    nombradas.update(valor.split("+"))
            for exc in lote.excursiones:
                for campo, valor in exc.campos().items():
                    if campo.startswith("regla") and valor:
                        nombradas.update(valor.split("+"))
            for ver in lote.veredictos:
                for campo, valor in ver.campos().items():
                    if campo.startswith("regla") and valor:
                        nombradas.update(valor.split("+"))
    for accion in conclusion.acciones:
        if accion.regla_id:
            nombradas.add(accion.regla_id)
    return nombradas


def verificar(caso, conclusion, conclusion_por_llegada=None):
    """Devuelve la lista de fallos del caso. Vacia significa superado."""
    fallos = []
    esperado = caso.esperado

    for pedido in esperado.get("lecturas", ()):
        indice_ev = pedido.get("evaluacion", 0)
        lote = conclusion.lote(pedido["lote"], indice_ev)
        candidatos = [v for v in lote.veredictos if v.indice == pedido["indice"]]
        if not candidatos:
            fallos.append("lectura %d de %s: no hay veredicto"
                          % (pedido["indice"], pedido["lote"]))
            continue
        _comparar(candidatos[0], pedido,
                  "lectura %d/%s" % (pedido["indice"], pedido["lote"]), fallos,
                  saltar=("lote", "indice", "evaluacion"))

    for pedido in esperado.get("lotes", ()):
        indice_ev = pedido.get("evaluacion", 0)
        lote = conclusion.lote(pedido["lote"], indice_ev)
        _comparar(lote, pedido, "lote %s" % pedido["lote"], fallos,
                  saltar=("lote", "evaluacion"))

    for pedido in esperado.get("excursiones", ()):
        indice_ev = pedido.get("evaluacion", 0)
        lote = conclusion.lote(pedido["lote"], indice_ev)
        reales = [e for e in lote.excursiones if not e.transitoria]
        cuales = lote.excursiones if pedido.get("incluir_transitorias") else reales
        indice = pedido.get("indice", 0)
        if len(cuales) <= indice:
            fallos.append("lote %s: se esperaba una excursion en la posicion %d y hay %d"
                          % (pedido["lote"], indice, len(cuales)))
            continue
        _comparar(cuales[indice], pedido, "excursion %d/%s" % (indice, pedido["lote"]),
                  fallos, saltar=("lote", "indice", "evaluacion", "incluir_transitorias"))

    if "sin_excursiones" in esperado:
        for lote_id in esperado["sin_excursiones"]:
            lote = conclusion.lote(lote_id)
            reales = [e for e in lote.excursiones if not e.transitoria]
            if reales:
                fallos.append("lote %s: se esperaba ninguna excursion y hay %d"
                              % (lote_id, len(reales)))

    acciones = esperado.get("acciones")
    if acciones is not None:
        if "total" in acciones and len(conclusion.acciones) != acciones["total"]:
            fallos.append("acciones: esperadas %d, obtenidas %d"
                          % (acciones["total"], len(conclusion.acciones)))
        for lote_id, cuantas in acciones.get("por_lote", {}).items():
            obtenidas = len(conclusion.acciones_de(lote_id))
            if obtenidas != cuantas:
                fallos.append("acciones de %s: esperadas %d, obtenidas %d"
                              % (lote_id, cuantas, obtenidas))
        for clase in acciones.get("clases", ()):
            if clase not in [a.clase for a in conclusion.acciones]:
                fallos.append("acciones: falta una accion de clase %s" % clase)
        # Criterio 2 tambien aqui: una accion sin regla no es una conclusion.
        if acciones.get("total", 0) > 0 or acciones.get("por_lote"):
            for accion in conclusion.acciones:
                if accion.regla_id is None:
                    fallos.append("accion sobre %s: sin identificador de regla"
                                  % accion.lote_id)

    if "difiere_por_llegada" in esperado and conclusion_por_llegada is not None:
        difiere = digesto(conclusion) != digesto(conclusion_por_llegada)
        if difiere != esperado["difiere_por_llegada"]:
            fallos.append("orden: se esperaba que la conclusion por orden de llegada %s"
                          % ("difiriera" if esperado["difiere_por_llegada"]
                             else "coincidiera"))

    # La regla declarada por el banco tiene que estar nombrada en la conclusion.
    nombradas = _reglas_nombradas(conclusion)
    for regla in caso.reglas:
        if regla not in nombradas:
            fallos.append("el caso lo produce %s y la conclusion no la nombra" % regla)

    return fallos


def digesto(conclusion, nivel="todo"):
    """Representacion comparable de la conclusion, por niveles.

    Es la unidad de comparacion: la conclusion completa, cada nivel con su
    identificador de regla. Comparar solo la aptitud final haria que ningun
    caso permisivo pudiera caer nunca.
    """
    partes = []
    for evaluacion in conclusion.evaluaciones:
        partes.append(("t_d", reloj.desplazamiento(evaluacion.t_d)))
        for lote in evaluacion.lotes:
            if nivel in ("todo", "lote"):
                partes.append((lote.lote_id, tuple(sorted(lote.campos().items()))))
            if nivel in ("todo", "excursion"):
                for exc in lote.excursiones:
                    partes.append((lote.lote_id, tuple(sorted(exc.campos().items()))))
            if nivel in ("todo", "lectura"):
                for ver in lote.veredictos:
                    partes.append((lote.lote_id, ver.indice,
                                   tuple(sorted(ver.campos().items()))))
    if nivel in ("todo", "lote"):
        for accion in conclusion.acciones:
            partes.append(("accion", tuple(sorted(accion.campos().items()))))
    return tuple(partes)
