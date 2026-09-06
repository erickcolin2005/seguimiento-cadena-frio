"""La costura del transporte: el sitio por donde se cambia sin tocar nada más.

El diseño afirma que **el transporte no sostiene ninguna garantía**, y que por eso
sustituirlo es sustituir un adaptador y no rediseñar el sistema. Mientras la
llamada estuviera incrustada dentro del drenaje, esa afirmación era una promesa:
no había ningún sitio donde enchufar otro transporte, así que no había forma de
comprobarla.

Este módulo es ese sitio. Un adaptador recibe un hecho actuable ya comprometido y
devuelve el desenlace que el receptor le dio. **Nada más.**

## Lo que un adaptador NO puede hacer, y es la mitad del asunto

  * **No deduplica.** La unidad de «exactamente una vez» es la terna, que es de
    dominio y no de transporte. Si un adaptador dedujera, la garantía viviría en
    él y cambiar de transporte la cambiaría.
  * **No decide si reintentar.** Eso lo decide quien tiene la bandeja, leyendo el
    desenlace.
  * **No ordena nada.** El orden se re-deriva del número de secuencia, y el
    sistema no depende del orden de entrega **ni siquiera cuando el transporte lo
    garantiza**.

Un adaptador que hiciera cualquiera de las tres cosas haría más barato el código
y **más falso el resultado**: la medición estaría comprobando el transporte, no
el sistema.

## Cómo se comprueba que la costura es real

No basta con haberla escrito. La comprobación es que **la medición completa de C1
dé lo mismo con dos adaptadores distintos**: si diera distinto, algo de la
garantía se habría filtrado al transporte.

Hoy hay un solo adaptador de verdad —la llamada directa— y **eso se declara**:
la costura existe y está aislada, pero **la comprobación de que sobrevive al
cambio no está hecha**, porque el segundo transporte no existe todavía. Escribir
aquí que «el transporte es intercambiable» sin haber cambiado ninguno sería
exactamente la clase de afirmación que este proyecto no publica.
"""

from . import protocolo

# Los tres desenlaces que el receptor puede dar. El adaptador los transporta tal
# cual: traducirlos seria decidir por el receptor.
REGISTRADA = "registrada"
YA_REGISTRADA = "ya_registrada"
RECHAZADA = "rechazada_lote_no_sembrado"


class Adaptador:
    """El puerto. Un transporte concreto implementa `entregar` y nada más."""

    nombre = "abstracto"

    def entregar(self, accion):
        """Devuelve (codigo, respuesta). Una excepción significa «no llegó»,
        que **no es lo mismo** que «llegó y fue rechazada»."""
        raise NotImplementedError

    def describir(self):
        return {"transporte": self.nombre}


class LlamadaDirecta(Adaptador):
    """Llamada síncrona al receptor, iniciada por el drenaje de la bandeja.

    Es el transporte con el que se midió C1. No ofrece orden, ni entrega única,
    ni durabilidad — y no se le piden: todo eso vive a los lados.
    """

    nombre = "llamada directa"

    def __init__(self, url_receptor):
        self.url_receptor = url_receptor

    def entregar(self, accion):
        return protocolo.pedir(self.url_receptor, "/acciones", accion)

    def describir(self):
        return {"transporte": self.nombre, "receptor": self.url_receptor}


ADAPTADORES = {"directo": LlamadaDirecta}


def construir(clase, url_receptor):
    if clase not in ADAPTADORES:
        raise ValueError("transporte desconocido: %s · hay %s"
                         % (clase, ", ".join(sorted(ADAPTADORES))))
    return ADAPTADORES[clase](url_receptor)
