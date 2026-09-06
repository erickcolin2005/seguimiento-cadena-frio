"""Los dos almacenes, y la frontera que los separa.

AL-1 es de SV-1 -- el proceso que muere-- y AL-2 es de SV-2 --el testigo--.
Son dos ficheros distintos, cada uno abierto por un proceso distinto, y **no
existe ninguna conexion, adjuncion ni vista que abra los dos a la vez**
(ADR-18, ADR-25, modelo-datos §2). No es que este prohibido usarla: no existe
el objeto que la haria posible.

Ninguna clave foranea cruza la frontera. Lo unico que une las dos mitades es un
identificador de dominio compartido -- `lote_id`, y dentro de el la terna--,
acordado por el guion y no impuesto por ningun motor.

Dos ausencias deliberadas, y las dos tienen documento detras:

  * `lectura.envio_id` NO tiene restriccion referencial contra `envio`
    (Q-1 respondida NO, especificacion-SEC §5.1). Con ella, la lectura de R-01
    --atribuida a un envio inexistente-- no se podria conservar, y RC-01 dice
    que no evaluarla no es descartarla.
  * `conclusion_lote` publica el umbral y la irreversibilidad de RC-08 como
    **dos columnas**, no una. Un unico `no_apto` haria indistinguible apagar
    una mitad de apagar la otra (banco §8, aviso 1).
"""

import sqlite3
from pathlib import Path

NOMBRE_AL1 = "al1-sv1.sqlite3"
NOMBRE_AL2 = "al2-sv2.sqlite3"

# Las dos listas son el contenido declarado de cada almacen. La comprobacion 7
# las usa como patron: si una tabla de una aparece en el otro fichero, la
# frontera se cruzo.
TABLAS_AL1 = ("corrida", "tipo_producto", "envio", "envio_proyeccion", "lote",
              "lectura", "veredicto_lectura", "excursion", "conclusion_lote",
              "bandeja_salida")
TABLAS_AL2 = ("siembra", "siembra_lote", "lote_custodia", "accion",
              "entrega_repetida")

