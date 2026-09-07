"""La costura del transporte: el sitio por donde se cambia sin tocar nada más.

El diseño afirma que **el transporte no sostiene ninguna garantía**, y que por eso
sustituirlo es sustituir un adaptador y no rediseñar el sistema. Mientras la
llamada estuviera incrustada dentro del drenaje, esa afirmación era una promesa:
no había ningún sitio donde enchufar otro transporte, así que no había forma de
comprobarla.

Este módulo es ese sitio. Un adaptador recibe un hecho actuable ya comprometido y
devuelve el desenlace que el receptor le dio. **Nada más.**

## Lo que un adaptador NO puede hacer, y es la mitad del asunto

  * **No deduplica.** La unidad de «exactamente una vez» es la terna, que es de
    dominio y no de transporte. Si un adaptador dedujera, la garantía viviría en
    él y cambiar de transporte la cambiaría.
  * **No decide si reintentar.** Eso lo decide quien tiene la bandeja, leyendo el
    desenlace.
  * **No ordena nada.** El orden se re-deriva del número de secuencia, y el
    sistema no depende del orden de entrega **ni siquiera cuando el transporte lo
    garantiza**.

Un adaptador que hiciera cualquiera de las tres cosas haría más barato el código
y **más falso el resultado**: la medición estaría comprobando el transporte, no
el sistema.

## Cómo se comprueba que la costura es real

No basta con haberla escrito. La comprobación es que **la medición completa de C1
dé lo mismo con dos adaptadores distintos**: si diera distinto, algo de la
garantía se habría filtrado al transporte.

Hoy hay un solo adaptador de verdad —la llamada directa— y **eso se declara**:
la costura existe y está aislada, pero **la comprobación de que sobrevive al
cambio no está hecha**, porque el segundo transporte no existe todavía. Escribir
aquí que «el transporte es intercambiable» sin haber cambiado ninguno sería
exactamente la clase de afirmación que este proyecto no publica.
"""

import json
import os

from . import protocolo

# Los tres desenlaces que el receptor puede dar. El adaptador los transporta tal
# cual: traducirlos seria decidir por el receptor.
REGISTRADA = "registrada"
YA_REGISTRADA = "ya_registrada"
RECHAZADA = "rechazada_lote_no_sembrado"

# Y un cuarto que NO es del receptor, sino del transporte, y por eso se llama
# distinto. Un productor asincrono no conoce el veredicto del receptor: solo
# sabe que la custodia del mensaje quedo aceptada de forma duradera. Devolver
# `registrada` desde un productor seria inventarse una respuesta que nadie dio
# -- exactamente lo que este modulo prohibe--. La garantia no se mueve por
# esto: si el proceso muere tras el acuse y antes de marcar la entrada, se
# reproduce y el receptor deduplica por la terna. Sigue siendo al-menos-una-vez
# con receptor idempotente, que es lo que el diseño dice que NO cambia.
ENTREGADA_AL_TRANSPORTE = "entregada_al_transporte"

# Donde vive el intermediario y como se llaman los temas. Se leen del entorno
# para que el instrumento pueda apuntar a otro sin tocar codigo.
INTERMEDIARIO = os.environ.get("P1_INTERMEDIARIO", "localhost:19092")
TEMA_LECTURAS = os.environ.get("P1_TEMA_LECTURAS", "p1.lecturas")
TEMA_ACCIONES = os.environ.get("P1_TEMA_ACCIONES", "p1.acciones")

# Mas de una particion a proposito. Con una sola, el orden global se conservaria
# por accidente y el modo de fallo «el orden entre particiones desaparece» no se
# podria ejercer: la medicion saldria verde sin haber corrido el riesgo.
PARTICIONES = 3


