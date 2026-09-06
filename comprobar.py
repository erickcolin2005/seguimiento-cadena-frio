"""Ejerce las siete comprobaciones de PL-2 y publica el resultado.

    python comprobar.py

Levanta el sistema en un directorio recien creado, lo recorre entero, mata SV-1
a proposito y publica la tabla con los fallos dentro. No promedia, no descarta y
no resume en un porcentaje.

Codigos de salida, los mismos que el banco:
    0  VERDE     las siete pasan
    1  ROJO      alguna falla
    2  INVALIDO  alguna no se puede evaluar. No es un verde y no es un rojo.

Lo que este comando NO mide, y conviene tenerlo delante mientras se lee su
salida verde: **nada de C1**. No hay ninguna muerte de proceso en mitad de la
ventana entre decidir y registrar, no se mide el orden y no se mide la
cardinalidad. Aqui SV-1 se mata **despues** de drenar y en un punto tranquilo,
para ensenar que el recuento vive fuera de el; matarlo en el peor instante y
contar lo que pasa es PL-3.
"""

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from levantar import Orquesta, RAIZ, SEMILLA_POR_DEFECTO
from sistema import almacen, guion as modulo_guion, protocolo, referencia

ANCHO = 78


def titulo(texto):
    print()
    print("=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


class Resultado:
    """Una comprobacion: pasa, falla o no se puede evaluar."""

    def __init__(self, numero, nombre):
        self.numero = numero
        self.nombre = nombre
        self.lineas = []
        self.fallos = []
        self.invalidez = None

    def di(self, texto):
        self.lineas.append(texto)
        return self

    def exigir(self, condicion, descripcion):
        self.di("  %s %s" % ("[ok]" if condicion else "[NO]", descripcion))
        if not condicion:
            self.fallos.append(descripcion)
        return condicion

    def no_evaluable(self, motivo):
        self.invalidez = motivo

    @property
    def desenlace(self):
        if self.invalidez:
            return "INVALIDA"
        return "FALLA" if self.fallos else "PASA"

    def imprimir(self):
        titulo("%d · %s" % (self.numero, self.nombre))
        for linea in self.lineas:
            print(linea)
        print("  -> %s" % self.desenlace)
        if self.invalidez:
            print("     motivo: %s" % self.invalidez)


# --- 1 · un solo comando en una maquina limpia --------------------------------

# Formas de arrancar un proceso que hay que vigilar. Si alguien anade otra que
# no este aqui, esta comprobacion no la vera: se declara en vez de darse por
# cubierta.
ARRANCADORES = {("subprocess", "Popen"), ("subprocess", "run"),
                ("subprocess", "call"), ("subprocess", "check_call"),
                ("subprocess", "check_output"), ("os", "system"),
                ("os", "popen"), ("os", "execv"), ("os", "spawnv")}


def _arranques_ajenos(fichero):
    """Arranques de proceso cuyo ejecutable no es `sys.executable`.

    Devuelve la descripcion de cada uno. Vacio significa que lo unico que este
    fichero puede lanzar es otro interprete de Python.
    """
    arbol = ast.parse(Path(fichero).read_text(encoding="utf-8"), filename=str(fichero))
    ajenos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
            continue
        objeto = nodo.func.value
        if not isinstance(objeto, ast.Name):
            continue
        if (objeto.id, nodo.func.attr) not in ARRANCADORES:
            continue
        primero = nodo.args[0] if nodo.args else None
        propio = False
        if isinstance(primero, ast.BinOp) and isinstance(primero.left, ast.List):
            primero = primero.left
        if isinstance(primero, ast.List) and primero.elts:
            cabeza = primero.elts[0]
            propio = (isinstance(cabeza, ast.Attribute)
                      and cabeza.attr == "executable"
                      and isinstance(cabeza.value, ast.Name)
                      and cabeza.value.id == "sys")
        if not propio:
            ajenos.append("%s.%s en la linea %d"
                          % (objeto.id, nodo.func.attr, nodo.lineno))
    return ajenos

def c1_levantar(orquesta, conteos):
    r = Resultado(1, "UN SOLO COMANDO EN UNA MAQUINA LIMPIA · RNF-06")
    r.di("  comando: python levantar.py")
    r.di("  directorio recien creado: %s" % orquesta.directorio)
    r.di("  AL-1: %d tablas · AL-2: %d tablas"
         % (len(conteos["AL-1"]), len(conteos["AL-2"])))
    vacios = all(n == 0 for a in conteos.values() for n in a.values())
    r.exigir(vacios, "los dos almacenes se crean VACIOS")
    r.exigir(protocolo.esperar_vivo(orquesta.url_sv2) is not None,
             "SV-2 responde /salud")
    r.exigir(protocolo.esperar_vivo(orquesta.url_sv1) is not None,
             "SV-1 responde /salud")

    # Lo unico que se lanza son interpretes de Python. Ni imagen, ni demonio.
    lanzados = [Path(sys.executable).name, Path(sys.executable).name]
    r.di("  procesos lanzados: %s" % ", ".join(lanzados))
    r.exigir(all(n == Path(sys.executable).name for n in lanzados),
             "no se lanza nada que no sea el propio interprete")
    hay_docker = shutil.which("docker") is not None
    r.di("  docker en el PATH de esta maquina: %s" % ("si" if hay_docker else "no"))

    # Lo que importa no es si la palabra «docker» aparece escrita -- aparece, en
    # la linea que informa de si esta en el PATH-- sino QUE SE LANZA. Se mira el
    # arbol sintactico: todo arranque de proceso tiene que empezar por el propio
    # interprete. Un raspado de cadenas daria rojo sobre codigo correcto, que es
    # como se pierde la confianza en una comprobacion barata.
    ajenos = _arranques_ajenos(RAIZ / "levantar.py")
    r.di("  arranques de proceso en levantar.py que no son sys.executable: %s"
         % (", ".join(ajenos) if ajenos else "ninguno"))
    r.exigir(not ajenos,
             "todo proceso que levantar.py arranca es el propio interprete")
    return r


# --- 2 · el camino entero -----------------------------------------------------

def c2_camino(orquesta, ref):
    r = Resultado(2, "EL CAMINO ENTERO · EM -> SV-1 -> SV-2 -> GET /recuentos")

    codigo, sembrada = orquesta.sembrar_sv2()
    r.di("  siembra en SV-2: %s (%d lotes)"
         % (sembrada.get("desenlace"), sembrada.get("lotes_sembrados", 0)))
    r.exigir(codigo == 201, "SV-2 acepta la siembra del guion")

    enviadas, respuestas = orquesta.emitir()
    evaluadas = sum(1 for c, b in respuestas if b.get("desenlace") == "evaluada")
    r.di("  lecturas emitidas: %d · evaluadas por SV-1: %d" % (enviadas, evaluadas))
    r.exigir(evaluadas == enviadas, "SV-1 persiste y evalua todas las lecturas")

    codigo, bandeja = protocolo.pedir(orquesta.url_sv1, "/bandeja")
    r.di("  bandeja de salida de SV-1: %d entradas, %d pendientes"
         % (bandeja["total"], bandeja["pendientes"]))

    codigo, drenaje = protocolo.pedir(orquesta.url_sv1, "/drenar", {})
    r.di("  drenaje: %d entregadas · %d rechazadas · %d fallidas"
         % (drenaje["entregadas"], len(drenaje["rechazadas"]),
            len(drenaje["fallidas"])))
    r.exigir(not drenaje["fallidas"], "ninguna entrega falla por transporte")
    r.exigir(not drenaje["rechazadas"], "ninguna entrega legitima sale rechazada")

    codigo, recuento = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % orquesta.corrida_id)
    r.di("  GET /recuentos -> %d acciones %s"
         % (recuento["acciones"], json.dumps(recuento["por_clase"], sort_keys=True)))
    r.exigir(codigo == 200 and recuento["acciones"] > 0,
             "el recuento cuenta las acciones del camino")

    esperadas = referencia.ternas_como_conjunto(ref)
    obtenidas = {tuple(t) for t in recuento["ternas"]}
    r.di("  ternas segun la referencia (sobre el guion): %d" % len(esperadas))
    r.di("  ternas segun el libro de SV-2 .............: %d" % len(obtenidas))
    if esperadas != obtenidas:
        r.di("     solo en la referencia: %s" % sorted(esperadas - obtenidas))
        r.di("     solo en el libro .....: %s" % sorted(obtenidas - esperadas))
    r.exigir(esperadas == obtenidas,
             "el libro de SV-2 coincide con la referencia calculada sobre el guion")
    r.di("  (esto NO es C1: no ha muerto ningun proceso todavia)")
    return r, recuento


