"""Las comprobaciones de PL-1 que no son «los casos pasan».

Cada una devuelve (pasa, lineas). Ninguna afirma nada que no ejecute.
"""

import ast
import dataclasses
import inspect
import sys
from pathlib import Path

from . import casos as modulo_casos
from . import conclusion as modulo_conclusion
from . import dominio, motor, reloj, verificar
from .piezas import PIEZAS, Interruptores

CARPETA = Path(__file__).parent


# --- Criterio 1 · determinismo -----------------------------------------------

def determinismo(casos_primera, conclusiones_primera):
    """Dos ejecuciones seguidas dan el mismo veredicto y la misma regla.

    La segunda ejecucion se hace con **otro T0**: se mueve el instante de
    referencia y se recargan los casos desde disco. Si algo del banco dependiera
    del reloj de pared y no de las marcas de las lecturas, aqui se veria.
    """
    lineas = []
    t0_original = reloj.T0
    t0_segunda = t0_original + (reloj.instante(7) - reloj.instante(0))

    # El digesto escribe los instantes como desplazamientos desde reloj.T0, asi
    # que cada corrida se digiere con SU T0 puesto. Tomar el de la segunda
    # despues de restaurar el original la mostraria entera desplazada +7 y los 64
    # casos divergirian por como se compara, no por lo que hace el banco.
    digestos_primera = {c.caso_id: verificar.digesto(conclusiones_primera[c.caso_id])
                        for c in casos_primera}
    try:
        reloj.T0 = t0_segunda
        segunda = modulo_casos.cargar()
        digestos_segunda = {c.caso_id: verificar.digesto(
            motor.evaluar_caso(c, Interruptores())) for c in segunda}
    finally:
        reloj.T0 = t0_original

    # Sigue teniendo dientes: si alguna regla mirara el reloj de pared en vez de
    # las marcas de las lecturas, su desplazamiento no coincidiria y se veria.
    divergentes = [c.caso_id for c in casos_primera
                   if digestos_primera[c.caso_id] != digestos_segunda[c.caso_id]]
    lineas.append("ejecucion 1 con T0 = %s · ejecucion 2 con T0 = %s (+7 min)"
                  % (t0_original.strftime("%H:%M"), t0_segunda.strftime("%H:%M")))
    lineas.append("casos comparados: %d · con veredicto o regla distinta: %d"
                  % (len(casos_primera), len(divergentes)))
    if divergentes:
        lineas.append("divergentes: %s" % ", ".join(divergentes))
    return not divergentes, lineas


# --- Criterio 2 · ninguna conclusion pasa sin nombrar su regla ---------------

def _sin_regla_situacion(conclusion):
    """Devuelve la misma conclusion con un identificador de regla borrado."""
    evaluacion = conclusion.evaluaciones[0]
    lote = evaluacion.lotes[0]
    veredictos = list(lote.veredictos)
    veredictos[0] = dataclasses.replace(veredictos[0], regla_situacion=None)
    lote = dataclasses.replace(lote, veredictos=tuple(veredictos))
    evaluacion = dataclasses.replace(evaluacion, lotes=(lote,) + evaluacion.lotes[1:])
    return dataclasses.replace(conclusion,
                               evaluaciones=(evaluacion,) + conclusion.evaluaciones[1:])


def conclusion_nombra_su_regla(casos, conclusiones):
    """A un caso que pasa se le quita el identificador de regla: debe fallar."""
    lineas = []
    caso = next(c for c in casos if c.caso_id == "A-01")
    original = conclusiones["A-01"]
    fallos_antes = verificar.verificar(caso, original)
    mutilada = _sin_regla_situacion(original)
    fallos_despues = verificar.verificar(caso, mutilada)

    lineas.append("A-01 con su regla: %d fallos" % len(fallos_antes))
    lineas.append("A-01 sin el identificador de regla de la lectura: %d fallos"
                  % len(fallos_despues))
    for f in fallos_despues:
        lineas.append("   %s" % f)

    # Y ademas: ningun veredicto afirmado en la corrida entera se queda sin regla.
    mudos = 0
    for caso in casos:
        for evaluacion in conclusiones[caso.caso_id].evaluaciones:
            for lote in evaluacion.lotes:
                for campo, regla in verificar.REGLA_DE_CAMPO.items():
                    if not hasattr(lote, campo):
                        continue
                    if getattr(lote, campo) is not None and getattr(lote, regla) is None:
                        mudos += 1
                for ver in lote.veredictos:
                    for campo, regla in verificar.REGLA_DE_CAMPO.items():
                        if not hasattr(ver, campo):
                            continue
                        if getattr(ver, campo) is not None and getattr(ver, regla) is None:
                            mudos += 1
    lineas.append("veredictos emitidos en toda la corrida sin regla que los nombre: %d"
                  % mudos)
    return (not fallos_antes and bool(fallos_despues) and mudos == 0), lineas


# --- Criterio 4 · el tipo de producto vive en el lote ------------------------

