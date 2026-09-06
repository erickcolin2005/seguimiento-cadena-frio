"""T0 y los instantes del banco.

T0 es el instante en que arranca la corrida, truncado al minuto. Todos los
tiempos de los casos se escriben como desplazamientos en minutos (T0+n) y se
convierten a instantes reales en cada corrida. Un banco con fechas escritas a
mano se pudre en silencio; este no tiene ninguna.
"""

from datetime import datetime, timedelta

# Se fija una sola vez al importar el modulo: una corrida, un T0.
T0 = datetime.now().replace(second=0, microsecond=0)


def instante(minutos):
    """Convierte el desplazamiento T0+n de un caso en un instante real."""
    if minutos is None:
        return None
    return T0 + timedelta(minutes=minutos)


def desplazamiento(momento):
    """Devuelve el instante como minutos desde T0. Es lo que se compara y se
    publica: dos corridas con T0 distintos tienen que dar el mismo numero."""
    if momento is None:
        return None
    return int((momento - T0).total_seconds() // 60)


def etiqueta(momento):
    """Instante en la notacion del banco: 'T0+30'."""
    if momento is None:
        return "-"
    return "T0+%d" % desplazamiento(momento)


def minutos_entre(inicio, fin):
    """Duracion en minutos. El intervalo es semiabierto: [inicio, fin)."""
    return int((fin - inicio).total_seconds() // 60)
