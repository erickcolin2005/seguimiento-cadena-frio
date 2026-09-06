"""Carga de los casos. Los casos son DATOS, no funciones de prueba.

Cada caso vive en un fichero JSON con su entrada y su desenlace esperado. Los
tiempos se escriben como desplazamientos en minutos desde T0 y se convierten a
instantes reales en cada corrida.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from . import reloj
from .dominio import Envio, Lectura, Lote

CARPETA = Path(__file__).parent / "casos"


@dataclass(frozen=True, slots=True)
class Caso:
    caso_id: str
    familia: str
    titulo: str
    reglas: tuple                 # reglas que el banco declara que lo producen
    control: bool                 # O-07, X-05, X-06: no se atribuyen a regla
    envio: Envio
    instantes_decision: tuple
    redecisiones: int
    esperado: dict
    fuente: str


def _expandir(crudas):
    """Una tanda de lecturas iguales se escribe una vez.

    `{"desde": 10, "hasta": 21, "cada": 1, "valor": 9.0}` son las lecturas de
    T0+10 a T0+21, una por minuto, todas de 9,0 grados. Sigue siendo un dato:
    no hay logica en el caso, solo una forma corta de escribir una secuencia.

    `llegada_desde` y `llegada_cada` dan el orden de entrega de la tanda, que es
    lo que los casos de orden invierten.
    """
    salida = []
    for cruda in crudas:
        if "desde" not in cruda:
            salida.append(cruda)
            continue
        paso = cruda.get("cada", 1)
        llegada = cruda.get("llegada_desde")
        for minuto in range(cruda["desde"], cruda["hasta"] + 1, paso):
            copia = {k: v for k, v in cruda.items()
                     if k not in ("desde", "hasta", "cada",
                                  "llegada_desde", "llegada_cada")}
            copia["produccion"] = minuto
            if llegada is not None:
                copia["llegada"] = llegada
                llegada += cruda.get("llegada_cada", 1)
            salida.append(copia)
    return salida


def _lecturas(envio_id, crudas):
    """Las lecturas se guardan en el orden en que las declara el caso -el orden
    de llegada- y se indexan por su orden de PRODUCCION. El motor ordena
    siempre por produccion; el orden de llegada no entra nunca en una regla."""
    hechas = []
    for cruda in _expandir(crudas):
        hechas.append(Lectura(
            indice=-1,
            produccion=reloj.instante(cruda["produccion"]),
            valor=cruda.get("valor"),
            envio_id=cruda.get("envio_id", envio_id),
            llegada=reloj.instante(cruda.get("llegada")),
        ))
    por_produccion = sorted(hechas, key=lambda l: l.produccion)
    indices = {id(l): i for i, l in enumerate(por_produccion)}
    return tuple(Lectura(indices[id(l)], l.produccion, l.valor, l.envio_id, l.llegada)
                 for l in hechas)


def _envio(crudo):
    lotes = tuple(Lote(lt["lote_id"], lt["tipo"],
                       reloj.instante(lt.get("carga", 0)),
                       reloj.instante(lt.get("entrega")))
                  for lt in crudo["lotes"])
    return Envio(crudo["envio_id"], lotes, _lecturas(crudo["envio_id"], crudo["lecturas"]))


def _decisiones(crudo):
    valor = crudo.get("decision")
    if valor is None:
        return (None,)
    if isinstance(valor, list):
        return tuple(reloj.instante(v) for v in valor)
    return (reloj.instante(valor),)


def cargar(carpeta=CARPETA):
    casos = []
    for fichero in sorted(carpeta.glob("*.json")):
        datos = json.loads(fichero.read_text(encoding="utf-8"))
        for crudo in datos["casos"]:
            casos.append(Caso(
                caso_id=crudo["caso_id"],
                familia=crudo["caso_id"].split("-")[0],
                titulo=crudo["titulo"],
                reglas=tuple(crudo.get("reglas", ())),
                control=crudo.get("control", False),
                envio=_envio(crudo["envio"]),
                instantes_decision=_decisiones(crudo),
                redecisiones=crudo.get("redecisiones", 0),
                esperado=crudo["esperado"],
                fuente=fichero.name,
            ))
    return casos


def envio_por_orden_de_llegada(envio):
    """El mismo envio como lo veria un sistema que evalua por orden de llegada.

    Se reasignan los instantes de produccion siguiendo el orden en que las
    lecturas llegaron. Sirve para comprobar que los casos de orden no son
    decorativos: la conclusion correcta tiene que DIFERIR de esta.
    """
    llegada = sorted(envio.lecturas,
                     key=lambda l: (l.llegada or l.produccion, l.indice))
    instantes = sorted(l.produccion for l in envio.lecturas)
    reasignadas = tuple(Lectura(i, instantes[i], lec.valor, lec.envio_id, lec.llegada)
                        for i, lec in enumerate(llegada))
    return Envio(envio.envio_id, envio.lotes, reasignadas)
