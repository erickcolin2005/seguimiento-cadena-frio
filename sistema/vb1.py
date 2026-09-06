"""VB-1 · la verificacion bloqueante de PL-3. Va antes que todo lo demas.

    python -m sistema.vb1

**Que decide.** Si el compromiso del almacen es duradero **a granularidad de
muerte de proceso**. Si no lo es, `PS-A` no esta donde el diseno dice que esta,
y **todo lo que se mida despues mide otra cosa**: C1-B contaria acciones sobre
un punto de control que no existe.

**Por que va primero.** Es la unica comprobacion del plan que puede tirar abajo
el resto del tramo, y cuesta unos segundos. Construir dos instrumentos encima de
un punto de control inexistente cuesta bastante mas.

**Si falla, PL-3 se detiene.** No se construye M5 ni M6. Vuelve a
`architect-agent`, no a `engineering-agent`: lo que falla es **la ubicacion del
punto de control**, que es diseno. Y no hay ningun umbral aqui que se pueda
bajar -- CD2 obliga a declararlo, no a aflojar el criterio.

## Las dos mitades, porque una sola no decide nada

La bandeja de salida promete que **o estan la conclusion y la intencion de
actuar, o no esta ninguna**. Eso son dos afirmaciones opuestas y hacen falta las
dos:

  **(A) durabilidad** · se compromete, se mata el proceso **sin darle ocasion de
  ordenar nada**, y en un proceso NUEVO las filas siguen ahi.

  **(B) atomicidad** · se escribe **sin comprometer**, se mata igual, y en un
  proceso NUEVO **no hay ni una sola** de esas filas.

Con (A) sola, un almacen que escribiera siempre y nunca deshiciera pasaria: la
bandeja tendria intenciones de actuar que ninguna conclusion respalda. Con (B)
sola pasaria uno que no escribiera nunca. **Juntas, acotan por los dos lados.**

## Como se mata, y por que asi

El proceso hijo se mata con la via mas brusca que ofrece la plataforma:
`Popen.kill()` -- `SIGKILL` donde existe, `TerminateProcess` en Windows. Ni
manejadores, ni `atexit`, ni cierre ordenado del fichero, ni vaciado de nada.
Es la muerte que C1-B va a provocar cincuenta veces, y por eso se prueba esta y
no un cierre educado.

**Lo que VB-1 NO mide, y se dice:** la muerte de la MAQUINA. Un corte de
corriente o un panico del sistema operativo no estan aqui `[NV]`. Lo que el
diseno afirma y este tramo necesita es la muerte del PROCESO, que es lo que se
mide. Un fallo de la maquina entera se declara fuera del alcance del MVP.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import almacen

RAIZ = Path(__file__).resolve().parent.parent
CORRIDA_VB1 = "CO-VB1"
FILAS = 25


def _filas(marca, cuantas):
    """Entradas de bandeja de salida sinteticas. La clave primaria es la terna."""
    return [(CORRIDA_VB1, "LT-VB1-%s-%02d" % (marca, i), i, "RESCATE", i,
             "RC-09", json.dumps({"vb1": marca}), 0, "PENDIENTE", 0, "vb1")
            for i in range(cuantas)]


INSERTAR = ("INSERT INTO bandeja_salida (corrida_id, lote_id, secuencia_apertura, "
            "clase, t_d_min, regla_id, instantanea_conclusion, "
            "sustituye_rescate_imposible, estado, intentos, commit_pared) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")


# --- los tres papeles del hijo -----------------------------------------------

def hijo_comprometido(directorio, cuantas):
    """Escribe, COMPROMETE, avisa y se queda quieto esperando la muerte."""
    con = almacen.abrir_al1(almacen.ruta_al1(directorio))
    con.execute("BEGIN IMMEDIATE")
    con.executemany(INSERTAR, _filas("A", cuantas))
    con.execute("COMMIT")
    # A partir de esta linea el compromiso ya volvio. Lo que pase con este
    # proceso ya no deberia poder deshacerlo.
    print("COMPROMETIDO", flush=True)
    while True:
        time.sleep(0.2)


def hijo_sin_comprometer(directorio, cuantas):
    """Escribe y NO compromete. Avisa con la transaccion abierta."""
    con = almacen.abrir_al1(almacen.ruta_al1(directorio))
    con.execute("BEGIN IMMEDIATE")
    con.executemany(INSERTAR, _filas("B", cuantas))
    print("ESCRITO_SIN_COMPROMETER", flush=True)
    while True:
        time.sleep(0.2)


def hijo_leer(directorio):
    """Un proceso NUEVO: abre el fichero desde cero y cuenta lo que hay."""
    con = almacen.abrir_al1(almacen.ruta_al1(directorio))
    filas = con.execute(
        "SELECT lote_id FROM bandeja_salida WHERE corrida_id = ? ORDER BY lote_id",
        (CORRIDA_VB1,)).fetchall()
    lotes = [f["lote_id"] for f in filas]
    print(json.dumps({
        "total": len(lotes),
        "comprometidas": sum(1 for l in lotes if "-A-" in l),
        "sin_comprometer": sum(1 for l in lotes if "-B-" in l),
    }))


# --- el padre -----------------------------------------------------------------

def _lanzar(argumentos):
    return subprocess.Popen([sys.executable, "-m", "sistema.vb1"] + argumentos,
                            cwd=str(RAIZ), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)


def _matar_tras_aviso(proceso, aviso, espera=60.0):
    """Espera la linea de aviso y mata al hijo por la via mas brusca que haya.

    Devuelve (llego_el_aviso, como_murio). Se lee la linea antes de matar: sin
    eso no se sabria si se mato antes o despues del momento que interesa, y la
    comprobacion no mediria nada.
    """
    limite = time.time() + espera
    linea = ""
    while time.time() < limite:
        linea = proceso.stdout.readline()
        if linea.strip() == aviso:
            break
        if proceso.poll() is not None:
            return False, "murio solo"
    else:
        return False, "no aviso a tiempo"
    if linea.strip() != aviso:
        return False, "aviso distinto: %r" % linea.strip()
    proceso.kill()                       # SIGKILL / TerminateProcess
    proceso.wait(timeout=30)
    return True, "kill() · codigo %s" % proceso.returncode


def _leer_en_proceso_nuevo(directorio):
    salida = subprocess.run(
        [sys.executable, "-m", "sistema.vb1", "--papel", "leer",
         "--directorio", str(directorio)],
        cwd=str(RAIZ), capture_output=True, text=True, timeout=120)
    if salida.returncode != 0:
        raise RuntimeError("el lector no pudo abrir el almacen: %s"
                           % (salida.stderr or salida.stdout)[-300:])
    return json.loads(salida.stdout.strip())


def ejecutar(directorio, cuantas=FILAS):
    """Las dos mitades. Devuelve (pasa, lineas, detalle)."""
    lineas = []
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    # El fichero se crea aqui y se cierra: los hijos lo abren ellos.
    almacen.abrir_al1(almacen.ruta_al1(directorio)).close()

    # --- (A) durabilidad ------------------------------------------------------
    hijo = _lanzar(["--papel", "comprometido", "--directorio", str(directorio),
                    "--filas", str(cuantas)])
    aviso_a, muerte_a = _matar_tras_aviso(hijo, "COMPROMETIDO")
    tras_a = _leer_en_proceso_nuevo(directorio)
    lineas.append("(A) durabilidad · %d filas comprometidas, despues %s"
                  % (cuantas, muerte_a))
    lineas.append("    el proceso llego a comprometer antes de morir: %s"
                  % ("si" if aviso_a else "NO"))
    lineas.append("    leidas en un proceso NUEVO: %d de %d"
                  % (tras_a["comprometidas"], cuantas))
    durabilidad = aviso_a and tras_a["comprometidas"] == cuantas

    # --- (B) atomicidad -------------------------------------------------------
    hijo = _lanzar(["--papel", "sin-comprometer", "--directorio", str(directorio),
                    "--filas", str(cuantas)])
    aviso_b, muerte_b = _matar_tras_aviso(hijo, "ESCRITO_SIN_COMPROMETER")
    tras_b = _leer_en_proceso_nuevo(directorio)
    lineas.append("(B) atomicidad · %d filas escritas SIN comprometer, despues %s"
                  % (cuantas, muerte_b))
    lineas.append("    el proceso llego a escribir antes de morir: %s"
                  % ("si" if aviso_b else "NO"))
    lineas.append("    leidas en un proceso NUEVO: %d (tienen que ser 0)"
                  % tras_b["sin_comprometer"])
    atomicidad = aviso_b and tras_b["sin_comprometer"] == 0

    # Y lo comprometido en (A) sigue ahi despues de (B): la muerte a mitad de
    # una transaccion no se lleva por delante lo que ya estaba.
    superviviente = tras_b["comprometidas"] == cuantas
    lineas.append("    y lo comprometido en (A) sigue ahi: %d de %d"
                  % (tras_b["comprometidas"], cuantas))

    return (durabilidad and atomicidad and superviviente), lineas, {
        "durabilidad": durabilidad, "atomicidad": atomicidad,
        "comprometido_sobrevive": superviviente,
        "tras_A": tras_a, "tras_B": tras_b}


def main(argv=None):
    partes = argparse.ArgumentParser(description="VB-1 · verificacion bloqueante")
    partes.add_argument("--papel", default="padre",
                        choices=("padre", "comprometido", "sin-comprometer", "leer"))
    partes.add_argument("--directorio", default=None)
    partes.add_argument("--filas", type=int, default=FILAS)
    args = partes.parse_args(argv)

    if args.papel == "comprometido":
        hijo_comprometido(args.directorio, args.filas)
        return 0
    if args.papel == "sin-comprometer":
        hijo_sin_comprometer(args.directorio, args.filas)
        return 0
    if args.papel == "leer":
        hijo_leer(args.directorio)
        return 0

    import tempfile
    directorio = Path(args.directorio) if args.directorio else Path(
        tempfile.mkdtemp(prefix="vb1-"))
    print("=" * 78)
    print("VB-1 · ¿ES DURADERO EL COMPROMISO FRENTE A LA MUERTE DEL PROCESO?")
    print("=" * 78)
    print("Va antes que todo lo demas de PL-3. Si falla, PL-3 se detiene y el")
    print("problema vuelve a diseno: no hay ningun umbral que se pueda bajar.")
    print()
    print("directorio: %s" % directorio)
    print("se mata con: Popen.kill() · SIGKILL donde existe, TerminateProcess en")
    print("Windows. Sin manejadores, sin atexit, sin cierre ordenado.")
    print()

    pasa, lineas, detalle = ejecutar(directorio, args.filas)
    for linea in lineas:
        print("  %s" % linea)
    print()
    print("  PS-A esta donde el diseno dice: %s" % ("SI" if pasa else "NO"))
    print()
    print("=" * 78)
    if pasa:
        print("VB-1: PASA · PL-3 puede continuar")
    else:
        print("VB-1: FALLA · PL-3 SE DETIENE")
        print("  No se construye M5 ni M6. Vuelve a `architect-agent`: lo que falla")
        print("  es la ubicacion del punto de control, y eso es diseno.")
    print("=" * 78)
    print()
    print("Lo que VB-1 NO mide: la muerte de la MAQUINA. Un corte de corriente o un")
    print("panico del sistema operativo no estan aqui, y se declara en vez de")
    print("darse por cubierto.")
    return 0 if pasa else 1


if __name__ == "__main__":
    sys.exit(main())
