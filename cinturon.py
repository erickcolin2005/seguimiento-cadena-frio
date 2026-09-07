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
import ast
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

# CE-5 · ya no es «tres frases prohibidas». La prohibicion no se borro al
# cumplirse el tramo: CAMBIO DE OBJETO.
#
# Dos de las tres expresiones las compra M11, y M11 existe: la medicion entera
# se repitio sobre el otro transporte y dio lo mismo. Pero comprarlas no es
# poder decirlas a secas -- la condicion exige que quien las use diga SOBRE QUE
# se midio--. Asi que ahora se permiten SOLO si la evidencia que las respalda
# esta publicada y en verde. Levantar la regla sin poner nada en su sitio
# habria sido cambiarla por un hueco.
FRASES_COMPRADAS = ("arquitectura distribuida", "sistema por eventos")

# Y una que NO se compro y sigue prohibida. El tramo autoriza hablar de la
# arquitectura y de los eventos; NO autoriza esta. Lo medido es la muerte del
# PROCESO dentro de una ventana, en una maquina: eso no es tolerancia a fallos
# en general, y usar la expresion seria afirmar lo que nadie midio.
FRASES_PROHIBIDAS = ("tolerante a fallos",)

# La evidencia que compra las dos primeras, y el comando que la reproduce.
EVIDENCIA_EVENTOS = "evidencia/pl-6-eventos/corrida.json"
COMANDO_EVENTOS = "--transporte eventos"
def publicables():
    """Todo texto publicable del repositorio, DERIVADO y no escrito a mano.

    Una lista escrita a mano deja escapar al artefacto nuevo: basta con que
    alguien olvide anadirlo, y el guardian de CE-5 no lo vera nunca. Es la misma
    familia de defecto que una lista de exclusiones, y aqui se cierra igual —
    no manteniendo la lista, sino no teniendola.
    """
    rutas = sorted(RAIZ.glob("*.md"))
    rutas += sorted((RAIZ / "banco").glob("*.md"))
    rutas += sorted((RAIZ / "evidencia").rglob("*.md"))
    rutas += sorted((RAIZ / "decisiones").glob("*.md"))
    return rutas

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


def donde_corrio():
    """Dónde corrió DE VERDAD, nunca dónde se suponía que iba a correr.

    La etiqueta se deriva del entorno, no de una constante escrita a mano: una
    corrida etiquetada «CI» porque alguien lo tecleó no dice nada. Y **no lleva
    ninguna ruta**: SEC-7 (ii) prohíbe rutas personales en el artefacto
    publicado, y el sitio natural por donde se cuela una es justo este campo.
    """
    en_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))
    return {
        "etiqueta": ("CI · maquina efimera del proveedor" if en_ci
                     else "maquina local del autor"),
        "derivada_de": "variable de entorno CI/GITHUB_ACTIONS",
        "plataforma": sys.platform,
        "python": sys.version.split()[0],
    }


# SEC-7 (ii) · lo que no puede aparecer en un artefacto publicado.
RUTAS_PERSONALES = (
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+", re.I),
    re.compile(r"/home/[^/\s\"']+"),
    re.compile(r"AppData", re.I),
    re.compile(r"\\Documents\\", re.I),
)


def rutas_personales_en(carpeta):
    """Toda ruta personal que aparezca en la evidencia publicable.

    Se mira el CONTENIDO, no solo el campo `donde_corrio`: una ruta se cuela
    igual de bien en un mensaje de error copiado que en un campo declarado.
    """
    encontradas = []
    for ruta in sorted(Path(carpeta).rglob("*")):
        if not ruta.is_file():
            continue
        try:
            texto = ruta.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for patron in RUTAS_PERSONALES:
            for hallazgo in patron.findall(texto):
                encontradas.append("%s · %s" % (ruta.name, hallazgo))
    return encontradas


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


