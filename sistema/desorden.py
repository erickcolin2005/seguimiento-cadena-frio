"""El desorden, y sobre todo: **cuando el desorden importa**.

Barajar cuatrocientas lecturas puede no cambiar ni una conclusion. Por eso el
denominador de C1-A son **inversiones decisivas** y no «lecturas desordenadas»:
publicar el segundo numero seria publicar algo que no se midio.

## Que modela «procesada tal como llega»

Un sistema que **no** reconstruye el orden trata la posicion de llegada como si
fuera el instante en que ocurrio. Ese es el modelo ingenuo, y es contra el que se
mide: se conservan los valores y se reasignan los instantes de produccion segun
el orden en que llegaron. Es literalmente *«subio, seguido de bajo, leido al
reves»*.

El sistema real hace lo contrario: re-deriva el orden por numero de secuencia y
**no depende del orden de entrega ni cuando el transporte lo garantiza** (DR-6).
Por eso su conclusion tiene que coincidir con la referencia aunque las lecturas
lleguen barajadas.

## Que cuenta como decisiva, una por una

**Una inversion es decisiva si, procesada tal como llega, produciria una
conclusion distinta de la de la referencia.** Se comprueba **por pares y de una
en una**: se parte del orden real, se intercambian esas dos lecturas y solo esas,
y se evalua el envio con el modelo ingenuo. Si la conclusion cambia, esa
inversion es decisiva; si no, no lo es, por mucho que este desordenada.

Es deliberadamente estricto. Contar como decisivas todas las inversiones de una
baraja que cambia algo inflaria el numerador con inversiones que no cambian nada
por si solas.

## Las cinco clases

| | Que cambia | Regla |
|---|---|---|
| IV-1 | El veredicto de aptitud del lote | RC-08 |
| IV-2 | La duracion acumulada | RC-06, RC-07 |
| IV-3 | La clase de accion | RC-09 |
| IV-4 | La posicion respecto al cierre del envio: cambia a que lote se imputa | RC-02 |
| IV-5 | El cruce de umbral para UN lote y no para otro del mismo envio | RC-04 |

Una misma inversion puede caer en varias clases. Se cuenta **una vez** en el
total y **una vez en cada clase que le corresponde**, asi que la suma por clases
puede ser mayor que el total. Se publican los dos numeros por separado, porque
sumarlos seria inventarse un tercero.
"""

import random

from banco import dominio, reloj

from . import referencia

CLASES = ("IV-1", "IV-2", "IV-3", "IV-4", "IV-5")

REGLA_DE_CLASE = {"IV-1": "RC-08", "IV-2": "RC-06/RC-07", "IV-3": "RC-09",
                  "IV-4": "RC-02", "IV-5": "RC-04"}


def envio_en_orden(crudo, llegada=None):
    """El envio del guion, montado segun un orden de llegada.

    `llegada` es una permutacion de indices sobre las lecturas ordenadas por
    produccion. Con `None` se monta el orden real, que es la referencia.

    Cuando se da una permutacion se **reasignan los instantes de produccion** a
    la posicion de llegada: eso es lo que hace un sistema que no reconstruye el
    orden, y es lo unico que puede cambiar una conclusion.
    """
    lecturas_guion = sorted(crudo["lecturas"], key=lambda l: l["produccion_min"])
    if llegada is None:
        lecturas = tuple(
            dominio.Lectura(indice=l["secuencia"],
                            produccion=reloj.instante(l["produccion_min"]),
                            valor=l["valor_c"], envio_id=crudo["envio_id"])
            for l in lecturas_guion)
    else:
        lecturas = tuple(
            dominio.Lectura(indice=posicion,
                            produccion=reloj.instante(posicion),
                            valor=lecturas_guion[origen]["valor_c"],
                            envio_id=crudo["envio_id"])
            for posicion, origen in enumerate(llegada))
    lotes = tuple(
        dominio.Lote(lote_id=l["lote_id"], tipo_producto=l["tipo_id"],
                     carga=reloj.instante(l["carga_min"]),
                     entrega=reloj.instante(l["entrega_min"]))
        for l in crudo["lotes"])
    return dominio.Envio(crudo["envio_id"], lotes, lecturas)