class Adaptador:
    """El puerto. Un transporte concreto implementa `entregar` y nada más."""

    nombre = "abstracto"

    def entregar(self, accion):
        """Devuelve (codigo, respuesta). Una excepción significa «no llegó»,
        que **no es lo mismo** que «llegó y fue rechazada»."""
        raise NotImplementedError

    def describir(self):
        return {"transporte": self.nombre}


class LlamadaDirecta(Adaptador):
    """Llamada síncrona al receptor, iniciada por el drenaje de la bandeja.

    Es el transporte con el que se midió C1. No ofrece orden, ni entrega única,
    ni durabilidad — y no se le piden: todo eso vive a los lados.
    """

    nombre = "llamada directa"

    def __init__(self, url_receptor):
        self.url_receptor = url_receptor

    def entregar(self, accion):
        return protocolo.pedir(self.url_receptor, "/acciones", accion)

    def describir(self):
        return {"transporte": self.nombre, "receptor": self.url_receptor}


def asegurar_temas(intermediario=None):
    """Crea los dos temas con sus particiones si no existen. Idempotente.

    Se hace explicito en vez de dejar que el intermediario los cree solo: la
    creacion automatica da UNA particion, y con una sola el orden global se
    conservaria por accidente. La medicion saldria verde sin haber corrido el
    riesgo que dice correr.
    """
    from confluent_kafka.admin import AdminClient, NewTopic

    admin = AdminClient({"bootstrap.servers": intermediario or INTERMEDIARIO})
    existentes = set(admin.list_topics(timeout=20.0).topics)
    faltan = [NewTopic(t, num_partitions=PARTICIONES, replication_factor=1)
              for t in (TEMA_LECTURAS, TEMA_ACCIONES) if t not in existentes]
    if not faltan:
        return
    for tema, futuro in admin.create_topics(faltan).items():
        try:
            futuro.result()
        except Exception as error:                    # noqa: BLE001
            # «Ya existe» es carrera benigna entre dos procesos que arrancan a
            # la vez, no un fallo. Cualquier otra cosa si lo es.
            if "already exists" not in str(error).lower():
                raise RuntimeError("no se pudo crear el tema %s: %s" % (tema, error))


def reiniciar_temas(intermediario=None):
    """Borra los dos temas y los vuelve a crear vacios. Para ANTES de la corrida.

    Cada corrida arranca sobre almacenes vacios, y los temas son parte de ese
    estado: si sobrevivieran de una corrida a la siguiente, la de despues
    ingeriria las lecturas de la de antes y mediria una mezcla de las dos. No
    es hipotetico -- es la primera regla de lectura del banco, «los casos no
    acumulan estado entre si», aplicada al sitio nuevo donde ahora hay estado.
    """
    import time

    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": intermediario or INTERMEDIARIO})
    existentes = [t for t in (TEMA_LECTURAS, TEMA_ACCIONES)
                  if t in admin.list_topics(timeout=20.0).topics]
    if existentes:
        for _, futuro in admin.delete_topics(existentes, operation_timeout=30.0).items():
            futuro.result()
        # El borrado es asincrono en el intermediario: crear inmediatamente
        # despues puede recrear el tema viejo. Se espera a que desaparezca de
        # verdad en vez de suponer que ya no esta.
        limite = time.monotonic() + 30.0
        while time.monotonic() < limite:
            vivos = set(admin.list_topics(timeout=10.0).topics)
            if not (set(existentes) & vivos):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("los temas no terminaron de borrarse: %s"
                               % ", ".join(existentes))
    asegurar_temas(intermediario)