def bloque_sec6(carpeta):
    """Los siete elementos que SEC-6 exige que estén EN el artefacto.

    No es un resumen bonito: es la lista cerrada. **Si falta uno, SEC-6 no está
    cumplida**, y por eso cada elemento lleva escrito qué es y qué NO es. La
    sexta lleva su etiqueta pegada a propósito: `entrega_repetida` es evidencia
    de REINTENTO, no de muerte en ventana, y leerla como lo segundo convertiría
    un mecanismo funcionando en un hallazgo que no existe.
    """
    def leer(nombre):
        ruta = Path(carpeta) / nombre
        if not ruta.exists():
            return None
        return json.loads(ruta.read_text(encoding="utf-8"))

    a, b = leer("c1a.json"), leer("c1b.json")
    if a is None or b is None:
        return {"completo": False,
                "falta": "no hay artefacto de medicion del que leer los elementos"}
    cal = b.get("calibracion")
    return {
        "completo": True,
        "1_construccion_medida": {
            "envios": b["envios"], "lotes": b["lotes"],
            "hechos_actuables": b["hechos_actuables"],
            "que_es": "sobre que se midio, enumerado y no declarado"},
        "2_puntos_armados_y_muertes_por_punto": {
            "muertes": b["muertes"], "por_instante": b["muertes_por_instante"],
            "sin_nada_en_curso": b["muertes_sin_nada_en_curso"],
            "que_es": "donde se mato y cuantas veces en cada punto"},
        "3_mutantes_y_sus_anomalias": (
            {"M-1": cal["M-1"], "M-2": cal["M-2"],
             "total": cal["anomalias_totales"],
             "que_es": "la refutacion: sin anomalias, la tanda no entro en la "
                       "ventana"}
            if cal else {"ausente": True}),
        "4_semilla_y_digesto": {
            "semilla": b["semilla"], "digesto_c1a": a["digesto_guion"],
            "digesto_c1b": b["digesto_guion"],
            "que_es": "con que se puede reproducir esto exactamente"},
        "5_inversiones": {
            "observadas": a["inversiones_observadas"],
            "decisivas": a["inversiones_decisivas"],
            "decisivas_por_clase": a["por_clase"],
            "sin_clase": a["sin_clase"],
            "que_es": "los DOS numeros. El denominador son las decisivas; el "
                      "otro se publica al lado, nunca en su lugar"},
        "6_entregas_repetidas": {
            "veces": b["entregas_repetidas"],
            "etiqueta": "EVIDENCIA DE REINTENTO, NO DE MUERTE EN VENTANA",
            "que_no_es": "no son acciones duplicadas ni hechos perdidos: son "
                         "entregas que llegaron dos veces y contaron una. Leerlas "
                         "como muertes en ventana convertiria un mecanismo "
                         "funcionando en un hallazgo que no existe"},
        "7_ausencia_de_calibracion": {
            "hay_calibracion": cal is not None,
            "regla": "la ausencia de calibracion es MEDICION INVALIDA, jamas "
                     "APROBADO",
            "demostrado_en": "evidencia/pl-4/invalido/"},
    }


def _sin_finales_de_linea(ruta):
    """Los bytes del fichero con los finales de linea normalizados.

    Un final de linea NO es contenido del banco. Sin esta normalizacion el
    digesto cambia segun el sistema en que se clone el repositorio -- git
    entrega CRLF en Windows y LF en Linux--, y entonces U-13 deja de vigilar el
    banco y pasa a vigilar el checkout.

    No es hipotetico: la primera vez que este proyecto corrio en una maquina
    que no era la de su autor, EP-0 salio FALLO por esto. `61-muerte-tanda.json`
    estaba con CRLF y los otros siete con LF, asi que el digesto de Windows y el
    de Linux nunca podian coincidir. El detector medía lo que no era.
    """
    return ruta.read_bytes().replace(b"\r\n", b"\n")