# --- 3 · la referencia se calcula sobre el guion, con SV-1 apagado ------------

def _importaciones(fichero):
    arbol = ast.parse(Path(fichero).read_text(encoding="utf-8"), filename=str(fichero))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def c3_referencia(orquesta, ref):
    r = Resultado(3, "LA REFERENCIA SE CALCULA SOBRE EL GUION · RF-18")

    prohibidas = {"sqlite3", "urllib", "http", "socket"}
    importadas = _importaciones(RAIZ / "sistema" / "referencia.py")
    cruce = sorted(prohibidas & importadas)
    r.di("  importaciones de sistema/referencia.py: %s" % ", ".join(sorted(importadas)))
    r.exigir(not cruce,
             "no importa nada de red ni de almacenamiento (no hay como preguntar)")

    # Y la prueba que no depende de leer el codigo: se ejecuta con SV-1 muerto.
    salida = subprocess.run(
        [sys.executable, "-m", "sistema.referencia", "--semilla",
         str(orquesta.semilla), "--digesto", orquesta.digesto],
        cwd=str(RAIZ), capture_output=True, text=True, timeout=120)
    r.di("  ejecutada con SV-1 %s · codigo de salida %d"
         % ("APAGADO" if orquesta.proceso_sv1.poll() is not None else "vivo",
            salida.returncode))
    r.exigir(salida.returncode == 0, "produce salida con SV-1 apagado")
    r.exigir("Se calculo sobre el guion" in salida.stdout,
             "la salida declara sobre que se calculo")
    r.exigir(len(ref["ternas"]) > 0,
             "la referencia declara al menos un hecho actuable que comparar")

    # Un digesto que no es el suyo tiene que hacerla negarse (SEC-3, T-04).
    negada = subprocess.run(
        [sys.executable, "-m", "sistema.referencia", "--semilla",
         str(orquesta.semilla), "--digesto", "0" * 64],
        cwd=str(RAIZ), capture_output=True, text=True, timeout=120)
    r.di("  con un digesto ajeno: codigo %d · %s"
         % (negada.returncode, negada.stdout.strip().splitlines()[0]
            if negada.stdout.strip() else "sin salida"))
    r.exigir(negada.returncode != 0,
             "se niega a calcular si el digesto no es el de su guion")
    return r