class ProduccionAlTema(Adaptador):
    """Produce la accion al tema, y espera el acuse duradero del intermediario.

    Lo que este adaptador NO hace, y es la mitad del asunto: **no sabe si el
    receptor la registro**. Nadie se lo dice. Por eso devuelve su propio
    desenlace y no uno del receptor.

    `enable.idempotence` evita que un reintento INTERNO del productor duplique
    el mensaje en el tema. No es la garantia del sistema y no se le confunde
    con ella: la de verdad es la terna en el receptor, y sigue siendo la que
    manda si el proceso muere y la entrada se vuelve a drenar.
    """

    nombre = "produccion al tema"

    def __init__(self, url_receptor, intermediario=None):
        from confluent_kafka import Producer

        self.url_receptor = url_receptor
        self.intermediario = intermediario or INTERMEDIARIO
        asegurar_temas(self.intermediario)
        self._productor = Producer({
            "bootstrap.servers": self.intermediario,
            # Acuse de todas las replicas y productor idempotente: sin esto, el
            # «entregada_al_transporte» seria una promesa mas floja que la que
            # el nombre sugiere.
            "acks": "all",
            "enable.idempotence": True,
        })

    def entregar(self, accion):
        estado = {}

        def acuse(error, mensaje):                    # noqa: ARG001
            estado["error"] = error

        # La terna es la clave de particion: todo lo de un mismo hecho actuable
        # cae en la misma particion. El orden NO se delega en eso -- se re-deriva
        # de la secuencia--, pero agrupar por terna evita barajar sin motivo.
        terna = (accion["lote_id"], accion["secuencia_apertura"], accion["clase"])
        self._productor.produce(
            TEMA_ACCIONES,
            key=("%s|%s|%s" % terna).encode("utf-8"),
            value=json.dumps(accion, sort_keys=True).encode("utf-8"),
            callback=acuse)
        sin_entregar = self._productor.flush(20.0)
        if sin_entregar or estado.get("error") is not None:
            # Una excepcion significa «no llego», y el drenaje la cuenta como
            # fallida y deja la entrada PENDIENTE. Que es lo correcto: no llego.
            raise RuntimeError("el intermediario no acuso la accion: %s"
                               % (estado.get("error") or "%d sin entregar"
                                  % sin_entregar))
        return 200, {"desenlace": ENTREGADA_AL_TRANSPORTE, "terna": list(terna)}

    def describir(self):
        return {"transporte": self.nombre, "intermediario": self.intermediario,
                "tema": TEMA_ACCIONES, "particiones": PARTICIONES}


ADAPTADORES = {"directo": LlamadaDirecta, "eventos": ProduccionAlTema}


def construir(clase, url_receptor):
    if clase not in ADAPTADORES:
        raise ValueError("transporte desconocido: %s · hay %s"
                         % (clase, ", ".join(sorted(ADAPTADORES))))
    return ADAPTADORES[clase](url_receptor)


# --- El otro extremo de la costura: por donde LLEGAN las lecturas -------------


class Entrada:
    """El puerto de entrada, que hasta ahora no existía.

    El de arriba es el puerto de **salida**: el drenaje empuja una acción. Este
    es el de **entrada**: alguien trae una lectura y el núcleo la recibe. Son
    dos puertos y no uno porque la dirección es distinta —uno empuja, al otro
    le empujan— y porque el diseño cambia **los dos** adaptadores, no solo el
    de salida.

    ## Por qué este puerto decide si el tramo se puede intentar

    El tramo pide que el instrumento **mate consumidores**. Si solo cambiara el
    puerto de salida, el único consumidor sería el receptor — y el receptor es
    el testigo, al que está prohibido matar porque el recuento no puede vivir
    en el proceso que muere. **Sin puerto de entrada no hay nada matable**, y
    la comprobación que da nombre al tramo no se podría ni intentar.

    ## Por qué hay un `bombear` y no un hilo

    El servidor de este proyecto es **de un solo hilo a propósito**, y de ahí
    depende que el camino sea reproducible y que el control optimista por
    versión quede declarado *sin ejercitar*. Meter el consumidor en un hilo
    aparte despertaría una concurrencia real dentro del servicio —dos hilos
    sobre el mismo almacén— que esta medición no modela, y las carreras que
    aparecieran se leerían como fallos del sistema cuando serían del
    instrumento. Por eso el consumidor **se bombea desde el mismo bucle** que
    atiende las peticiones.
    """

    nombre = "abstracto"

    # Si la ingesta NO va por HTTP, la ruta de lecturas se cierra. Dejarla
    # abierta permitiria que una lectura entrara por el camino viejo durante
    # una medicion que dice ser sobre otro transporte: la medicion afirmaria
    # una cosa mientras el sistema hace otra, que es el defecto de la pieza que
    # se cree mutada y no lo esta.
    admite_http = False

    # Si es cierto, el bucle principal tiene que llamar a `bombear`. La entrada
    # por HTTP no lo necesita, y por eso su camino -- el que ya se midio -- se
    # queda exactamente como estaba.
    necesita_bombeo = False

    def arrancar(self, recibir):
        """Empieza a traer lecturas. `recibir(cuerpo)` devuelve (codigo, dict)."""
        raise NotImplementedError

    def bombear(self):
        """Trae como mucho una entrada y la entrega. Devuelve cuantas trajo."""
        return 0

    def parar(self):
        raise NotImplementedError

    def describir(self):
        return {"entrada": self.nombre}


