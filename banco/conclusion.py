"""La forma de una conclusion: tres niveles, y cada nivel nombra su regla.

Los tres niveles son lectura, excursion y lote. **Todos los desenlaces llevan
identificador de regla, tambien los permisivos**: "dentro de rango" no es la
ausencia de veredicto, es un veredicto producido por RC-04. Si solo los
desenlaces restrictivos nombraran su regla, apagar RC-04 no cambiaria nada para
un caso que ya estaba dentro de rango y trece casos del banco no podrian caer
nunca.

No existe ninguna clase de conclusion a nivel de envio. La aptitud, el
acumulado, la clase de accion y la marca de secuencia son campos del LOTE.
"""

from dataclasses import dataclass

from . import reloj


@dataclass(frozen=True, slots=True)
class VeredictoLectura:
    """Nivel lectura: una entrada por cada lectura y cada lote del envio."""

    lote_id: str
    indice: int
    produccion: object
    atribucion: str | None          # evaluada | no_evaluada          (RC-01)
    regla_atribucion: str | None
    imputacion: str | None          # imputada | no_imputada          (RC-02)
    regla_imputacion: str | None
    validez: str | None             # valida | invalida               (RC-03)
    regla_validez: str | None
    situacion: str | None           # dentro_de_rango | fuera_de_rango (RC-04)
    regla_situacion: str | None
    conservada: bool = True         # no evaluarla no es descartarla

    def campos(self):
        return {
            "produccion": reloj.etiqueta(self.produccion),
            "atribucion": self.atribucion,
            "regla_atribucion": self.regla_atribucion,
            "imputacion": self.imputacion,
            "regla_imputacion": self.regla_imputacion,
            "validez": self.validez,
            "regla_validez": self.regla_validez,
            "situacion": self.situacion,
            "regla_situacion": self.regla_situacion,
            "conservada": self.conservada,
        }


@dataclass(frozen=True, slots=True)
class Excursion:
    """Nivel excursion. `transitoria` marca la desviacion que no llego al
    minimo del tipo: se registra, no invalida (RC-05)."""

    apertura: object
    cierre: object | None
    duracion: int
    abierta: bool
    transitoria: bool
    regla_apertura: str | None
    regla_cierre: str | None

    def campos(self):
        return {
            "apertura": reloj.etiqueta(self.apertura),
            "cierre": reloj.etiqueta(self.cierre),
            "duracion": self.duracion,
            "abierta": self.abierta,
            "transitoria": self.transitoria,
            "regla_apertura": self.regla_apertura,
            "regla_cierre": self.regla_cierre,
        }


@dataclass(frozen=True, slots=True)
class ConclusionLote:
    """Nivel lote. Es donde vive la aptitud, y no hay otro sitio donde viva."""

    lote_id: str
    tipo_producto: str
    t_d: object | None
    aptitud: str | None             # apto | no_apto | no_declarable_apto
    regla_aptitud: str | None
    acumulado: int | None           # minutos
    regla_acumulado: str | None
    clase_accion: str | None        # NINGUNA | RESCATE | DISPOSICION
    regla_clase_accion: str | None
    marca_secuencia: str | None     # completa | hueco_no_determinante | hueco_determinante
    regla_marca_secuencia: str | None
    provisional: bool
    marca_excursiones: str | None   # sin_excursion | con_excursion
    regla_marca_excursiones: str | None
    cerrada_en: object | None       # solo si el lote se entrego (RC-12)
    regla_cierre_conclusion: str | None
    conocido_hasta: object          # horizonte del prefijo: lo fija el instante
                                    # de decision, no una regla. Por eso no lleva
                                    # identificador y no esta en REGLA_DE_CAMPO.
    excursiones: tuple
    veredictos: tuple

    def campos(self):
        return {
            "aptitud": self.aptitud,
            "regla_aptitud": self.regla_aptitud,
            "acumulado": self.acumulado,
            "regla_acumulado": self.regla_acumulado,
            "clase_accion": self.clase_accion,
            "regla_clase_accion": self.regla_clase_accion,
            "marca_secuencia": self.marca_secuencia,
            "regla_marca_secuencia": self.regla_marca_secuencia,
            "provisional": self.provisional,
            "marca_excursiones": self.marca_excursiones,
            "regla_marca_excursiones": self.regla_marca_excursiones,
            "cerrada_en": reloj.etiqueta(self.cerrada_en),
            "regla_cierre_conclusion": self.regla_cierre_conclusion,
            "conocido_hasta": reloj.etiqueta(self.conocido_hasta),
        }


@dataclass(frozen=True, slots=True)
class Accion:
    """Una accion sobre un hecho actuable: la terna (lote, excursion, clase)."""

    lote_id: str
    apertura_excursion: object | None
    clase: str
    regla_id: str | None

    def campos(self):
        return {
            "lote_id": self.lote_id,
            "apertura_excursion": reloj.etiqueta(self.apertura_excursion),
            "clase": self.clase,
            "regla_id": self.regla_id,
        }


@dataclass(frozen=True, slots=True)
class Evaluacion:
    """Una evaluacion del caso en un instante de decision."""

    t_d: object | None
    lotes: tuple


@dataclass(frozen=True, slots=True)
class ConclusionCaso:
    caso_id: str
    evaluaciones: tuple
    acciones: tuple

    def lote(self, lote_id, evaluacion=0):
        for cl in self.evaluaciones[evaluacion].lotes:
            if cl.lote_id == lote_id:
                return cl
        raise KeyError(lote_id)

    def acciones_de(self, lote_id):
        return [a for a in self.acciones if a.lote_id == lote_id]
