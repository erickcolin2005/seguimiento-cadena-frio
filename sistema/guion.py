"""EM · el guion: la telemetria sintetica, fijada por una semilla.

El guion es **datos**, no un flujo. Se genera entero antes de que exista una
sola lectura en el sistema, se le calcula un digesto, y ese par
`(semilla, digesto)` se fija UNA vez y se le pasa como parametro a cada
consumidor: el emisor, SV-1, SV-2 y la calculadora de referencia. Cada
consumidor regenera el guion desde la semilla y **se niega a trabajar si su
digesto no coincide** con el que recibio (SEC-3 §4.1 elemento 4).

Dos propiedades que este modulo tiene que cumplir, y por que:

  * **Todo son minutos enteros desde T0, nunca instantes de pared.** El guion
    cruza procesos y cada proceso fija su propio T0 al importar `banco.reloj`.
    Si el guion llevara instantes absolutos, dos procesos compararian cosas
    distintas. Con desplazamientos, el T0 se cancela.
  * **Los identificadores los genera la semilla** (SEC-7): llevan una etiqueta
    derivada de ella y ninguna superficie del sistema permite teclearlos.

Lo que este generador NO es: un generador aleatorio de telemetria. Es un juego
fijo de cuatro perfiles de envio cuyo reparto, longitudes y valores mueve la
semilla. Se hace asi para que **toda semilla produzca al menos un hecho
actuable** -- si no, el camino entero de la comprobacion 2 no tendria nada que
recorrer y saldria verde sin haber ejercido nada.
"""

import hashlib
import json
import random

VERSION_GUION = "PL-2"

# Valores dentro y fuera de rango por tipo, todos dentro del rango operativo de
# la sonda (-40 a +60): fuera de el la lectura seria invalida por RC-03 y eso es
# otro caso, no una excursion.
VALORES = {
    "P-REF": {"dentro": (3.0, 3.5, 4.0, 4.5, 5.0), "fuera": (8.0, 8.5, 9.0, -1.0, 0.5)},
    "P-CON": {"dentro": (-25.0, -22.0, -20.0), "fuera": (-17.0, -15.0, -10.0)},
    "P-FRE": {"dentro": (13.0, 14.0, 15.0, 16.0), "fuera": (20.0, 21.0, 10.0)},
}


def _etiqueta(semilla):
    return hashlib.sha256(("semilla:%d" % semilla).encode("utf-8")).hexdigest()[:4].upper()


def _lecturas(n, valor_de):
    return [{"secuencia": s, "produccion_min": s, "valor_c": valor_de(s)}
            for s in range(n)]


def _perfil_normal(az, tipo="P-REF"):
    """Todo dentro de rango, con UNA lectura sin valor.

    La lectura sin valor es invalida por RC-03: ni abre ni cierra excursion y no
    rompe la consecutividad. Deja un hueco no determinante, que es lo que RC-11
    tiene que saber marcar sin declarar nada perdido.
    """
    n = 24 + az.randrange(0, 4)
    dentro = az.choice(VALORES[tipo]["dentro"])
    sin_valor = 10 + az.randrange(0, 3)

    def valor(s):
        return None if s == sin_valor else dentro

    return {"tipo": tipo, "n": n, "lecturas": _lecturas(n, valor),
            "lotes": [("todo", 0, n + 3)],
            "espera": "NINGUNA"}


def _perfil_rescate(az, tipo="P-REF"):
    """Una excursion abierta al final, mas larga que la duracion minima del
    tipo y con acumulado por debajo de lo tolerado: RC-09 da RESCATE."""
    n = 24 + az.randrange(0, 4)
    dentro = az.choice(VALORES[tipo]["dentro"])
    fuera = az.choice(VALORES[tipo]["fuera"])
    largo = 6 + az.randrange(0, 3)          # duracion = largo - 1, >= 5
    inicio = n - largo

    def valor(s):
        return fuera if s >= inicio else dentro

    return {"tipo": tipo, "n": n, "lecturas": _lecturas(n, valor),
            "lotes": [("todo", 0, n + 3)],
            "espera": "RESCATE"}