class EntradaHTTP(Entrada):
    """Las lecturas entran por la ruta que el servicio ya atiende.

    No arranca nada, y eso es correcto: el servidor existe de todos modos para
    las rutas de control, así que esta entrada **solo declara que la ruta de
    lecturas está abierta**. Es la entrada con la que se midió C1.
    """

    nombre = "http"
    admite_http = True

    def __init__(self, tema=None, grupo=None, intermediario=None):
        # Los acepta y los ignora: el constructor es comun para que quien
        # construye no tenga que saber que entrada le va a tocar.
        pass

    def arrancar(self, recibir):
        return None

    def parar(self):
        return None


class EntradaEventos(Entrada):
    """Las lecturas llegan consumiendo un tema, y por eso hay algo que matar.

    Dos decisiones que no son de estilo, y que son justo lo que el tramo mide:

      * **El acuse del avance se confirma DESPUÉS del compromiso local**, nunca
        antes, y nunca automáticamente. Al revés —confirmar y luego morir—
        perdería la entrada para siempre. En este orden, morir en medio produce
        un reconsumo, y reconsumir **no crea nada** porque la ingesta es
        idempotente por `(envio, secuencia)`. Ese es el desacople clásico entre
        el avance del consumidor y el compromiso local, y se absorbe con una
        clave que ya existía.
      * **La confirmación es síncrona.** Una asíncrona volvería a abrir el
        hueco que se acaba de cerrar.
    """

    nombre = "eventos"
    admite_http = False
    necesita_bombeo = True

    def __init__(self, tema=None, grupo=None, intermediario=None):
        if not tema or not grupo:
            raise ValueError("la entrada por eventos necesita tema y grupo")
        self.tema = tema
        self.grupo = grupo
        self.intermediario = intermediario or INTERMEDIARIO
        self._consumidor = None
        self._recibir = None

    def arrancar(self, recibir):
        from confluent_kafka import Consumer

        asegurar_temas(self.intermediario)
        self._recibir = recibir
        self._consumidor = Consumer({
            "bootstrap.servers": self.intermediario,
            "group.id": self.grupo,
            # Desde el principio del tema: un consumidor que revive despues de
            # morir tiene que volver a ver lo que no llego a confirmar.
            "auto.offset.reset": "earliest",
            # NUNCA automatico. El avance lo confirma este codigo, y solo
            # despues de que el compromiso local exista.
            "enable.auto.commit": False,
        })
        self._consumidor.subscribe([self.tema])

    # Cuantas lecturas se traen de una vez. Con una por vuelta, cada mensaje
    # pagaba ademas la espera del servidor y una confirmacion de avance propia,
    # y a tamaño real la ingesta no terminaba a tiempo. No es una optimizacion
    # cosmetica: sin esto la corrida no se completa.
    POR_TANDA = 100

    def bombear(self):
        if self._consumidor is None:
            return 0
        mensajes = [m for m in self._consumidor.consume(self.POR_TANDA, 0.02)
                    if m is not None and not m.error()]
        if not mensajes:
            return 0
        for mensaje in mensajes:
            self._recibir(json.loads(mensaje.value().decode("utf-8")))
        # Y AHORA, una sola vez para toda la tanda. Confirmar el avance MAS
        # TARDE de lo estrictamente necesario siempre es seguro; lo que nunca
        # puede hacerse es confirmarlo ANTES del compromiso local. Al hacerlo
        # por tandas, una muerte reconsume mas lecturas -- y reconsumir no crea
        # nada, porque la ingesta es idempotente por (envio, secuencia)--. Esto
        # ENSANCHA el desacople entre el avance y el compromiso local en vez de
        # estrecharlo: pone a prueba mas ese modo de fallo, no menos.
        self._consumidor.commit(asynchronous=False)
        return len(mensajes)

    def parar(self):
        if self._consumidor is not None:
            self._consumidor.close()
            self._consumidor = None

    def describir(self):
        return {"entrada": self.nombre, "intermediario": self.intermediario,
                "tema": self.tema, "grupo": self.grupo}