ESQUEMA_AL1 = """
CREATE TABLE IF NOT EXISTS corrida (
    corrida_id               TEXT PRIMARY KEY,
    semilla                  INTEGER NOT NULL,
    digesto_guion            TEXT NOT NULL,
    instante_arranque_pared  TEXT NOT NULL,
    donde_corrio             TEXT NOT NULL,
    parametros               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tipo_producto (
    tipo_id                  TEXT PRIMARY KEY,
    rango_min_c              REAL,
    rango_max_c              REAL,
    duracion_minima_min      INTEGER NOT NULL,
    duracion_tolerada_min    INTEGER NOT NULL,
    granularidad_muestreo_s  INTEGER NOT NULL,
    retencion_meses          INTEGER NOT NULL,
    -- RF-23 y RT-4: el origen del umbral se declara junto al umbral, y no
    -- admite valor vacio. Un umbral sin origen aqui no se puede escribir.
    origen_umbral            TEXT NOT NULL CHECK (length(origen_umbral) > 0)
);

CREATE TABLE IF NOT EXISTS envio (
    corrida_id               TEXT NOT NULL,
    envio_id                 TEXT NOT NULL,
    secuencia_total_declarada INTEGER,
    estado                   TEXT NOT NULL CHECK (estado IN ('EN_RUTA', 'CERRADO')),
    PRIMARY KEY (corrida_id, envio_id),
    FOREIGN KEY (corrida_id) REFERENCES corrida (corrida_id)
);

CREATE TABLE IF NOT EXISTS envio_proyeccion (
    corrida_id               TEXT NOT NULL,
    envio_id                 TEXT NOT NULL,
    mac                      INTEGER NOT NULL,
    secuencia_sellada_hasta  INTEGER NOT NULL,
    t_d_vigente_min          INTEGER,
    version                  INTEGER NOT NULL,
    PRIMARY KEY (corrida_id, envio_id),
    FOREIGN KEY (corrida_id, envio_id) REFERENCES envio (corrida_id, envio_id)
);

CREATE TABLE IF NOT EXISTS lote (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    envio_id                 TEXT NOT NULL,
    -- ADR-20: el tipo de producto vive en el LOTE. No hay ninguna columna de
    -- envio donde se pueda poner un umbral.
    tipo_id                  TEXT NOT NULL,
    carga_min                INTEGER NOT NULL,
    entrega_min              INTEGER NOT NULL,
    carga_secuencia          INTEGER NOT NULL,
    entrega_secuencia        INTEGER NOT NULL,
    PRIMARY KEY (corrida_id, lote_id),
    FOREIGN KEY (corrida_id, envio_id) REFERENCES envio (corrida_id, envio_id),
    FOREIGN KEY (tipo_id) REFERENCES tipo_producto (tipo_id),
    CHECK (carga_min < entrega_min)
);

-- `envio_id` es a quien la atribuye quien la envia, y puede no existir.
-- NO lleva clave foranea: ver Q-1 arriba.
CREATE TABLE IF NOT EXISTS lectura (
    corrida_id               TEXT NOT NULL,
    envio_id                 TEXT NOT NULL,
    secuencia                INTEGER NOT NULL,
    produccion_min           INTEGER NOT NULL,
    valor_c                  REAL,
    validez                  TEXT NOT NULL,
    emision_pared            TEXT NOT NULL,
    recepcion_pared          TEXT NOT NULL,
    PRIMARY KEY (corrida_id, envio_id, secuencia)
);

CREATE TABLE IF NOT EXISTS veredicto_lectura (
    corrida_id               TEXT NOT NULL,
    envio_id                 TEXT NOT NULL,
    secuencia                INTEGER NOT NULL,
    lote_id                  TEXT NOT NULL,
    evaluada                 INTEGER NOT NULL,
    situacion                TEXT NOT NULL,
    regla_id                 TEXT NOT NULL,
    mensaje_llano            TEXT NOT NULL,
    PRIMARY KEY (corrida_id, envio_id, secuencia, lote_id)
);

CREATE TABLE IF NOT EXISTS excursion (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    secuencia_apertura       INTEGER NOT NULL,
    apertura_min             INTEGER NOT NULL,
    secuencia_cierre         INTEGER,
    cierre_min               INTEGER,
    duracion_min             INTEGER NOT NULL,
    transitoria              INTEGER NOT NULL,
    estado                   TEXT NOT NULL,
    regla_apertura_id        TEXT,
    regla_cierre_id          TEXT,
    sellada                  INTEGER NOT NULL,
    PRIMARY KEY (corrida_id, lote_id, secuencia_apertura),
    FOREIGN KEY (corrida_id, lote_id) REFERENCES lote (corrida_id, lote_id)
);

CREATE TABLE IF NOT EXISTS conclusion_lote (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    aptitud                  TEXT NOT NULL,
    regla_aptitud            TEXT,
    acumulado_min            INTEGER NOT NULL,
    clase_accion             TEXT NOT NULL,
    regla_clase_accion       TEXT,
    marca_secuencia          TEXT NOT NULL,
    provisional              INTEGER NOT NULL,
    t_d_min                  INTEGER,
    umbral_superado          INTEGER NOT NULL,
    irreversible_activa      INTEGER NOT NULL,
    cerrada                  INTEGER NOT NULL,
    PRIMARY KEY (corrida_id, lote_id),
    FOREIGN KEY (corrida_id, lote_id) REFERENCES lote (corrida_id, lote_id)
);

-- La clave primaria ES la terna. La entrada es inmutable salvo su estado, sus
-- intentos y sus dos instantes de pared (ADR-23).
CREATE TABLE IF NOT EXISTS bandeja_salida (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    secuencia_apertura       INTEGER NOT NULL,
    clase                    TEXT NOT NULL CHECK (clase IN ('RESCATE', 'DISPOSICION')),
    t_d_min                  INTEGER NOT NULL,
    regla_id                 TEXT NOT NULL,
    instantanea_conclusion   TEXT NOT NULL,
    sustituye_rescate_imposible INTEGER NOT NULL,
    estado                   TEXT NOT NULL CHECK (estado IN ('PENDIENTE', 'ENTREGADA')),
    intentos                 INTEGER NOT NULL DEFAULT 0,
    commit_pared             TEXT NOT NULL,
    entrega_pared            TEXT,
    PRIMARY KEY (corrida_id, lote_id, secuencia_apertura, clase)
);
"""

