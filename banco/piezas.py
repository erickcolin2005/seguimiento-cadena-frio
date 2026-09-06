"""Las trece piezas apagables del banco.

Son trece y no doce porque RC-08 se parte en dos: el umbral y la
irreversibilidad. Apagarlas juntas deja viva la irreversibilidad sin que nadie
lo note, porque los casos del umbral caen igual y el rojo aparece.

Que hace cada pieza cuando esta APAGADA queda escrito aqui, junto a la pieza,
porque es lo que la mutacion mide. Apagar una pieza no es borrarla del informe:
es dejar de aplicar su restriccion, y con ella desaparece su identificador de
regla de la conclusion.
"""

PIEZAS = (
    "RC-01",                   # atribucion de la lectura a un envio con lote a bordo
    "RC-02",                   # ventana de a bordo del lote
    "RC-03",                   # validez de la lectura
    "RC-04",                   # umbral por tipo de producto
    "RC-05",                   # apertura de excursion (duracion minima)
    "RC-06",                   # cierre de excursion con la primera lectura dentro
    "RC-07",                   # acumulacion de excursiones del lote
    "RC-08-umbral",            # superar lo tolerado deja el lote no apto
    "RC-08-irreversibilidad",  # no apto no se rehabilita nunca
    "RC-09",                   # clase de accion en el instante de decision
    "RC-10",                   # una accion por hecho actuable
    "RC-11",                   # hueco determinante e conclusion provisional
    "RC-12",                   # la conclusion se cierra en la entrega del lote
)

# Como se nombra cada pieza en la conclusion. RC-08 se publica con el nombre de
# la regla del banco; el sufijo distingue la mitad para la mutacion.
REGLA_DE_PIEZA = {
    "RC-08-umbral": "RC-08",
    "RC-08-irreversibilidad": "RC-08",
}


def regla_de(pieza):
    return REGLA_DE_PIEZA.get(pieza, pieza)


class Interruptores:
    """Las trece piezas, encendidas salvo las que se pidan apagadas."""

    def __init__(self, apagadas=()):
        desconocidas = [p for p in apagadas if p not in PIEZAS]
        if desconocidas:
            raise ValueError("piezas inexistentes: %s" % ", ".join(desconocidas))
        self.apagadas = frozenset(apagadas)

    def encendida(self, pieza):
        if pieza not in PIEZAS:
            raise ValueError("pieza inexistente: %s" % pieza)
        return pieza not in self.apagadas

    def __repr__(self):
        if not self.apagadas:
            return "<todas encendidas>"
        return "<apagadas: %s>" % ", ".join(sorted(self.apagadas))


TODAS_ENCENDIDAS = Interruptores()