def digesto_del_banco():
    """Digesto de los casos y del mapa de mutación. Es lo que U-13 vigila."""
    h = hashlib.sha256()
    for ruta in sorted((RAIZ / "banco" / "casos").glob("*.json")):
        h.update(ruta.name.encode("utf-8"))
        h.update(_sin_finales_de_linea(ruta))
    h.update(_sin_finales_de_linea(RAIZ / "banco" / "mapa-mutacion.json"))
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

    # CT-12 · CE-5, en TODO artefacto publicable. Dos comprobaciones, no una.
    revisados = publicables()

    # (i) La que sigue prohibida sin excepcion: nadie la compro.
    con_prohibida = []
    for ruta in revisados:
        bajo = ruta.read_text(encoding="utf-8").lower()
        encontradas = [f for f in FRASES_PROHIBIDAS if f in bajo]
        if encontradas:
            con_prohibida.append("%s (%s)" % (ruta.relative_to(RAIZ),
                                              ", ".join(encontradas)))
    e.di("  CE-5(i) · %d artefactos publicables revisados (lista DERIVADA, no "
         "escrita a mano) · con frase aun prohibida: %s"
         % (len(revisados), ", ".join(con_prohibida) if con_prohibida else "ninguno"))
    if con_prohibida:
        fallos.append("CE-5 · frase que nadie compro, en: %s"
                      % "; ".join(con_prohibida))

    # (ii) Las que M11 compra: permitidas SOLO con su evidencia detras. La
    # afirmacion fuerte no se prohibe; se le exige el denominador, que es lo
    # mismo que este proyecto hace con las inversiones decisivas.
    usan_fuerte = sorted({str(r.relative_to(RAIZ)) for r in revisados
                          for f in FRASES_COMPRADAS
                          if f in r.read_text(encoding="utf-8").lower()})
    if not usan_fuerte:
        e.di("  CE-5(ii) · nadie usa la afirmacion fuerte: nada que respaldar")
    else:
        respaldo = RAIZ / EVIDENCIA_EVENTOS
        motivos = []
        if not respaldo.exists():
            motivos.append("no existe %s" % EVIDENCIA_EVENTOS)
        else:
            crudo = json.loads(respaldo.read_text(encoding="utf-8"))
            if crudo.get("transporte") != "eventos":
                motivos.append("la evidencia no es del transporte por eventos "
                               "(dice %r)" % crudo.get("transporte"))
            if crudo.get("veredicto") != "APROBADO":
                motivos.append("la corrida de respaldo no esta en verde (dice %r)"
                               % crudo.get("veredicto"))
        # Y que se pueda REPRODUCIR: sin el comando, el lector tiene que
        # creerse la tabla en vez de volver a sacarla.
        legible = (RAIZ / "README.md").read_text(encoding="utf-8")
        if COMANDO_EVENTOS not in legible:
            motivos.append("el README no publica el comando que la reproduce (%s)"
                           % COMANDO_EVENTOS)
        e.di("  CE-5(ii) · la usan %d artefactos · respaldo: %s"
             % (len(usan_fuerte), "; ".join(motivos) if motivos else "en verde"))
        if motivos:
            fallos.append("CE-5 · se afirma de mas: la frase fuerte se usa en %s "
                          "y %s" % (", ".join(usan_fuerte), "; ".join(motivos)))

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

    # SEC-7 (ii) · ninguna ruta personal en lo que se publica. Mecanico, no una
    # inspeccion que alguien tenga que acordarse de hacer.
    personales = rutas_personales_en(RAIZ / "evidencia")
    e.di("  SEC-7(ii) · rutas personales en la evidencia publicable: %s"
         % (", ".join(personales[:3]) if personales else "ninguna"))
    if personales:
        fallos.append("SEC-7(ii) · la evidencia publicable contiene %d rutas "
                      "personales" % len(personales))

    for f in fallos:
        e.di("  FALLO: %s" % f)
    return e.resolver(FALLO if fallos else APROBADO, "; ".join(fallos))


# --- EP-1 y EP-2 · el banco y su mutación ------------------------------------

