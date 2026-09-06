"""Levanta el sistema entero con un comando.

    python levantar.py

Sin instalar nada, sin imagen, sin credencial y sin red externa. Crea los dos
almacenes vacios y arranca SV-2 y SV-1 en puertos que el sistema operativo
declara libres.

**El arranque de un solo comando no puede depender de Docker Compose**
(arquitectura §10.4 y §11.2): Compose, si algun dia existe, es una SEGUNDA forma
de levantar lo mismo, y llega al final. Aqui no se le pide nada a ningun demonio:
son cuatro procesos y dos ficheros.

El orden importa y no es casual: **SV-2 primero**. El testigo tiene que estar en
pie antes de que exista nada que atestiguar; al reves, SV-1 podria decidir un
hecho actuable sin que hubiera nadie a quien contarselo, y la bandeja de salida
existe justamente para que eso no se pierda -- pero probarlo es PL-3, no esto.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from sistema import almacen, guion as modulo_guion, protocolo

RAIZ = Path(__file__).resolve().parent
SEMILLA_POR_DEFECTO = 20260906


class Orquesta:
    """Los dos servicios, sus dos almacenes y su ciclo de vida.

    Se puede usar como contexto. `comprobar.py` la usa para poder **matar SV-1 y
    seguir preguntandole a SV-2**, que es la comprobacion 4 y la razon de ser de
    la separacion.
    """

    def __init__(self, directorio, semilla=SEMILLA_POR_DEFECTO, corrida=None,
                 silencioso=False, repeticiones=1, sin_orden=False,
                 marca_antes=False, receptor_no_idempotente=False):
        self.directorio = Path(directorio)
        self.semilla = semilla
        self.repeticiones = repeticiones
        # Mutante de C1-A: SV-1 arranca sin reconstruir el orden. Solo lo usa la
        # calibracion, para ver a la medicion ponerse roja.
        self.sin_orden = sin_orden
        # Los dos mutantes de C1-B. Uno pierde acciones, el otro las duplica.
        # Hacen falta los dos: con uno solo, la calibracion demostraria una mitad.
        self.marca_antes = marca_antes
        self.receptor_no_idempotente = receptor_no_idempotente
        self.guion = modulo_guion.generar(semilla, repeticiones)
        self.digesto = modulo_guion.digesto(self.guion)
        self.corrida_id = corrida or ("CO-%s-%d" % (self.guion["etiqueta"], semilla))
        self.silencioso = silencioso
        self.puerto_sv1 = None
        self.puerto_sv2 = None
        self.proceso_sv1 = None
        self.proceso_sv2 = None

    # --- ciclo de vida -------------------------------------------------------

    def _decir(self, texto):
        if not self.silencioso:
            print(texto, flush=True)

    def crear_almacenes(self):
        """Los dos ficheros, vacios. Devuelve el conteo de filas de cada uno."""
        self.directorio.mkdir(parents=True, exist_ok=True)
        con1 = almacen.abrir_al1(almacen.ruta_al1(self.directorio))
        # El esquema del receptor tiene que crearse ya mutado si la corrida es
        # una calibracion. Crearlo normal aqui y dejar que SV-2 lo «mute» despues
        # no muta nada: `CREATE TABLE IF NOT EXISTS` no toca una tabla que ya
        # existe, y el mutante se quedaria con la clave primaria de la terna
        # puesta -- es decir, sin mutar y en silencio--.
        con2 = almacen.abrir_al2(almacen.ruta_al2(self.directorio),
                                 idempotente=not self.receptor_no_idempotente)
        try:
            return {"AL-1": almacen.conteos(con1), "AL-2": almacen.conteos(con2)}
        finally:
            con1.close()
            con2.close()

    def _lanzar(self, modulo, argumentos):
        return subprocess.Popen(
            [sys.executable, "-m", modulo] + argumentos,
            cwd=str(RAIZ), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True)

    def arrancar(self):
        self.puerto_sv2 = protocolo.puerto_libre()
        self.proceso_sv2 = self._lanzar("sistema.sv2", [
            "--puerto", str(self.puerto_sv2), "--directorio", str(self.directorio)]
            + (["--receptor-no-idempotente"] if self.receptor_no_idempotente else []))
        if protocolo.esperar_vivo(self.url_sv2) is None:
            raise RuntimeError("SV-2 no respondio a /salud: %s" % self._diagnostico(
                self.proceso_sv2))

        self.arrancar_sv1()
        return self

    def arrancar_sv1(self):
        """Arranca (o vuelve a arrancar) SV-1 sobre el mismo almacen.

        C1-B lo llama despues de cada muerte. El proceso es nuevo; lo que
        encuentra al abrir es lo que quedo comprometido, y nada mas.
        """
        self.puerto_sv1 = protocolo.puerto_libre()
        self.proceso_sv1 = self._lanzar("sistema.sv1", [
            "--puerto", str(self.puerto_sv1), "--directorio", str(self.directorio),
            "--semilla", str(self.semilla), "--digesto", self.digesto,
            "--corrida", self.corrida_id, "--sv2", self.url_sv2,
            "--repeticiones", str(self.repeticiones)]
            + (["--sin-reconstruccion-de-orden"] if self.sin_orden else [])
            + (["--marca-antes-de-enviar"] if self.marca_antes else []))
        if protocolo.esperar_vivo(self.url_sv1) is None:
            raise RuntimeError("SV-1 no respondio a /salud: %s" % self._diagnostico(
                self.proceso_sv1))
        return self.proceso_sv1

    def _diagnostico(self, proceso):
        if proceso.poll() is None:
            return "sigue vivo pero no contesta"
        return (proceso.stderr.read() or proceso.stdout.read() or "sin salida")[-400:]

    def detener_sv1(self):
        """Mata SV-1 y espera a que el puerto quede realmente libre.

        Es la mitad de la comprobacion 4: despues de esto, SV-2 tiene que seguir
        contestando el recuento. `terminate` y no `kill` porque en Windows la
        diferencia no es la que uno espera y aqui basta con que se vaya.
        """
        if self.proceso_sv1 is None:
            return False
        self.proceso_sv1.terminate()
        try:
            self.proceso_sv1.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proceso_sv1.kill()
            self.proceso_sv1.wait(timeout=10)
        for _ in range(100):
            if not protocolo.puerto_ocupado(self.puerto_sv1):
                return True
            time.sleep(0.05)
        return False

    def parar(self):
        for proceso in (self.proceso_sv1, self.proceso_sv2):
            if proceso is None or proceso.poll() is not None:
                continue
            proceso.terminate()
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proceso.kill()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.parar()
        return False

    # --- accesos -------------------------------------------------------------

    @property
    def url_sv1(self):
        return protocolo.base(self.puerto_sv1)

    @property
    def url_sv2(self):
        return protocolo.base(self.puerto_sv2)

    def sembrar_sv2(self):
        lotes = [{"lote_id": l["lote_id"], "tipo_id": l["tipo_id"]}
                 for _, l in modulo_guion.lotes(self.guion)]
        return protocolo.pedir(self.url_sv2, "/siembra",
                               {"corrida_id": self.corrida_id, "lotes": lotes})

    def emitir(self):
        """EM · emite las lecturas del guion a SV-1, en orden de produccion."""
        enviadas, respuestas = 0, []
        for envio in self.guion["envios"]:
            for lectura in sorted(envio["lecturas"], key=lambda l: l["produccion_min"]):
                codigo, cuerpo = protocolo.pedir(self.url_sv1, "/lecturas", {
                    "corrida_id": self.corrida_id,
                    "envio_id": envio["envio_id"],
                    "secuencia": lectura["secuencia"],
                    "produccion_min": lectura["produccion_min"],
                    "valor_c": lectura["valor_c"]})
                enviadas += 1
                respuestas.append((codigo, cuerpo))
        return enviadas, respuestas


def main(argv=None):
    partes = argparse.ArgumentParser(
        description="Levanta SV-2 y SV-1 con los almacenes vacios. Un comando.")
    partes.add_argument("--directorio", default=str(RAIZ / "corrida"),
                        help="donde viven los dos ficheros de almacen")
    partes.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    partes.add_argument("--limpio", action="store_true",
                        help="borra el directorio de corrida antes de empezar")
    partes.add_argument("--y-salir", action="store_true",
                        help="arranca, informa y para; no se queda esperando")
    args = partes.parse_args(argv)

    directorio = Path(args.directorio)
    if args.limpio and directorio.exists():
        shutil.rmtree(directorio)

    print("=" * 78)
    print("LEVANTAR · dos servicios, dos almacenes, un comando")
    print("=" * 78)
    print("Python %s · solo biblioteca estandar · sin imagen, sin demonio, "
          "sin credencial" % sys.version.split()[0])
    print("docker en el PATH: %s  (no se usa: el arranque no depende de el)"
          % ("si" if shutil.which("docker") else "no"))

    orquesta = Orquesta(directorio, args.semilla)
    conteos = orquesta.crear_almacenes()
    vacios = all(n == 0 for a in conteos.values() for n in a.values())
    print()
    print("directorio de corrida: %s" % directorio)
    print("  %s · %d tablas" % (almacen.NOMBRE_AL1, len(conteos["AL-1"])))
    print("  %s · %d tablas" % (almacen.NOMBRE_AL2, len(conteos["AL-2"])))
    print("  los dos almacenes recien creados estan vacios: %s"
          % ("si" if vacios else "NO"))
    print()
    print("corrida: %s" % orquesta.corrida_id)
    print("semilla: %d" % orquesta.semilla)
    print("digesto del guion: %s" % orquesta.digesto)

    try:
        orquesta.arrancar()
    except RuntimeError as error:
        print()
        print("NO SE PUDO LEVANTAR: %s" % error)
        orquesta.parar()
        return 1

    print()
    print("SV-2 (testigo) ....... %s" % orquesta.url_sv2)
    print("SV-1 (reglas) ........ %s" % orquesta.url_sv1)
    print()
    print("  curl %s/salud" % orquesta.url_sv2)
    print("  curl \"%s/recuentos?corrida_id=%s\"" % (orquesta.url_sv2,
                                                     orquesta.corrida_id))
    print()
    print("Para ejercer las siete comprobaciones de PL-2:  python comprobar.py")

    if args.y_salir:
        orquesta.parar()
        print()
        print("Los dos servicios respondieron y se han parado (--y-salir).")
        return 0

    print()
    print("Ctrl-C para parar los dos.")
    try:
        while True:
            time.sleep(0.5)
            if orquesta.proceso_sv1.poll() is not None:
                print("SV-1 se ha ido.")
                break
            if orquesta.proceso_sv2.poll() is not None:
                print("SV-2 se ha ido.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        orquesta.parar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