ESQUEMA_AL2 = """
CREATE TABLE IF NOT EXISTS siembra (
    corrida_id               TEXT PRIMARY KEY,
    sembrada_pared           TEXT NOT NULL,
    lotes_sembrados          INTEGER NOT NULL
);

-- SV-2 conoce los lotes de la corrida por el guion, no preguntandole a SV-1.
CREATE TABLE IF NOT EXISTS siembra_lote (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    tipo_id                  TEXT NOT NULL,
    PRIMARY KEY (corrida_id, lote_id),
    FOREIGN KEY (corrida_id) REFERENCES siembra (corrida_id)
);

-- Maquina monotona SIN umbrales. SV-2 no reimplementa RC-08 (ADR-27).
CREATE TABLE IF NOT EXISTS lote_custodia (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    estado_custodia          TEXT NOT NULL
        CHECK (estado_custodia IN ('SIN_ACCIONES', 'EN_RESCATE', 'PERDIDO')),
    ultima_instantanea       TEXT,
    instante_ultima_accion_pared TEXT,
    PRIMARY KEY (corrida_id, lote_id),
    FOREIGN KEY (corrida_id, lote_id) REFERENCES siembra_lote (corrida_id, lote_id)
);

-- EL LIBRO. La clave primaria es la terna, y el recuento es contar filas de
-- esta tabla: no hay ninguna columna que cuente (ADR-24).
CREATE TABLE IF NOT EXISTS accion (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    secuencia_apertura       INTEGER NOT NULL,
    clase                    TEXT NOT NULL CHECK (clase IN ('RESCATE', 'DISPOSICION')),
    t_d_min                  INTEGER NOT NULL,
    regla_id                 TEXT NOT NULL,
    instantanea_conclusion   TEXT NOT NULL,
    sustituye_rescate_imposible INTEGER NOT NULL,
    instante_registro_pared  TEXT NOT NULL,
    PRIMARY KEY (corrida_id, lote_id, secuencia_apertura, clase)
);

CREATE TABLE IF NOT EXISTS entrega_repetida (
    corrida_id               TEXT NOT NULL,
    lote_id                  TEXT NOT NULL,
    secuencia_apertura       INTEGER NOT NULL,
    clase                    TEXT NOT NULL,
    veces                    INTEGER NOT NULL,
    PRIMARY KEY (corrida_id, lote_id, secuencia_apertura, clase)
);
"""


def _abrir(ruta, esquema):
    con = sqlite3.connect(str(ruta), isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    # El compromiso llega al sistema operativo antes de acusar. Si es duradero
    # a granularidad de muerte de proceso lo mide VB-1 en PL-3, no aqui.
    con.execute("PRAGMA synchronous = FULL")
    con.executescript(esquema)
    return con


def abrir_al1(ruta):
    """Abre el almacen de SV-1. Solo lo llama SV-1."""
    return _abrir(ruta, ESQUEMA_AL1)


def abrir_al2(ruta):
    """Abre el almacen de SV-2. Solo lo llama SV-2."""
    return _abrir(ruta, ESQUEMA_AL2)


def ruta_al1(directorio):
    return Path(directorio) / NOMBRE_AL1


def ruta_al2(directorio):
    return Path(directorio) / NOMBRE_AL2


# --- Inspeccion, para la comprobacion 7 --------------------------------------

def tablas(con):
    filas = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return tuple(f["name"] for f in filas)


def conteos(con):
    """Filas por tabla. Un almacen vacio da cero en todas."""
    return {t: con.execute("SELECT count(*) AS n FROM %s" % t).fetchone()["n"]
            for t in tablas(con)}


def claves_foraneas(con):
    """Toda referencia declarada del almacen: (tabla, tabla_referida)."""
    salida = []
    for t in tablas(con):
        for fk in con.execute("PRAGMA foreign_key_list(%s)" % t).fetchall():
            salida.append((t, fk["table"]))
    return salida
