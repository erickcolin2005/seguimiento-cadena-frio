"""El cinturón de calidad entero, en el orden en que hay que pagarlo.

    python cinturon.py

Ocho etapas, de la más barata a la más cara. La primera no arranca un solo
proceso; la quinta mata cincuenta y seis. **El orden no es estético: un push que
va a salir rojo por una frase prohibida no debe pagar cientos de muertes de
proceso antes de descubrirlo.**

## Los códigos de salida, y por qué no son 0 y 1

    0   APROBADO
    20  FALLO             de C1, de una capa, o del propio cinturón
    30  MEDICION INVALIDA con su motivo
    cualquier otro        MEDICION INVALIDA por causa no atribuida

**El espacio no reservado es INVÁLIDO, y eso es lo importante.** El código 1 lo
produce cualquier excepción no atendida de casi cualquier runtime, y el 137 una
muerte por falta de memoria. Si FALLO fuera 1, **una excepción del instrumento se
leería como «el sistema perdió una acción»** — y esas son dos cosas distintas:
*«la prueba dejó de ejercer el fallo»* no es *«el sistema perdió una acción»*.
Reservar solo los códigos que el proceso elige hace que la confusión sea
imposible **por construcción, y no por disciplina**.

Para un CI que solo entiende éxito y fallo: **éxito ⟺ código 0 exacto**. FALLO e
INVÁLIDO se representan los dos como fallo. La asimetría es deliberada.

## Lo que este fichero NO hace, y es una prohibición

**No reintenta por color.** FALLO e INVÁLIDO comparten color, así que un reintento
automático reintentaría un FALLO válido — y *un FALLO válido no se repite jamás;
repetir un rojo hasta que salga verde es lavarlo*. La política de repeticiones es
del instrumento, no del CI: se decide **aquí dentro**, leyendo el motivo, y solo
para las causas no deterministas.

## La auto-guardia

La etapa 0 se lee a sí misma y al fichero del CI, y pone **ROJO** si encuentra
cualquiera de las formas conocidas de anular un veredicto: una tubería que
ignora el código de salida, una continuación tras error declarada en el
proveedor, el desarme del corte por error en un guion de consola, o un reintento
automático. **Excepción única y nombrada:** la ejecución incondicional es
obligatoria en el paso que sube la evidencia, porque ahí lo que garantiza es que
el INVÁLIDO se publique. *Se permite en la publicación; se prohíbe en el
veredicto.*

Los patrones se arman **partidos en trozos** a propósito. Escritos enteros, este
fichero se encontraría a sí mismo y daría rojo sobre un pipeline correcto. La
salida fácil sería excluir a este fichero de la búsqueda, **y una lista de
exclusiones es justo el sitio por donde una comprobación se queda ciega**.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ANCHO = 78

APROBADO, FALLO, INVALIDO = 0, 20, 30
NOMBRE = {APROBADO: "APROBADO", FALLO: "FALLO", INVALIDO: "MEDICION INVALIDA"}

# CE-5 · las tres expresiones que no se han ganado todavía.
FRASES_PROHIBIDAS = ("arquitectura distribuida", "tolerante a fallos",
                     "sistema por eventos")
PUBLICABLES = ("README.md", "NOTAS-PL2.md", "NOTAS-PL3.md", "NOTAS-PL4.md",
               "banco/NOTAS-IMPLEMENTACION.md")

# DL-9 · lo que la auto-guardia no puede encontrar en el pipeline. Partidos a
# proposito: enteros, este fichero se acusaria a si mismo.
VENENOS = ("|" + "| true", "continue-" + "on-error", "set " + "+e",
           "exit 0 " + "#", "ret" + "ry", "reintento " + "automatico")
FICHERO_CI = ".github/workflows/cinturon.yml"
PASO_DE_EVIDENCIA = "if: always()"      # la excepcion nombrada de DL-9

REFERENCIA_DIGESTO = Path("banco/DIGESTO-REFERENCIA.txt")

# U-06 · tres ejecuciones (1 + 2 repeticiones), y SOLO para las causas no
# deterministas. Una invalidez determinista no se repite: repetirla es gastar el
# elemento mas caro del proyecto para volver a leer el mismo hueco.
EJECUCIONES = 3
MOTIVOS_DETERMINISTAS = ("sin calibracion", "T-23", "hacen falta")


def titulo(texto):
    print()
    print("=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Etapa:
    """Una etapa del cinturón. Emite un veredicto, o declara que no emitió.

    **El desenlace no se decide por ausencia de fallos, sino por presencia de
    veredictos.** Una etapa que no llegó a emitir no cuenta como verde: cuenta
    como capa que falta, y eso es invalidez.
    """

    def __init__(self, codigo, nombre, que_corre):
        self.codigo = codigo
        self.nombre = nombre
        self.que_corre = que_corre
        self.emitio = False
        self.veredicto = None          # APROBADO / FALLO / INVALIDO
        self.motivo = ""
        self.lineas = []
        self.segundos = 0.0
        self.procesos = 0

    def resolver(self, veredicto, motivo=""):
        self.emitio = True
        self.veredicto = veredicto
        self.motivo = motivo
        return self

    def di(self, texto):
        self.lineas.append(texto)


# --- utilidades de medida -----------------------------------------------------

class Contador:
    """Cuenta los procesos que el cinturón arranca **directamente**.

    No es el total de procesos de la corrida, y decirlo importa: la etapa de
    medición arranca a su vez servicios y los mata decenas de veces. Publicar
    «3 procesos» a secas para un cinturón que provoca cientos de muertes sería
    exactamente el tipo de número que este proyecto no publica. El total real se
    lee del artefacto de la medición y se imprime al lado.
    """

    def __init__(self):
        self.procesos = 0

    def correr(self, argumentos, tiempo=None):
        self.procesos += 1
        return subprocess.run([sys.executable, "-u"] + argumentos,
                              cwd=str(RAIZ), capture_output=True, text=True,
                              timeout=tiempo)


def muertes_de_la_medicion(carpeta):
    """Muertes de proceso provocadas dentro de la medicion, leidas del artefacto.

    Se lee del dato, no se estima. Si el artefacto no esta, se devuelve None y
    la linea no se imprime: un numero que no se pudo leer no se inventa.
    """
    ruta = Path(carpeta) / "c1b.json"
    if not ruta.exists():
        return None
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    tandas = 1 if datos.get("calibracion") is None else 3
    return datos.get("muertes", 0) * tandas


def digesto_del_banco():
    """Digesto de los casos y del mapa de mutación. Es lo que U-13 vigila."""
    h = hashlib.sha256()
    for ruta in sorted((RAIZ / "banco" / "casos").glob("*.json")):
        h.update(ruta.name.encode("utf-8"))
        h.update(ruta.read_bytes())
    mapa = RAIZ / "banco" / "mapa-mutacion.json"
    h.update(mapa.read_bytes())
    return h.hexdigest()


def inventario_del_banco():
    """Enumera los casos del banco. U-10: se cuenta, no se declara."""
    total, familias = 0, {}
    for ruta in sorted((RAIZ / "banco" / "casos").glob("*.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        casos = datos["casos"] if isinstance(datos, dict) else datos
        for caso in casos:
            total += 1
            familia = caso["caso_id"].split("-")[0]
            familias[familia] = familias.get(familia, 0) + 1
    return total, familias


# --- EP-0 · la estática -------------------------------------------------------

def ep0_estatica(contador):
    e = Etapa("EP-0", "ESTATICA · el gate de texto",
              "CE-5 · digesto del banco · inventario · auto-guardia")
    fallos = []

    # CT-12 · las tres frases prohibidas, en los artefactos publicables.
    for nombre in PUBLICABLES:
        ruta = RAIZ / nombre
        if not ruta.exists():
            continue
        bajo = ruta.read_text(encoding="utf-8").lower()
        encontradas = [f for f in FRASES_PROHIBIDAS if f in bajo]
        if encontradas:
            fallos.append("CE-5 · %s contiene %s" % (nombre, ", ".join(encontradas)))
    e.di("  CE-5 · %d artefactos publicables revisados, 0 frases prohibidas"
         % len(PUBLICABLES) if not fallos else "  CE-5 · HAY FRASES PROHIBIDAS")

    # U-13 / DL-2 · el digesto del banco contra su referencia versionada.
    actual = digesto_del_banco()
    ruta_ref = RAIZ / REFERENCIA_DIGESTO
    if not ruta_ref.exists():
        e.di("  U-13 · no hay digesto de referencia: se fija ahora, %s" % actual[:16])
        ruta_ref.write_text(actual + "\n", encoding="utf-8")
    else:
        esperado = ruta_ref.read_text(encoding="utf-8").strip()
        e.di("  U-13 · digesto del banco %s · referencia %s"
             % (actual[:16], esperado[:16]))
        if actual != esperado:
            fallos.append("U-13 · el banco cambió sin actualizar su digesto de "
                          "referencia. Un cambio al banco se declara en un commit "
                          "que solo hace eso")

    # U-10 · el inventario se enumera, no se declara.
    total, familias = inventario_del_banco()
    e.di("  U-10 · casos enumerados: %d · %s"
         % (total, " ".join("%s=%d" % kv for kv in sorted(familias.items()))))
    if total != 64:
        fallos.append("U-10 · el banco enumera %d casos y se esperaban 64" % total)

    # DL-9 · la auto-guardia, sobre este fichero y sobre el del CI.
    revisados, envenenados = [], []
    for nombre in ("cinturon.py", FICHERO_CI):
        ruta = RAIZ / nombre
        if not ruta.exists():
            e.di("  DL-9 · %s no existe todavia" % nombre)
            continue
        revisados.append(nombre)
        texto = ruta.read_text(encoding="utf-8")
        for numero, linea in enumerate(texto.splitlines(), start=1):
            # Los comentarios explican la prohibicion; no la cometen.
            if linea.strip().startswith("#"):
                continue
            bajo = linea.lower()
            for veneno in VENENOS:
                if veneno in bajo and PASO_DE_EVIDENCIA not in bajo:
                    envenenados.append("%s:%d · %s" % (nombre, numero, veneno))
    e.di("  DL-9 · ficheros de pipeline revisados: %s" % ", ".join(revisados))
    e.di("  DL-9 · patrones que anularian el veredicto: %s"
         % (", ".join(envenenados) if envenenados else "ninguno"))
    if envenenados:
        fallos.append("DL-9 · el pipeline contiene algo que anula su veredicto")

    for f in fallos:
        e.di("  FALLO: %s" % f)
    return e.resolver(FALLO if fallos else APROBADO, "; ".join(fallos))


# --- EP-1 y EP-2 · el banco y su mutación ------------------------------------

def ep1_ep2_banco(contador):
    e = Etapa("EP-1+2", "BANCO Y MUTACION POR REGLA",
              "64 casos · determinismo · 13 piezas × 4 condiciones")
    salida = contador.correr(["ejecutar.py"], tiempo=900)
    texto = salida.stdout
    for marca in ("superados ...", "(a)  sensibilidad", "(b)  discriminacion",
                  "(c1) localizacion", "(c2) extension"):
        for linea in texto.splitlines():
            if marca in linea:
                e.di("  " + linea.strip())
                break
    if salida.returncode == 0:
        return e.resolver(APROBADO)
    if salida.returncode == 2:
        return e.resolver(INVALIDO, "el banco no pudo evaluar una condicion de "
                                    "mutacion")
    if salida.returncode == 1:
        return e.resolver(FALLO, "el banco o su mutacion fallan")
    return e.resolver(INVALIDO, "el banco termino con un codigo que no eligio: %d"
                      % salida.returncode)


# --- EP-3 · el preflight que evita pagar la tanda en vano --------------------

def ep3_preflight(contador):
    e = Etapa("EP-3", "PREFLIGHT DE LA MEDICION",
              "VB-1 · que los dos mutantes existen y se distinguen")
    vb1 = contador.correr(["-m", "sistema.vb1"], tiempo=600)
    e.di("  VB-1 · codigo %d · %s" % (vb1.returncode,
                                      "PASA" if vb1.returncode == 0 else "FALLA"))
    if vb1.returncode != 0:
        # Lo que falla es el instrumento, no el sistema medido, y el retorno es
        # a diseño: PS-A no estaria donde el diseño dice.
        return e.resolver(INVALIDO, "VB-1 no pasa: el compromiso no es duradero "
                                    "frente a la muerte del proceso, asi que las "
                                    "muertes siguientes medirian otra cosa")

    # DL-4 · que los dos mutantes existen y son distinguibles cuesta dos
    # arranques; descubrirlo despues costaria la tanda entera.
    fuente_sv1 = (RAIZ / "sistema" / "sv1.py").read_text(encoding="utf-8")
    fuente_sv2 = (RAIZ / "sistema" / "sv2.py").read_text(encoding="utf-8")
    tiene_m1 = "--marca-antes-de-enviar" in fuente_sv1
    tiene_m2 = "--receptor-no-idempotente" in fuente_sv2
    e.di("  MUT-1 (marca antes de enviar) declarado: %s" % ("si" if tiene_m1 else "NO"))
    e.di("  MUT-2 (receptor no idempotente) declarado: %s" % ("si" if tiene_m2 else "NO"))
    if not (tiene_m1 and tiene_m2):
        return e.resolver(INVALIDO, "falta alguno de los dos mutantes: sin los dos "
                                    "la calibracion no puede demostrar la ventana")
    return e.resolver(APROBADO)


# --- EP-4 … EP-7 · la medición ------------------------------------------------

def ep4_a_ep7_medicion(contador, repeticiones_c1a, repeticiones_c1b,
                       sin_calibracion, carpeta_evidencia):
    e = Etapa("EP-4..7", "C1-A · C1-B · CALIBRACION · SEC-5",
              "la medicion completa, con su veredicto DP-02")
    argumentos = ["veredicto.py",
                  "--repeticiones-c1a", str(repeticiones_c1a),
                  "--repeticiones-c1b", str(repeticiones_c1b),
                  "--evidencia", str(carpeta_evidencia)]
    if sin_calibracion:
        argumentos.append("--sin-calibracion")
    salida = contador.correr(argumentos, tiempo=7200)
    for linea in salida.stdout.splitlines():
        if linea.startswith("VEREDICTO DE LA CORRIDA:") or linea.startswith("  · "):
            e.di("  " + linea.strip())
    if salida.returncode == 0:
        return e.resolver(APROBADO)
    if salida.returncode == 1:
        return e.resolver(FALLO, "hay divergencias de orden o hechos actuables con "
                                 "cero o con dos acciones")
    if salida.returncode == 2:
        motivos = [l.strip() for l in salida.stdout.splitlines()
                   if l.startswith("  · ")]
        return e.resolver(INVALIDO, "; ".join(motivos) or "la corrida no midio")
    return e.resolver(INVALIDO, "la medicion termino con un codigo que no eligio: %d"
                      % salida.returncode)


# --- EP-8 · agregación y veredicto -------------------------------------------

def agregar(etapas):
    """DL-1 · la precedencia. Y no se decide por ausencia de fallos.

    Una capa que no emitió no es una capa verde: es una capa que falta, y eso es
    invalidez. Si se decidiera por ausencia de fallos, un cinturón que no llegó a
    correr saldria aprobado.
    """
    sin_emitir = [e for e in etapas if not e.emitio]
    rojas = [e for e in etapas if e.veredicto == FALLO]
    invalidas = [e for e in etapas if e.veredicto == INVALIDO]
    if rojas:
        return FALLO, ["%s · %s" % (e.codigo, e.motivo) for e in rojas]
    if invalidas:
        return INVALIDO, ["%s · %s" % (e.codigo, e.motivo) for e in invalidas]
    if sin_emitir:
        return INVALIDO, ["%s · la capa no llego a emitir veredicto" % e.codigo
                          for e in sin_emitir]
    return APROBADO, []


def es_determinista(motivos):
    """Una invalidez determinista NO se repite. Repetirla es gastar el elemento
    mas caro del proyecto para volver a leer exactamente el mismo hueco."""
    texto = " ".join(motivos).lower()
    return any(m.lower() in texto for m in MOTIVOS_DETERMINISTAS)


def main(argv=None):
    partes = argparse.ArgumentParser(description="El cinturon entero · DL-6")
    partes.add_argument("--repeticiones-c1a", type=int, default=2)
    partes.add_argument("--repeticiones-c1b", type=int, default=14)
    partes.add_argument("--sin-calibracion", action="store_true",
                        help="DEMOSTRACION DL-10: fuerza un INVALIDO")
    partes.add_argument("--carpeta", default="evidencia/pl-4/corrida",
                        help="carpeta propia de ESTA corrida. Dos corridas no "
                             "comparten carpeta: la evidencia de una sobrescribiria "
                             "la de la otra y la tabla publicada dejaria de "
                             "corresponder a su artefacto (DL-12)")
    args = partes.parse_args(argv)

    carpeta = RAIZ / args.carpeta
    carpeta.mkdir(parents=True, exist_ok=True)
    arranque = time.time()
    contador = Contador()
    titulo("CINTURON DE CALIDAD · ocho etapas, de la mas barata a la mas cara")
    print("Python %s · solo biblioteca estandar" % sys.version.split()[0])
    print("Instante de arranque: %s" % ahora())

    etapas = []
    ejecuciones_hechas = 0

    def cronometrar(funcion, *extra):
        t0, p0 = time.time(), contador.procesos
        etapa = funcion(contador, *extra)
        etapa.segundos = time.time() - t0
        etapa.procesos = contador.procesos - p0
        etapas.append(etapa)
        titulo("%s · %s" % (etapa.codigo, etapa.nombre))
        print("  %s" % etapa.que_corre)
        for linea in etapa.lineas:
            print(linea)
        print("  -> %s  (%.1f s · %d procesos)"
              % (NOMBRE[etapa.veredicto], etapa.segundos, etapa.procesos))
        return etapa

    cronometrar(ep0_estatica)
    if agregar(etapas)[0] == FALLO:
        pass                     # DL-5: se corta entre etapas, no dentro
    else:
        cronometrar(ep1_ep2_banco)
        if agregar(etapas)[0] == APROBADO:
            cronometrar(ep3_preflight)
            if agregar(etapas)[0] == APROBADO:
                for intento in range(EJECUCIONES):
                    ejecuciones_hechas = intento + 1
                    etapa = cronometrar(ep4_a_ep7_medicion,
                                        args.repeticiones_c1a,
                                        args.repeticiones_c1b,
                                        args.sin_calibracion,
                                        carpeta)
                    if etapa.veredicto != INVALIDO:
                        break
                    if es_determinista([etapa.motivo]):
                        etapa.di("  la causa es DETERMINISTA: no se repite")
                        print("  · la causa de la invalidez es determinista: "
                              "repetirla leeria el mismo hueco. No se repite.")
                        break
                    if intento + 1 < EJECUCIONES:
                        print("  · invalidez de causa no determinista: se repite "
                              "(%d de %d)" % (intento + 2, EJECUCIONES))
                        etapas.pop()

    codigo, motivos = agregar(etapas)
    segundos = time.time() - arranque

    # --- CE-2 · la factura del cinturon --------------------------------------
    titulo("CE-2 · LA FACTURA DEL CINTURON")
    print("  %-24s %10s %10s" % ("ETAPA", "SEGUNDOS", "PROCESOS"))
    print("  " + "-" * (ANCHO - 4))
    for e in etapas:
        print("  %-24s %10.1f %10d" % (e.codigo, e.segundos, e.procesos))
    print("  " + "-" * (ANCHO - 4))
    print("  %-24s %10.1f %10d" % ("TOTAL", segundos, contador.procesos))
    muertes = muertes_de_la_medicion(carpeta)
    if muertes is not None:
        print("  procesos que la medicion MATA por dentro: %d" % muertes)
        print("  (el %d de arriba son los hijos DIRECTOS del cinturon)"
              % contador.procesos)
    print("  ejecuciones de la medicion: %d de %d permitidas (U-06)"
          % (ejecuciones_hechas, EJECUCIONES))
    print()
    print("  Lo que este numero NO es: minutos de un proveedor de CI. Aqui no hay")
    print("  proveedor elegido, y este proyecto no admite ninguna cifra de minutos,")
    print("  ningun precio y ningun nombre de plan sin la cita literal de su")
    print("  documentacion de limites. Lo medido es tiempo de pared y procesos")
    print("  arrancados EN ESTA MAQUINA. [NV] el limite del proveedor.")
    print("  Memoria y minutos de CPU: NO MEDIDOS. La biblioteca estandar no los")
    print("  da de forma portable en esta plataforma y no se instala nada (CE-3).")

    # --- el artefacto crudo, del que se genera la tabla ----------------------
    artefacto = {
        "instante": ahora(),
        "veredicto": NOMBRE[codigo], "codigo": codigo, "motivos": motivos,
        "segundos_total": round(segundos, 1),
        "procesos_directos": contador.procesos,
        "muertes_provocadas_por_la_medicion": None,
        "ejecuciones_medicion": ejecuciones_hechas,
        "digesto_banco": digesto_del_banco(),
        "donde_corrio": sys.platform,
        "python": sys.version.split()[0],
        "etapas": [{"codigo": e.codigo, "nombre": e.nombre,
                    "veredicto": NOMBRE[e.veredicto] if e.emitio else "NO EMITIO",
                    "motivo": e.motivo, "segundos": round(e.segundos, 1),
                    "procesos": e.procesos} for e in etapas],
        "no_medido": ["minutos y limites del proveedor de CI",
                      "memoria y minutos de CPU",
                      "muerte de la maquina", "carga", "concurrencia externa"],
    }
    destino = carpeta / "corrida.json"
    artefacto["muertes_provocadas_por_la_medicion"] = muertes
    destino.write_text(json.dumps(artefacto, indent=2, sort_keys=True),
                       encoding="utf-8")

    titulo("VEREDICTO DEL CINTURON: %s  (codigo %d)" % (NOMBRE[codigo], codigo))
    for m in motivos:
        print("  · %s" % m)
    if codigo == INVALIDO:
        print()
        print("  UNA MEDICION INVALIDA NO ES UN DEFECTO DEL SISTEMA MEDIDO.")
    print()
    print("  Artefacto crudo: %s" % destino.relative_to(RAIZ))
    print("  La tabla publicable se genera DESDE ese artefacto, nunca a mano: una")
    print("  tabla tecleada es una tabla en la que alguien pudo elegir que filas")
    print("  copiaba.")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
