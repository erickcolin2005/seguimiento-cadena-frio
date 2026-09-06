"""Las cosas del dominio: tipos de producto, envio, lote y lectura.

La decision estructural de este modulo, y es la que sostiene el criterio 4 de
PL-1: **el tipo de producto es un campo del LOTE y el envio no tiene ninguno**.
Las clases son congeladas y con `slots`, asi que un envio no puede recibir un
tipo de producto ni siquiera por accidente: no hay ranura donde ponerlo, y
escribir en el objeto levanta una excepcion. No es que evaluar por envio este
desaconsejado; es que no hay camino para escribirlo.
"""

from dataclasses import dataclass

# --- Parametros por tipo de producto -----------------------------------------
# Origen de cada numero, declarado junto al numero (RF-23):
#   - Rango de P-REF (2 a 6 grados): DN-02, TOMADO PRESTADO del Art. 18 num.
#     3.1 de la Resolucion 2674 de 2013, que regula MANIPULACION. La norma NO
#     fija temperatura numerica de refrigeracion para el TRANSPORTE.
#   - Rango de P-CON (<= -18 grados): DN-09, el numero esta en la norma; el
#     articulo exacto no esta verificado.
#   - Rango de P-FRE (12 a 18 grados): asumido entero, sin anclaje normativo.
#   - Duracion minima (DN-05) y tolerada (DN-06): decisiones de negocio sin
#     anclaje normativo, adoptadas como valores de trabajo NO validados.
#     Ver decisiones/decisiones-de-negocio.md.


@dataclass(frozen=True, slots=True)
class Parametros:
    codigo: str
    nombre: str
    minimo: float | None          # None = sin limite inferior (P-CON)
    maximo: float | None          # None = sin limite superior
    duracion_minima: int          # minutos para que una desviacion abra excursion
    duracion_tolerada: int        # minutos acumulados antes de perder el lote
    granularidad: int             # segundos entre lecturas esperadas


TIPOS = {
    "P-REF": Parametros("P-REF", "Refrigerado", 2.0, 6.0, 5, 30, 60),
    "P-CON": Parametros("P-CON", "Congelado", None, -18.0, 2, 10, 30),
    "P-FRE": Parametros("P-FRE", "Fresco controlado", 12.0, 18.0, 10, 60, 120),
}

# Rango operativo de la sonda. Fuera de el la lectura es invalida (RC-03).
SONDA_MINIMA = -40.0
SONDA_MAXIMA = 60.0


@dataclass(frozen=True, slots=True)
class Lote:
    """La unidad sobre la que recaen todas las conclusiones.

    `tipo_producto` vive aqui y solo aqui. La ventana de a bordo es
    [carga, entrega); `entrega = None` significa que sigue a bordo.
    """

    lote_id: str
    tipo_producto: str
    carga: object                 # instante real, derivado de T0
    entrega: object | None

    @property
    def parametros(self):
        """Unico camino hacia los umbrales: se pasa por un lote."""
        return TIPOS[self.tipo_producto]

    def a_bordo_en(self, momento):
        if momento < self.carga:
            return False
        if self.entrega is not None and momento >= self.entrega:
            return False
        return True


@dataclass(frozen=True, slots=True)
class Lectura:
    """Una medicion de la sonda del envio, con su instante de produccion.

    `envio_id` es a quien la atribuye quien la envia, que puede no existir
    (RC-01). `valor = None` es una lectura sin valor de temperatura.
    """

    indice: int                   # orden de produccion, 0..n
    produccion: object
    valor: float | None
    envio_id: str
    llegada: object | None = None  # solo para los casos de orden (O)


@dataclass(frozen=True, slots=True)
class Envio:
    """Un vehiculo en ruta, con UNA sonda y UNA secuencia de lecturas.

    No tiene tipo de producto, ni umbrales, ni aptitud, ni conclusion. Los
    lotes a bordo pueden ser de tipos distintos y entonces la misma lectura es
    excursion para uno y no para el otro.
    """

    envio_id: str
    lotes: tuple
    lecturas: tuple

    def lote(self, lote_id):
        for lt in self.lotes:
            if lt.lote_id == lote_id:
                return lt
        raise KeyError(lote_id)

    def hay_lote_a_bordo(self, momento):
        return any(lt.a_bordo_en(momento) for lt in self.lotes)


def fuera_del_rango_operativo(valor):
    return valor < SONDA_MINIMA or valor > SONDA_MAXIMA