def cruza_el_cierre(par, crudo):
    """Cierto si intercambiar ese par mueve una lectura a traves de la ventana
    de a bordo de algun lote — emitida antes de la entrega, llegada despues.

    **Por que IV-4 no se puede detectar contando.** Bajo una permutacion, el
    multiconjunto de instantes de produccion es el mismo, asi que CUANTAS
    lecturas caen dentro de la ventana de un lote no cambia nunca: solo cambia
    CUALES. Contar imputadas daria cero siempre y la clase parecería inalcanzable
    cuando lo que fallaba era el detector. Se mira el par, no el recuento.
    """
    i, j = par
    for lote in crudo["lotes"]:
        dentro_i = lote["carga_min"] <= i < lote["entrega_min"]
        dentro_j = lote["carga_min"] <= j < lote["entrega_min"]
        if dentro_i != dentro_j:
            return True
    return False


def clasificar(base, alterada, par=None, crudo=None):
    """En que clases IV cae la diferencia entre dos juegos de conclusiones."""
    clases = set()
    lotes = set(base) | set(alterada)
    fuera_cambia, fuera_igual = 0, 0
    for lote_id in lotes:
        a, b = base.get(lote_id), alterada.get(lote_id)
        if a is None or b is None:
            clases.add("IV-4")
            continue
        if a["aptitud"] != b["aptitud"] or a["umbral_superado"] != b["umbral_superado"]:
            clases.add("IV-1")
        if a["acumulado_min"] != b["acumulado_min"]:
            clases.add("IV-2")
        if a["clase_accion"] != b["clase_accion"]:
            clases.add("IV-3")
        if a["fuera_de_rango"] != b["fuera_de_rango"]:
            fuera_cambia += 1
        else:
            fuera_igual += 1
    # IV-4: la diferencia la produce una lectura que cruza el cierre del envio.
    if par is not None and crudo is not None and cruza_el_cierre(par, crudo):
        clases.add("IV-4")
    # IV-5 es «para UN lote y no para otro»: hace falta que el envio tenga mas de
    # un lote y que el cruce de umbral cambie para unos y no para todos.
    if len(lotes) > 1 and fuera_cambia and fuera_igual:
        clases.add("IV-5")
    return clases


def _difieren(a, b):
    return a != b


def inversiones_presentes(llegada):
    """Los pares (i, j) que llegan en orden invertido respecto al real.

    `llegada[k]` es el indice real de la lectura que llego en la posicion k.
    """
    pares = []
    for k in range(len(llegada)):
        for m in range(k + 1, len(llegada)):
            if llegada[k] > llegada[m]:
                pares.append((llegada[m], llegada[k]))
    return pares


def analizar_envio(crudo, llegada):
    """Inversiones observadas y decisivas de un envio, con su clase.

    Devuelve un diccionario con los dos numeros por separado y el detalle.
    """
    base, _ = referencia.conclusiones_del_envio(
        envio_en_orden(crudo), crudo["envio_id"])
    n = len(crudo["lecturas"])
    observadas = inversiones_presentes(llegada)

    decisivas = []
    por_clase = {c: 0 for c in CLASES}
    for i, j in observadas:
        # Solo esas dos, y nada mas. Se parte del orden real.
        permutacion = list(range(n))
        permutacion[i], permutacion[j] = permutacion[j], permutacion[i]
        alterada, _ = referencia.conclusiones_del_envio(
            envio_en_orden(crudo, permutacion), crudo["envio_id"])
        if not _difieren(base, alterada):
            continue
        clases = clasificar(base, alterada, (i, j), crudo)
        if not clases:
            # Cambia algo que ninguna de las cinco clases nombra. No se cuenta
            # como decisiva de ninguna clase, y se dice: inventarle una clase
            # seria peor que declararlo.
            clases = {"sin_clase"}
        decisivas.append({"par": (i, j), "clases": sorted(clases)})
        for c in clases:
            if c in por_clase:
                por_clase[c] += 1

    return {"envio_id": crudo["envio_id"],
            "lecturas": n,
            "observadas": len(observadas),
            "decisivas": len(decisivas),
            "por_clase": por_clase,
            "sin_clase": sum(1 for d in decisivas if d["clases"] == ["sin_clase"]),
            "detalle": decisivas}


def barajar(crudo, az):
    """Un orden de llegada para este envio. Determinista: lo fija la semilla."""
    llegada = list(range(len(crudo["lecturas"])))
    az.shuffle(llegada)
    return llegada


def ordenes_de_llegada(guion, semilla):
    """Un orden de llegada por envio, todos derivados de la semilla."""
    az = random.Random(semilla + 1)
    return {crudo["envio_id"]: barajar(crudo, az) for crudo in guion["envios"]}
