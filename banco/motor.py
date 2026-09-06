"""El motor: aplica las doce reglas a un caso y devuelve su conclusion.

Todo se evalua **por lote**. La firma de la evaluacion recibe un lote, y los
umbrales solo se alcanzan a traves de `lote.parametros`. No hay ninguna funcion
que reciba un envio y devuelva una aptitud: evaluar por envio no esta
desaconsejado, es inescribible.

Orden de evaluacion: el numero de la regla. Los conflictos de desenlace estan
resueltos uno a uno y llevan su marca (CF-1 ... CF-7).
"""

from . import dominio, reloj
from .conclusion import (Accion, ConclusionCaso, ConclusionLote, Evaluacion,
                         Excursion, VeredictoLectura)


class RegistroAcciones:
    """La accion se identifica por el hecho, no por el intento (RC-10).

    El hecho actuable es la terna (lote, excursion, clase de accion). Dos
    decisiones sobre el mismo hecho producen la misma accion, no dos.
    """

    def __init__(self, interruptores):
        self.interruptores = interruptores
        self.acciones = []
        self.hechos = []          # ternas ya decididas, en orden

    def registrar(self, lote_id, apertura, clase):
        terna = (lote_id, reloj.desplazamiento(apertura), clase)
        if terna not in self.hechos:
            self.hechos.append(terna)
        if self.interruptores.encendida("RC-10"):
            ya = any(a.lote_id == lote_id
                     and a.apertura_excursion == apertura
                     and a.clase == clase
                     for a in self.acciones)
            if ya:
                return
            regla = "RC-10"
        else:
            regla = None
        self.acciones.append(Accion(lote_id, apertura, clase, regla))


def _fuera_de_rango(valor, parametros):
    """RC-04. Los limites son inclusive."""
    if parametros.minimo is not None and valor < parametros.minimo:
        return True
    if parametros.maximo is not None and valor > parametros.maximo:
        return True
    return False


def _veredictos_de_lectura(envio, lote, lecturas, sw):
    """Nivel lectura: RC-01, RC-02, RC-03 y RC-04, cada uno con su regla."""
    veredictos = []
    utiles = []          # (clase, lectura, situacion) en orden de produccion
    for lec in lecturas:
        # --- RC-01 · envio y lote identificados y vigentes -------------------
        if sw.encendida("RC-01"):
            atribuible = (lec.envio_id == envio.envio_id
                          and envio.hay_lote_a_bordo(lec.produccion))
            if not atribuible:
                veredictos.append(VeredictoLectura(
                    lote.lote_id, lec.indice, lec.produccion,
                    "no_evaluada", "RC-01", None, None, None, None, None, None))
                continue
            atribucion, regla_atribucion = "evaluada", "RC-01"
        else:
            atribucion, regla_atribucion = None, None

        # --- RC-02 · ventana de a bordo del lote -----------------------------
        if sw.encendida("RC-02"):
            if not lote.a_bordo_en(lec.produccion):
                veredictos.append(VeredictoLectura(
                    lote.lote_id, lec.indice, lec.produccion,
                    atribucion, regla_atribucion,
                    "no_imputada", "RC-02", None, None, None, None))
                continue
            imputacion, regla_imputacion = "imputada", "RC-02"
        else:
            imputacion, regla_imputacion = None, None

        # --- RC-03 · lectura valida ------------------------------------------
        invalida = (lec.valor is None
                    or dominio.fuera_del_rango_operativo(lec.valor))
        if invalida:
            if sw.encendida("RC-03"):
                veredictos.append(VeredictoLectura(
                    lote.lote_id, lec.indice, lec.produccion,
                    atribucion, regla_atribucion,
                    imputacion, regla_imputacion,
                    "invalida", "RC-03", None, None))
                # Ni abre ni cierra excursion, y no rompe la consecutividad
                # que exige RC-05 (CF-5).
                utiles.append(("invalida", lec, None))
            else:
                veredictos.append(VeredictoLectura(
                    lote.lote_id, lec.indice, lec.produccion,
                    atribucion, regla_atribucion,
                    imputacion, regla_imputacion,
                    None, None, None, None))
            continue
        validez, regla_validez = ("valida", "RC-03") if sw.encendida("RC-03") else (None, None)

        # --- RC-04 · umbral por tipo de producto, del LOTE --------------------
        if sw.encendida("RC-04"):
            fuera = _fuera_de_rango(lec.valor, lote.parametros)
            situacion = "fuera_de_rango" if fuera else "dentro_de_rango"
            regla_situacion = "RC-04"
        else:
            situacion, regla_situacion = None, None

        veredictos.append(VeredictoLectura(
            lote.lote_id, lec.indice, lec.produccion,
            atribucion, regla_atribucion,
            imputacion, regla_imputacion,
            validez, regla_validez,
            situacion, regla_situacion))
        utiles.append(("valida", lec, situacion))
    return veredictos, utiles