ENTRADAS = {"http": EntradaHTTP, "eventos": EntradaEventos}


def construir_entrada(clase, tema=None, grupo=None):
    if clase not in ENTRADAS:
        raise ValueError("entrada desconocida: %s · hay %s"
                         % (clase, ", ".join(sorted(ENTRADAS))))
    return ENTRADAS[clase](tema=tema, grupo=grupo)


# --- El emisor: por donde el INSTRUMENTO manda lecturas -----------------------


class EmisorLecturas:
    """El otro extremo del puerto de entrada, y vive en el instrumento.

    Existe por simetria obligada: si la ingesta consume de un tema, quien emite
    tiene que producir a ese tema. Que este en este modulo y no en el
    instrumento es deliberado: asi los dos extremos se cambian a la vez y no
    puede quedar uno emitiendo por un camino que el otro ya no escucha.

    **Un emisor por eventos no devuelve el veredicto de la ingesta**, porque no
    lo tiene. Quien lo llame no puede seguir suponiendo que al volver de
    `enviar` la lectura ya esta ingerida: tiene que esperarlo, y para eso esta
    `esperar_ingesta`.
    """

    nombre = "abstracto"
    entrega_veredicto = True

    def enviar(self, lectura):
        raise NotImplementedError

    def cerrar(self):
        return None

    def describir(self):
        return {"emisor": self.nombre}


class EmisorHTTP(EmisorLecturas):
    """Manda la lectura y espera. Es el emisor con el que se midio C1."""

    nombre = "http"
    entrega_veredicto = True

    def __init__(self, url_sv1, intermediario=None):
        self.url_sv1 = url_sv1

    def enviar(self, lectura):
        return protocolo.pedir(self.url_sv1, "/lecturas", lectura)

    def describir(self):
        return {"emisor": self.nombre, "destino": self.url_sv1}