def ep1_ep2_banco(contador):
    e = Etapa("EP-1+2", "BANCO Y MUTACION POR REGLA",
              "64 casos · determinismo · 13 piezas × 4 condiciones")
    salida = contador.correr(["ejecutar.py"], tiempo=900)
    # Se toman las lineas de RESULTADO, no las de leyenda. El banco imprime
    # primero la explicacion de cada condicion y despues su cifra, asi que
    # quedarse con la primera coincidencia devuelve el texto y tira el dato --
    # justo lo contrario de lo que este proyecto publica.
    texto = salida.stdout
    for marca in ("superados ...", "(a)  sensibilidad", "(b)  discriminacion",
                  "(c1) localizacion", "(c2) extension"):
        for linea in texto.splitlines():
            if marca in linea and ("/13" in linea or "superados" in linea):
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

    # La garantia NO puede vivir en el transporte. Se comprueba por estructura y
    # no de palabra: un adaptador SIN memoria no puede deduplicar aunque quiera.
    # Si pudiera, cambiar de transporte cambiaria la garantia -- y entonces M11
    # no seria cambiar un adaptador, seria rediseñar.
    fuente = (RAIZ / "sistema" / "transporte.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    importa = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importa.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importa.add(nodo.module.split(".")[0])
        elif isinstance(nodo, ast.ImportFrom) and nodo.level:
            importa.update(a.name for a in nodo.names)
    prohibidos = sorted(importa & {"sqlite3", "almacen", "motor", "banco"})
    e.di("  el transporte importa: %s" % ", ".join(sorted(importa)))
    e.di("  de eso, memoria o reglas: %s"
         % (", ".join(prohibidos) if prohibidos else "nada"))
    if prohibidos:
        return e.resolver(FALLO, "la garantia se filtro al transporte: importa %s, "
                                 "asi que podria deduplicar u ordenar por su cuenta"
                          % ", ".join(prohibidos))
    return e.resolver(APROBADO)


# --- EP-4 … EP-7 · la medición ------------------------------------------------

def ep4_a_ep7_medicion(contador, repeticiones_c1a, repeticiones_c1b,
                       sin_calibracion, carpeta_evidencia,
                       modo_transporte="directo"):
    e = Etapa("EP-4..7", "C1-A · C1-B · CALIBRACION · SEC-5",
              "la medicion completa, con su veredicto DP-02 · transporte %s"
              % modo_transporte)
    argumentos = ["veredicto.py",
                  "--repeticiones-c1a", str(repeticiones_c1a),
                  "--repeticiones-c1b", str(repeticiones_c1b),
                  "--transporte", modo_transporte,
                  "--evidencia", str(carpeta_evidencia)]
    if sin_calibracion:
        argumentos.append("--sin-calibracion")
    salida = contador.correr(argumentos, tiempo=7200)
    vistas = []
    for linea in salida.stdout.splitlines():
        if linea.startswith("VEREDICTO DE LA CORRIDA:") or linea.startswith("  · "):
            limpia = linea.strip()
            if limpia not in vistas:      # la medicion lo imprime arriba y abajo
                vistas.append(limpia)
                e.di("  " + limpia)
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
    partes.add_argument("--carpeta", default="evidencia/ultima-corrida",
                        help="carpeta propia de ESTA corrida. Dos corridas no "
                             "comparten carpeta: la evidencia de una sobrescribiria "
                             "la de la otra y la tabla publicada dejaria de "
                             "corresponder a su artefacto (DL-12). Por defecto se "
                             "escribe en `ultima-corrida`, que NO se versiona: la "
                             "corrida de quien prueba el proyecto no debe caer "
                             "dentro de la evidencia publicada de un tramo")
    partes.add_argument("--transporte", default="directo",
                        choices=("directo", "eventos"),
                        help="sobre que transporte corre la medicion. `directo` "
                             "no necesita red, ni imagen, ni credencial, ni "
                             "instalar nada; `eventos` necesita el intermediario "
                             "levantado y el cliente que no trae la biblioteca "
                             "estandar. El predeterminado es el que sostiene RNF-06")
    args = partes.parse_args(argv)

    carpeta = RAIZ / args.carpeta
    carpeta.mkdir(parents=True, exist_ok=True)
    arranque = time.time()
    contador = Contador()
    titulo("CINTURON DE CALIDAD · ocho etapas, de la mas barata a la mas cara")
    if args.transporte == "directo":
        print("Python %s · solo biblioteca estandar" % sys.version.split()[0])
    else:
        # Decirlo aqui y no solo en las notas: la frase de arriba dejaria de ser
        # cierta en esta corrida, y una cabecera que miente es peor que una que
        # no esta.
        print("Python %s · biblioteca estandar MAS un cliente del intermediario"
              % sys.version.split()[0])
    print("Transporte de esta corrida: %s" % args.transporte)
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
                                        carpeta,
                                        args.transporte)
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
    # CE-2 · durante siete tramos esta nota decia que no habia proveedor elegido
    # y que aqui no entraba ninguna cifra sin la cita literal de su
    # documentacion. Ya hay proveedor y ya hay cita, asi que la nota cambia --
    # pero la disciplina no: el numero de arriba sigue siendo tiempo de pared de
    # ESTA maquina, y no son minutos facturables de nadie.
    print("  Lo que este numero NO es: minutos facturables de un proveedor. Es")
    print("  tiempo de pared y procesos arrancados EN ESTA MAQUINA, y las dos")
    print("  cifras se publican etiquetadas y nunca promediadas.")
    print("  El limite del proveedor, citado literal de su documentacion:")
    print("    «Each job in a workflow can run for up to 6 hours of execution")
    print("     time.» -- atribuido a All GitHub-hosted runners")
    print("    «GitHub Actions usage is free for standard GitHub-hosted runners")
    print("     in public repositories.»")
    print("    «These limits are subject to change.»")
    print("  Detalle y margen medido: evidencia/ce2-el-cinturon-en-ci.md")
    print("  Memoria y minutos de CPU: NO MEDIDOS. La biblioteca estandar no los")
    print("  da de forma portable en esta plataforma y no se instala nada para")
    print("  medirlos (CE-3).")
    if args.transporte == "eventos":
        # Sin esto, la cifra de arriba se leeria como comparable con la del
        # transporte directo, y no lo es: esta lleva dentro el arranque de los
        # consumidores y sus reequilibrados. Compararlas sin decirlo seria
        # publicar una mejora o un empeoramiento que nadie midio.
        print("  ESTA corrida NO es comparable con la del transporte directo sin")
        print("  decir por que: lleva dentro el alta de cada consumidor y sus")
        print("  reequilibrados, que el transporte directo no tiene. Las dos")
        print("  cifras se publican juntas y etiquetadas, nunca una sola.")

    # --- el artefacto crudo, del que se genera la tabla ----------------------
    artefacto = {
        "instante": ahora(),
        "veredicto": NOMBRE[codigo], "codigo": codigo, "motivos": motivos,
        "segundos_total": round(segundos, 1),
        "procesos_directos": contador.procesos,
        "muertes_provocadas_por_la_medicion": None,
        "ejecuciones_medicion": ejecuciones_hechas,
        "digesto_banco": digesto_del_banco(),
        "donde_corrio": donde_corrio(),
        # RF-30 pide etiquetar por donde corrio DE VERDAD. El transporte es
        # parte de ese «donde»: dos corridas con el mismo veredicto y distinto
        # transporte no dicen lo mismo, y sin este campo la tabla publicada no
        # podria distinguirlas.
        "transporte": args.transporte,
        "etapas": [{"codigo": e.codigo, "nombre": e.nombre,
                    "veredicto": NOMBRE[e.veredicto] if e.emitio else "NO EMITIO",
                    "motivo": e.motivo, "segundos": round(e.segundos, 1),
                    "procesos": e.procesos} for e in etapas],
        "sec6": bloque_sec6(carpeta),
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