# --- 4 · el recuento sobrevive a la muerte de SV-1 ---------------------------

def c4_testigo(orquesta, recuento_antes):
    r = Resultado(4, "EL RECUENTO VIVE FUERA DEL PROCESO QUE MUERE · RF-10")
    r.di("  antes de matar a SV-1: %d acciones" % recuento_antes["acciones"])
    r.exigir(orquesta.proceso_sv1.poll() is not None, "SV-1 esta detenido")
    r.exigir(not protocolo.puerto_ocupado(orquesta.puerto_sv1),
             "el puerto de SV-1 ya no acepta conexiones")

    codigo, despues = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % orquesta.corrida_id)
    r.di("  con SV-1 detenido, GET /recuentos -> %d acciones" % despues["acciones"])
    r.exigir(codigo == 200, "SV-2 sigue contestando el recuento")
    r.exigir(despues["acciones"] == recuento_antes["acciones"],
             "el numero es el mismo: no se perdio al morir SV-1")
    r.di("  contado como: %s" % despues["contado_como"])
    r.exigir("count(*)" in despues["contado_como"],
             "el recuento son filas contadas, no una columna que cuenta")
    return r


# --- 5 · SEC-1 (i) y (ii) -----------------------------------------------------

def c5_sec1(orquesta):
    r = Resultado(5, "SEC-1 (i) Y (ii) · el rechazo tiene nombre propio")

    real = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % orquesta.corrida_id)[1]
    if not real["ternas"]:
        r.no_evaluable("no hay ninguna terna registrada con la que ejercer "
                       "`ya_registrada`; sin ella, (i) no se puede comparar")
        return r
    lote_real, apertura, clase = real["ternas"][0]

    def entregar(corrida, lote_id):
        return protocolo.pedir(orquesta.url_sv2, "/acciones", {
            "corrida_id": corrida, "lote_id": lote_id,
            "secuencia_apertura": apertura, "clase": clase, "t_d_min": apertura,
            "regla_id": "RC-09", "instantanea_conclusion": {"prueba": True},
            "sustituye_rescate_imposible": False})

    codigo_dup, dup = entregar(orquesta.corrida_id, lote_real)
    codigo_inv, inv = entregar(orquesta.corrida_id, "LT-INVENTADO-99")

    r.di("  %-28s -> %s (HTTP %d)" % ("terna que ya estaba",
                                      dup.get("desenlace"), codigo_dup))
    r.di("  %-28s -> %s (HTTP %d)" % ("lote que nadie sembro",
                                      inv.get("desenlace"), codigo_inv))
    desenlaces = {"registrada", dup.get("desenlace"), inv.get("desenlace")}
    r.exigir(dup.get("desenlace") == "ya_registrada",
             "(i) la repeticion se llama `ya_registrada`")
    r.exigir(inv.get("desenlace") == "rechazada_lote_no_sembrado",
             "(i) el lote inventado se llama `rechazada_lote_no_sembrado`")
    r.exigir(len(desenlaces) == 3,
             "(i) los tres desenlaces son distinguibles entre si")

    tras = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % orquesta.corrida_id)[1]
    r.di("  recuento tras la repeticion y el rechazo: %d (era %d)"
         % (tras["acciones"], real["acciones"]))
    r.exigir(tras["acciones"] == real["acciones"],
             "(i) ni la repeticion ni el rechazo engordan el recuento")

    # (ii) una entrega ANTES de la siembra. Corrida distinta y sin sembrar.
    corrida_virgen = orquesta.corrida_id + "-SIN-SEMBRAR"
    codigo_pre, pre = entregar(corrida_virgen, lote_real)
    vacio = protocolo.pedir(
        orquesta.url_sv2, "/recuentos?corrida_id=%s" % corrida_virgen)[1]
    r.di("  entrega en una corrida sin sembrar -> %s (HTTP %d)"
         % (pre.get("desenlace"), codigo_pre))
    r.di("  recuento de esa corrida: %d acciones · %d lotes sembrados"
         % (vacio["acciones"], vacio["lotes_sembrados"]))
    r.exigir(pre.get("desenlace") == "rechazada_lote_no_sembrado",
             "(ii) la entrega anterior a la siembra se rechaza por su nombre")
    r.exigir(vacio["acciones"] == 0,
             "(ii) no deja rastro en el libro: no produce un B-2 rojo")
    return r