def _perfil_disposicion(az, tipo="P-CON"):
    """Una excursion cerrada mas larga que lo tolerado por el tipo: el lote
    queda no apto y RC-09 da DISPOSICION, que gana sobre RESCATE (CF-2)."""
    n = 24 + az.randrange(0, 4)
    dentro = az.choice(VALORES[tipo]["dentro"])
    fuera = az.choice(VALORES[tipo]["fuera"])
    inicio = 4 + az.randrange(0, 2)
    fin = inicio + 11 + az.randrange(0, 2)   # duracion = fin + 1 - inicio > 10

    def valor(s):
        return fuera if inicio <= s <= fin else dentro

    return {"tipo": tipo, "n": n, "lecturas": _lecturas(n, valor),
            "lotes": [("todo", 0, n + 3)],
            "espera": "DISPOSICION"}


def _perfil_dos_lotes(az, tipo="P-FRE"):
    """Dos lotes en el mismo envio, con ventanas de a bordo distintas.

    La misma lectura es excursion para uno y no cuenta para el otro. Es lo que
    hace visible que la conclusion es del LOTE y nunca del envio.
    """
    n = 24 + az.randrange(0, 4)
    dentro = az.choice(VALORES[tipo]["dentro"])
    fuera = az.choice(VALORES[tipo]["fuera"])
    largo = 12 + az.randrange(0, 2)          # duracion = largo - 1, >= 10
    inicio = n - largo
    entrega_corta = 8 + az.randrange(0, 3)   # entregado antes de la excursion

    def valor(s):
        return fuera if s >= inicio else dentro

    return {"tipo": tipo, "n": n, "lecturas": _lecturas(n, valor),
            "lotes": [("todo", 0, n + 3), ("corto", 0, entrega_corta)],
            "espera": "RESCATE + NINGUNA"}


PERFILES = (_perfil_normal, _perfil_rescate, _perfil_disposicion, _perfil_dos_lotes)


def generar(semilla):
    """El guion completo para esta semilla. Determinista, sin reloj de pared."""
    az = random.Random(semilla)
    etiqueta = _etiqueta(semilla)
    perfiles = list(PERFILES)
    az.shuffle(perfiles)

    envios = []
    n_lote = 0
    for indice, construir in enumerate(perfiles, start=1):
        crudo = construir(az)
        envio_id = "EN-%s-%02d" % (etiqueta, indice)
        lotes = []
        for clase, carga, entrega in crudo["lotes"]:
            n_lote += 1
            lotes.append({
                "lote_id": "LT-%s-%02d" % (etiqueta, n_lote),
                "tipo_id": crudo["tipo"],
                "carga_min": carga,
                "entrega_min": entrega,
                "carga_secuencia": carga,
                "entrega_secuencia": entrega,
                "ventana": clase,
            })
        envios.append({
            "envio_id": envio_id,
            "estado": "EN_RUTA",
            "perfil_esperado": crudo["espera"],
            "lecturas": crudo["lecturas"],
            "lotes": lotes,
        })

    return {"version_guion": VERSION_GUION, "semilla": semilla,
            "etiqueta": etiqueta, "envios": envios}


def canonico(guion):
    """La forma sobre la que se calcula el digesto: una sola representacion."""
    return json.dumps(guion, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def digesto(guion):
    return hashlib.sha256(canonico(guion).encode("utf-8")).hexdigest()


def lotes(guion):
    for envio in guion["envios"]:
        for lote in envio["lotes"]:
            yield envio, lote


def resumen(guion):
    n_lecturas = sum(len(e["lecturas"]) for e in guion["envios"])
    n_lotes = sum(len(e["lotes"]) for e in guion["envios"])
    return {"envios": len(guion["envios"]), "lotes": n_lotes,
            "lecturas": n_lecturas}


def exigir_digesto(guion, esperado):
    """Un consumidor que no reconoce el guion no trabaja: se niega.

    Es el cierre de T-04. Si los tres consumidores no reportan el mismo par
    (semilla, digesto), no se comparo nada sobre lo mismo.
    """
    obtenido = digesto(guion)
    if esperado and obtenido != esperado:
        raise ValueError(
            "digesto del guion distinto del recibido: %s != %s" % (obtenido, esperado))
    return obtenido