class EmisorEventos(EmisorLecturas):
    """Produce la lectura al tema. No espera a que nadie la ingiera.

    La clave de particion es el `envio_id`: todo lo de un mismo envio cae en la
    misma particion. El orden **no** se delega en eso -- se re-deriva de la
    secuencia--, y esa es justamente la afirmacion que el desorden entre
    particiones pone a prueba.
    """

    nombre = "eventos"
    entrega_veredicto = False

    def __init__(self, url_sv1, intermediario=None):
        from confluent_kafka import Producer

        self.url_sv1 = url_sv1
        self.intermediario = intermediario or INTERMEDIARIO
        asegurar_temas(self.intermediario)
        self._productor = Producer({"bootstrap.servers": self.intermediario,
                                    "acks": "all", "enable.idempotence": True})

    def enviar(self, lectura):
        self._productor.produce(
            TEMA_LECTURAS,
            key=str(lectura["envio_id"]).encode("utf-8"),
            value=json.dumps(lectura, sort_keys=True).encode("utf-8"))
        self._productor.poll(0)
        # 202 y no 200: se acepto para transporte, y NADIE ha dicho todavia que
        # este ingerida. Devolver 200 aqui seria afirmar lo que no consta.
        return 202, {"desenlace": "encolada_en_el_tema"}

    def cerrar(self):
        sin_entregar = self._productor.flush(30.0)
        if sin_entregar:
            raise RuntimeError("%d lecturas sin acuse del intermediario"
                               % sin_entregar)

    def describir(self):
        return {"emisor": self.nombre, "intermediario": self.intermediario,
                "tema": TEMA_LECTURAS, "particiones": PARTICIONES}


EMISORES = {"http": EmisorHTTP, "eventos": EmisorEventos}


def construir_emisor(clase, url_sv1):
    if clase not in EMISORES:
        raise ValueError("emisor desconocido: %s · hay %s"
                         % (clase, ", ".join(sorted(EMISORES))))
    return EMISORES[clase](url_sv1)


def frase_de_alcance(clase):
    """La linea que dice SOBRE QUE se midio. Derivada del transporte real.

    Escrita a mano, esta linea sobrevive al cambio que la vuelve falsa: la
    primera corrida completa sobre el transporte por eventos seguia imprimiendo
    «Medido sobre un mecanismo directo», que es exactamente lo contrario de lo
    que acababa de hacer. Un artefacto que publica la leyenda en vez del hecho
    medido es el defecto que este proyecto persigue -- y aparecio dentro del
    propio instrumento, que es donde mas caro sale.

    Se deriva, y por eso no puede quedarse vieja.
    """
    if clase == "eventos":
        return ("Medido sobre un transporte por eventos, con consumidores "
                "muertos a proposito. NO sobre ningun otro.")
    return "Medido sobre un mecanismo directo. NO sobre ningun otro."


def techo_de_espera(esperadas):
    """Cuanto se le da a la ingesta antes de declarar que no llego.

    Un tope FIJO no es un tope: es un limite de tamaño disfrazado. Con 90 s
    constantes, una corrida de 1441 lecturas se declaraba invalida por ser
    grande, no por estar atascada -- y eso ya paso una vez, con la tanda del
    primer mutante quedandose en 1284 de 1441--. El tope crece con el trabajo
    para que lo que mida siga siendo «esto no avanza» y no «esto es largo».

    Sigue siendo un tope, y sigue haciendo falta: sin el, una ingesta parada
    colgaria la corrida en vez de declararla invalida.
    """
    return max(90.0, 0.25 * esperadas)


def esperar_ingesta(url_sv1, esperadas, tiempo=None, pausa=0.05):
    """Espera a que el nucleo tenga ingeridas `esperadas` lecturas.

    Con el emisor sincrono esto sobra —al volver de `enviar` ya estaba—, pero
    con uno asincrono es obligatorio: preguntar por las conclusiones antes de
    que la ingesta haya terminado mediria un prefijo, no la corrida.

    Devuelve (llego, cuantas). Que devuelva False NO es un fallo del sistema y
    quien llama no debe publicarlo como tal: es que el instrumento no pudo
    completar la corrida, y eso se declara MEDICION INVALIDA.
    """
    import time

    limite = time.monotonic() + (tiempo if tiempo is not None
                                 else techo_de_espera(esperadas))
    cuantas = -1
    while time.monotonic() < limite:
        codigo, cuerpo = protocolo.pedir(url_sv1, "/salud", tiempo=5.0)
        if codigo == 200:
            cuantas = cuerpo.get("lecturas_ingeridas", -1)
            if cuantas >= esperadas:
                return True, cuantas
        time.sleep(pausa)
    return False, cuantas