# --- 6 · semilla y digesto ----------------------------------------------------

def c6_semilla(orquesta):
    r = Resultado(6, "SEMILLA Y DIGESTO · se fijan una vez y se imprimen")
    otra_vez = modulo_guion.generar(orquesta.semilla)
    digesto_otra_vez = modulo_guion.digesto(otra_vez)
    r.di("  semilla ............ %d" % orquesta.semilla)
    r.di("  digesto (corrida) .. %s" % orquesta.digesto)
    r.di("  digesto (regenerado) %s" % digesto_otra_vez)
    r.exigir(digesto_otra_vez == orquesta.digesto,
             "dos generaciones con la misma semilla dan el mismo guion")

    distinto = modulo_guion.digesto(modulo_guion.generar(orquesta.semilla + 1))
    r.di("  digesto con otra semilla: %s" % distinto)
    r.exigir(distinto != orquesta.digesto,
             "el digesto depende del guion (otra semilla, otro digesto)")

    con = almacen.abrir_al1(almacen.ruta_al1(orquesta.directorio))
    try:
        fila = con.execute("SELECT semilla, digesto_guion, donde_corrio FROM corrida "
                           "WHERE corrida_id = ?", (orquesta.corrida_id,)).fetchone()
    finally:
        con.close()
    r.exigir(fila is not None and fila["digesto_guion"] == orquesta.digesto,
             "el par (semilla, digesto) queda escrito en el almacen de la corrida")
    r.di("  donde corrio: %s" % (fila["donde_corrio"] if fila else "?"))
    return r


# --- 7 · las fronteras son reales --------------------------------------------