def esquema_por_lote():
    """Evaluar por envio no esta desaconsejado: no hay camino para escribirlo."""
    lineas = []
    fallos = []

    campos_envio = {f.name for f in dataclasses.fields(dominio.Envio)}
    if "tipo_producto" in campos_envio:
        fallos.append("Envio tiene un campo tipo_producto")
    lineas.append("campos de Envio: %s" % ", ".join(sorted(campos_envio)))

    campos_lote = {f.name for f in dataclasses.fields(dominio.Lote)}
    if "tipo_producto" not in campos_lote:
        fallos.append("Lote no tiene tipo_producto")
    lineas.append("campos de Lote: %s" % ", ".join(sorted(campos_lote)))

    # No se le puede poner uno: la clase es congelada y con slots.
    envio = dominio.Envio("EN-00", (), ())
    try:
        envio.tipo_producto = "P-REF"
        fallos.append("se pudo escribir Envio.tipo_producto")
        excepcion = "ninguna"
    except (AttributeError, dataclasses.FrozenInstanceError) as error:
        excepcion = type(error).__name__
    lineas.append("escribir Envio.tipo_producto levanta: %s" % excepcion)

    if hasattr(dominio.Envio, "parametros"):
        fallos.append("Envio expone parametros (umbrales) sin pasar por un lote")
    lineas.append("Envio.parametros existe: %s" % hasattr(dominio.Envio, "parametros"))
    lineas.append("Lote.parametros existe: %s" % hasattr(dominio.Lote, "parametros"))

    # Los umbrales solo se alcanzan indexando TIPOS, y eso solo ocurre dentro
    # de Lote.parametros. Se comprueba sobre el codigo fuente.
    # El patron se arma partido a proposito: escrito entero, este fichero se
    # encontraria a si mismo y se acusaria de alcanzar los umbrales. La salida
    # seria excluir a este modulo de la busqueda, y una lista de exclusiones es
    # justo el sitio por donde una comprobacion se queda ciega.
    patron = "TIPOS" + "["
    indexan = []
    for fichero in sorted(CARPETA.glob("*.py")):
        texto = fichero.read_text(encoding="utf-8")
        if patron in texto and fichero.name != "dominio.py":
            indexan.append(fichero.name)
    if indexan:
        fallos.append("modulos que alcanzan los umbrales sin pasar por un lote: %s"
                      % ", ".join(indexan))
    lineas.append("modulos que indexan TIPOS fuera de dominio.py: %s"
                  % (", ".join(indexan) if indexan else "ninguno"))

    # Ninguna funcion del motor recibe un envio para decidir aptitud: la firma
    # de la evaluacion pide un lote.
    firma = inspect.signature(motor.evaluar_lote)
    if "lote" not in firma.parameters:
        fallos.append("motor.evaluar_lote no recibe un lote")
    lineas.append("firma de motor.evaluar_lote: %s" % firma)

    # Y no existe ninguna conclusion a nivel de envio: la aptitud es del lote.
    con_aptitud = []
    for nombre, objeto in vars(modulo_conclusion).items():
        if not dataclasses.is_dataclass(objeto) or not isinstance(objeto, type):
            continue
        campos = {f.name for f in dataclasses.fields(objeto)}
        if "aptitud" in campos:
            con_aptitud.append(nombre)
            if "envio_id" in campos:
                fallos.append("%s lleva aptitud y envio_id: es una conclusion de envio"
                              % nombre)
    lineas.append("clases de conclusion con campo aptitud: %s"
                  % ", ".join(con_aptitud))

    for f in fallos:
        lineas.append("FALLO: %s" % f)
    return not fallos, lineas


# --- Criterio 5 · un solo comando, sin dependencias --------------------------

def solo_biblioteca_estandar():
    """Todo lo que el banco importa esta en la biblioteca estandar.

    Se mide sobre las importaciones del codigo propio, leidas del fuente, y no
    sobre sys.modules: el interprete de esta maquina carga cosas de
    site-packages por ficheros .pth antes de que corra una sola linea nuestra.
    Contarlas como dependencia del banco seria un rojo falso; no mencionarlas
    seria esconder el entorno. Se hacen las dos cosas por separado: se mide lo
    propio y se declara lo ajeno.

    Lo que esta comprobacion NO detecta: un fichero puesto en el arbol con el
    nombre de un modulo estandar. Se declara aqui en vez de darse por cubierto.
    """
    lineas = []
    propios = sorted(CARPETA.glob("*.py")) + [CARPETA.parent / "ejecutar.py"]
    importados = set()
    for fichero in propios:
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    importados.add(alias.name.split(".")[0])
            elif isinstance(nodo, ast.ImportFrom) and not nodo.level and nodo.module:
                importados.add(nodo.module.split(".")[0])

    fuera = sorted(n for n in importados
                   if n not in sys.stdlib_module_names and n != "banco")

    precargados = sorted(
        nombre for nombre, modulo in list(sys.modules.items())
        if (getattr(modulo, "__file__", None)
            and ("site-packages" in modulo.__file__.replace("\\", "/").lower()
                 or "dist-packages" in modulo.__file__.replace("\\", "/").lower())))

    lineas.append("Python: %s" % sys.version.split()[0])
    lineas.append("modulos que el banco importa (%d): %s"
                  % (len(importados), ", ".join(sorted(importados))))
    lineas.append("de esos, fuera de la biblioteca estandar: %s"
                  % (", ".join(fuera) if fuera else "ninguno"))
    lineas.append("precargados por el interprete via .pth, ajenos al banco: %s"
                  % (", ".join(precargados) if precargados else "ninguno"))
    lineas.append("ficheros del banco: %d modulos y %d ficheros de casos"
                  % (len(list(CARPETA.glob("*.py"))),
                     len(list((CARPETA / "casos").glob("*.json")))))
    return not fuera, lineas


def piezas_declaradas():
    """Las trece piezas existen y RC-08 esta partida en dos."""
    lineas = ["piezas apagables: %d" % len(PIEZAS)]
    lineas.append(" · ".join(PIEZAS))
    mitades = [p for p in PIEZAS if p.startswith("RC-08")]
    return len(PIEZAS) == 13 and len(mitades) == 2, lineas