def _tramos_fuera_de_rango(utiles, sw):
    """RC-05 y RC-06: tramos consecutivos fuera de rango, con su cierre.

    Devuelve tuplas (apertura, cierre, abierta). Una lectura invalida no abre
    ni cierra y no rompe la consecutividad (CF-5).
    """
    tramos = []
    apertura = None
    for clase, lec, situacion in utiles:
        if clase == "invalida":
            continue
        if situacion == "fuera_de_rango":
            if apertura is None:
                apertura = lec.produccion
        else:
            if apertura is not None and sw.encendida("RC-06"):
                tramos.append((apertura, lec.produccion, False))
                apertura = None
    if apertura is not None:
        tramos.append((apertura, None, True))
    return tramos


def _huecos(utiles, parametros):
    """Tramos sin lectura valida. Un hueco de duracion >= la minima del tipo es
    determinante: puede esconder una excursion entera (RC-11)."""
    validas = [lec for clase, lec, _ in utiles if clase == "valida"]
    esperada = parametros.granularidad / 60.0
    huecos = []
    for anterior, siguiente in zip(validas, validas[1:]):
        separacion = (siguiente.produccion - anterior.produccion).total_seconds() / 60.0
        faltante = separacion - esperada
        if faltante > 0:
            huecos.append(faltante)
    return huecos


def _racha_final_dentro(utiles):
    """Minutos cubiertos por la ultima racha de lecturas dentro de rango.

    Solo se usa para el mutante de RC-08: sin la mitad de la irreversibilidad,
    una mejora sostenida rehabilitaria el lote. Con la regla encendida no
    rehabilita nada.
    """
    racha = []
    for clase, lec, situacion in utiles:
        if clase == "invalida":
            continue
        if situacion == "dentro_de_rango":
            racha.append(lec.produccion)
        else:
            racha = []
    if len(racha) < 2:
        return 0.0
    return (racha[-1] - racha[0]).total_seconds() / 60.0