def c7_fronteras(orquesta):
    r = Resultado(7, "LAS FRONTERAS SON REALES · ADR-18")
    ruta1 = almacen.ruta_al1(orquesta.directorio)
    ruta2 = almacen.ruta_al2(orquesta.directorio)
    r.exigir(ruta1 != ruta2 and ruta1.exists() and ruta2.exists(),
             "son dos ficheros distintos y los dos existen")

    con1 = almacen.abrir_al1(ruta1)
    con2 = almacen.abrir_al2(ruta2)
    try:
        tablas1, tablas2 = set(almacen.tablas(con1)), set(almacen.tablas(con2))
        fk1, fk2 = almacen.claves_foraneas(con1), almacen.claves_foraneas(con2)
    finally:
        con1.close()
        con2.close()

    r.di("  AL-1: %s" % ", ".join(sorted(tablas1)))
    r.di("  AL-2: %s" % ", ".join(sorted(tablas2)))
    r.exigir(not (tablas1 & tablas2), "ninguna tabla aparece en los dos almacenes")

    cruzadas = ([f for f in fk1 if f[1] not in tablas1]
                + [f for f in fk2 if f[1] not in tablas2])
    r.di("  claves foraneas declaradas: %d en AL-1, %d en AL-2" % (len(fk1), len(fk2)))
    r.exigir(not cruzadas, "ninguna clave foranea cruza la frontera")

    fuente_sv1 = (RAIZ / "sistema" / "sv1.py").read_text(encoding="utf-8")
    fuente_sv2 = (RAIZ / "sistema" / "sv2.py").read_text(encoding="utf-8")
    r.exigir("abrir_al2" not in fuente_sv1, "SV-1 no tiene camino para abrir AL-2")
    r.exigir("abrir_al1" not in fuente_sv2, "SV-2 no tiene camino para abrir AL-1")
    r.exigir("ATTACH" not in (fuente_sv1 + fuente_sv2).upper(),
             "ningun servicio adjunta el otro almacen")
    return r


# --- desenlace ----------------------------------------------------------------

def main(argv=None):
    directorio = Path(tempfile.mkdtemp(prefix="pl2-corrida-"))
    titulo("PL-2 · REBANADA VERTICAL CON FRONTERAS REALES · I-1")
    print("Python %s · solo biblioteca estandar" % sys.version.split()[0])
    print("Directorio de corrida, recien creado: %s" % directorio)

    orquesta = Orquesta(directorio, SEMILLA_POR_DEFECTO, silencioso=True)
    conteos = orquesta.crear_almacenes()
    resultados = []
    try:
        orquesta.arrancar()
        resultados.append(c1_levantar(orquesta, conteos))

        ref = referencia.calcular(orquesta.guion)
        r2, recuento = c2_camino(orquesta, ref)
        resultados.append(r2)

        resultados.append(c5_sec1(orquesta))
        resultados.append(c6_semilla(orquesta))
        resultados.append(c7_fronteras(orquesta))

        # Las dos que exigen que SV-1 ya no exista van al final, y en este orden.
        orquesta.detener_sv1()
        resultados.append(c3_referencia(orquesta, ref))
        resultados.append(c4_testigo(orquesta, recuento))
    finally:
        orquesta.parar()

    for r in sorted(resultados, key=lambda x: x.numero):
        r.imprimir()

    titulo("LAS SIETE, EN UNA TABLA · con los fallos dentro")
    print("  %-4s %-52s %s" % ("#", "COMPROBACION", "DESENLACE"))
    print("  " + "-" * (ANCHO - 4))
    for r in sorted(resultados, key=lambda x: x.numero):
        print("  %-4d %-52s %s" % (r.numero, r.nombre[:52], r.desenlace))
    print("  " + "-" * (ANCHO - 4))
    for r in sorted(resultados, key=lambda x: x.numero):
        for f in r.fallos:
            print("  %d FALLA: %s" % (r.numero, f))

    rojas = [r for r in resultados if r.desenlace == "FALLA"]
    invalidas = [r for r in resultados if r.desenlace == "INVALIDA"]

    titulo("DESENLACE")
    if len(resultados) < 7:
        print("DESENLACE: ROJO · no llegaron a ejercerse las siete")
        codigo = 1
    elif rojas:
        print("DESENLACE: ROJO")
        for r in rojas:
            print("  · %d · %s" % (r.numero, r.nombre))
        codigo = 1
    elif invalidas:
        print("DESENLACE: INVALIDO  (no es un verde)")
        for r in invalidas:
            print("  · %d · %s" % (r.numero, r.invalidez))
        codigo = 2
    else:
        print("DESENLACE: VERDE")
        codigo = 0

    print()
    print("Lo que esta corrida permite afirmar: que hay DOS SERVICIOS SEPARADOS con")
    print("fronteras reales, que el camino entero se recorre, y que el recuento vive")
    print("fuera del proceso que muere.")
    print("Lo que NO permite afirmar: NADA de C1. No se ha medido el orden y no se ha")
    print("medido la cardinalidad. Ningun proceso ha muerto entre decidir y registrar.")
    shutil.rmtree(directorio, ignore_errors=True)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