def evaluar_lote(envio, lote, t_d, sw, registro):
    """Evalua UN lote contra las reglas de SU tipo de producto."""
    parametros = lote.parametros

    # Prefijo conocido en el instante de decision (RF-11).
    lecturas = sorted(envio.lecturas, key=lambda l: (l.produccion, l.indice))
    if t_d is not None:
        lecturas = [l for l in lecturas if l.produccion <= t_d]

    veredictos, utiles = _veredictos_de_lectura(envio, lote, lecturas, sw)

    ultimo_conocido = lecturas[-1].produccion if lecturas else lote.carga
    if t_d is not None:
        ultimo_conocido = t_d

    # --- El horizonte del prefijo --------------------------------------------
    # Hasta donde se conoce. No es un veredicto: lo fija el instante de decision,
    # no una regla. Va en su propio campo justamente para que no se confunda con
    # un cierre y no acabe atribuido a RC-12.
    conocido_hasta = ultimo_conocido

    # --- RC-12 · la conclusion se cierra en la entrega DEL LOTE ---------------
    # La entrega es un hecho del registro del lote, no algo que se infiera de las
    # lecturas: un lote entregado en T0+90 cierra ahi aunque la ultima lectura sea
    # de T0+70 (A-18). Lo que si limita es el instante de decision: si la entrega
    # todavia no ha ocurrido para quien decide, la conclusion NO esta cerrada.
    # Antes se recortaba cerrada_en hasta t_d conservando "RC-12", y eso atribuia
    # a la regla un valor que la regla no habia producido.
    if (sw.encendida("RC-12") and lote.entrega is not None
            and (t_d is None or lote.entrega <= t_d)):
        cerrada_en, regla_cierre_conclusion = lote.entrega, "RC-12"
    else:
        cerrada_en, regla_cierre_conclusion = None, None

    # --- RC-05 y RC-06 · apertura, cierre y duracion --------------------------
    excursiones = []
    for apertura, cierre, abierta in _tramos_fuera_de_rango(utiles, sw):
        regla_cierre = "RC-06"
        if abierta:
            # Una excursion abierta cierra en la entrega del lote (RC-12, L-14).
            if sw.encendida("RC-12") and lote.entrega is not None and lote.entrega <= ultimo_conocido:
                cierre = lote.entrega
                abierta = False
                # El cierre en la entrega lo dispara RC-12; la duracion en
                # intervalo semiabierto la calcula RC-06. Se nombran las dos.
                regla_cierre = "RC-06+RC-12" if sw.encendida("RC-06") else "RC-12"
            else:
                cierre = None
                regla_cierre = None
        fin = cierre if cierre is not None else ultimo_conocido
        duracion = reloj.minutos_entre(apertura, fin)
        if sw.encendida("RC-05") and duracion < parametros.duracion_minima:
            # Desviacion transitoria: se registra, no es excursion.
            excursiones.append(Excursion(apertura, cierre, duracion, abierta,
                                         True, "RC-05", regla_cierre))
            continue
        excursiones.append(Excursion(apertura, cierre, duracion, abierta, False,
                                     "RC-05" if sw.encendida("RC-05") else None,
                                     regla_cierre))

    reales = [e for e in excursiones if not e.transitoria]
    if sw.encendida("RC-05"):
        marca_excursiones = "con_excursion" if reales else "sin_excursion"
        regla_marca_excursiones = "RC-05"
    else:
        marca_excursiones, regla_marca_excursiones = None, None

    # --- RC-07 · acumulacion por lote ----------------------------------------
    if sw.encendida("RC-07"):
        acumulado = sum(e.duracion for e in reales)
        regla_acumulado = "RC-07"
    else:
        # Sin acumulacion, el plazo se mediria sobre una sola excursion.
        acumulado = max([e.duracion for e in reales], default=0)
        regla_acumulado = None

    # --- RC-08 · perdida del lote, en dos mitades -----------------------------
    aptitud, regla_aptitud = "apto", "RC-08"
    # Las dos mitades por separado, para que el almacen pueda escribirlas en dos
    # columnas. No cambian ningun desenlace: son lectura de lo que ya se decidio.
    umbral_superado = (sw.encendida("RC-08-umbral")
                       and acumulado > parametros.duracion_tolerada)
    irreversible_activa = umbral_superado and sw.encendida("RC-08-irreversibilidad")
    if sw.encendida("RC-08-umbral"):
        if acumulado > parametros.duracion_tolerada:
            aptitud = "no_apto"
            if not sw.encendida("RC-08-irreversibilidad"):
                # Mitad de la irreversibilidad apagada: una mejora sostenida
                # rehabilita el lote. Es justo lo que DN-07 prohibe.
                if _racha_final_dentro(utiles) >= parametros.duracion_minima:
                    aptitud = "apto"
    else:
        regla_aptitud = None

    # --- RC-11 · secuencia incompleta ----------------------------------------
    provisional = False
    if sw.encendida("RC-11"):
        huecos = _huecos(utiles, parametros)
        determinantes = [h for h in huecos if h >= parametros.duracion_minima]
        if determinantes:
            marca_secuencia = "hueco_determinante"
        elif huecos:
            marca_secuencia = "hueco_no_determinante"
        else:
            marca_secuencia = "completa"
        regla_marca_secuencia = "RC-11"
        if determinantes and aptitud == "apto":
            # CF-3: ni apto ni DISPOSICION. No consta que se perdiera.
            aptitud, regla_aptitud = "no_declarable_apto", "RC-11"
            provisional = True
    else:
        marca_secuencia, regla_marca_secuencia = None, None

    # --- RC-09 · clase de accion en el instante de decision -------------------
    if sw.encendida("RC-09"):
        abierta_ahora = any(e.abierta for e in reales)
        if sw.encendida("RC-08-umbral") and acumulado > parametros.duracion_tolerada and not provisional:
            clase_accion = "DISPOSICION"      # CF-2: gana sobre RESCATE
        elif abierta_ahora and not provisional:
            clase_accion = "RESCATE"
        else:
            clase_accion = "NINGUNA"
        regla_clase_accion = "RC-09"
    else:
        clase_accion, regla_clase_accion = None, None

    # --- RC-10 · el hecho actuable se registra una sola vez -------------------
    if clase_accion in ("RESCATE", "DISPOSICION"):
        ultima = reales[-1].apertura if reales else None
        registro.registrar(lote.lote_id, ultima, clase_accion)

    return ConclusionLote(
        lote.lote_id, lote.tipo_producto, t_d,
        aptitud, regla_aptitud,
        umbral_superado, irreversible_activa,
        acumulado, regla_acumulado,
        clase_accion, regla_clase_accion,
        marca_secuencia, regla_marca_secuencia,
        provisional,
        marca_excursiones, regla_marca_excursiones,
        cerrada_en, regla_cierre_conclusion,
        conocido_hasta,
        tuple(excursiones), tuple(veredictos))


def evaluar_caso(caso, sw):
    """Evalua el caso completo: un envio, sus lotes, sus instantes de decision.

    Las muertes del caso se modelan como redecisiones del mismo hecho actuable:
    el proceso vuelve a decidir lo mismo tras revivir. Aqui no muere ningun
    proceso -- eso no es este tramo--; lo que se ejerce es la regla de dominio
    RC-10, que es la que dice que dos decisiones del mismo hecho son una accion.
    """
    registro = RegistroAcciones(sw)
    evaluaciones = []
    for t_d in caso.instantes_decision:
        lotes = tuple(evaluar_lote(caso.envio, lote, t_d, sw, registro)
                      for lote in caso.envio.lotes)
        evaluaciones.append(Evaluacion(t_d, lotes))

    for _ in range(caso.redecisiones):
        for lote_id, apertura, clase in list(registro.hechos):
            registro.registrar(lote_id, reloj.instante(apertura), clase)

    return ConclusionCaso(caso.caso_id, tuple(evaluaciones), tuple(registro.acciones))
