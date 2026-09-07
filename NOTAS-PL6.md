# Notas de PL-6 · el tramo que compra el eje, y lo que costó

Marcas: `[M]` medido ejecutando · `[V]` verificado · `[A]` asumido · `[NV]` no
verificado.

> **Este documento decía, hasta esta corrida, «PL-6 no está terminado, y este
> documento existe para decirlo con precisión». Ahora está terminado, y el
> documento existe para decir con la misma precisión qué se midió y qué no.**

---

## 1 · Las cinco comprobaciones

| # | Qué pedía | Estado |
|---|---|---|
| **1** | El transporte por eventos sustituye la llamada directa, y el instrumento mata consumidores | ✅ **HECHA** · §2 |
| **2** | C1-A y C1-B se vuelven a medir sobre el nuevo transporte, con sus tres modos de fallo | ✅ **HECHA** · §3 |
| **3** | CE-4 registrada: si el costo de la plomería coincidió con lo declarado | ✅ **HECHA** · `evidencia/pl-6/ce4-costo-de-la-plomeria.md` |
| **4** | CE-3 aplicada: toda limpieza de disco comparada contra el inventario | ✅ **HECHA** · `evidencia/pl-6/inventario-ce3.txt` · **ninguna limpieza ejecutada** |
| **5** | **Solo aquí se levanta CE-5** | ✅ **LEVANTADA, y sustituida** · §5 |

**Cinco de cinco.**

## 2 · Por qué hicieron falta DOS puertos y no uno

El diseño decía que en M11 cambian **dos** adaptadores. Solo existía costura en
el de salida: la ingesta atendía su ruta a pelo, sin puerto.

Y eso no era un detalle de simetría. **Sin puerto de entrada no hay ningún
consumidor matable**, porque el único que quedaría es el receptor — y el
receptor es el testigo, al que está prohibido matar porque el recuento no puede
vivir en el proceso que muere. La comprobación que da nombre al tramo no se
habría podido ni intentar.

Con los dos puertos, quien muere 56 veces por corrida **es** un consumidor.

### Una decisión asimétrica, y su razón

Con la entrada por eventos, **la ruta HTTP de lecturas se cierra** (devuelve
409) `[M]`. Si siguiera abierta, una lectura podría entrar por el camino viejo
durante una corrida que dice medir sobre el otro transporte: la medición
afirmaría una cosa mientras el sistema hace otra. Es el defecto de la pieza que
se cree mutada y no lo está, que este proyecto ya se comió una vez.

**En el receptor NO se cierra la ruta equivalente, a propósito.** Allí una mala
configuración no produce una medición silenciosamente falsa: produce un
recuento en cero, que es un fallo a gritos. Y cerrarla rompería las sondas que
comprueban el vocabulario del receptor posteando directo.

### Un desenlace nuevo, porque el productor no sabe lo que no sabe

Un productor asíncrono **no conoce el veredicto del receptor**. Devolver
`registrada` desde él habría sido inventarse una respuesta que nadie dio —
justo lo que el módulo del transporte se prohíbe—. Hay un cuarto desenlace,
`entregada_al_transporte`, que informa de un hecho distinto: **custodia duradera
aceptada**.

La garantía no se mueve por eso: si el proceso muere tras el acuse y antes de
marcar la entrada, se reproduce y el receptor deduplica por la terna. Sigue
siendo al-menos-una-vez con receptor idempotente.

## 3 · Lo medido, con sus dos columnas

Las dos corridas son **del mismo código y de la misma máquina** `[M]`:

| | directo | eventos |
|---|---|---|
| C1-A · divergencias | 0 | **0** |
| divergencias con la versión rota | 18 | **18** |
| C1-B · hechos actuables · muertes | 56 · 56 | **56 · 56** |
| hechos con 0 · con ≥2 acciones | 0 · 0 | **0 · 0** |
| entregas repetidas absorbidas | 28 | **28** |
| anomalías M-1 / M-2 | 28 / 28 | **28 / 28** |
| Cinturón | **APROBADO · 0** · 221,3 s | **APROBADO · 0** · 408,6 s |

**Que coincidan es el resultado.** Si la garantía hubiera vivido en el
transporte, cambiarlo la habría cambiado.

Los tres modos de fallo que el cambio añade ocurrieron y los absorbió una clave
que ya existía. El del orden se puede ver en el reparto: las lecturas cayeron
**26 / 50 / 24** entre tres particiones `[M]`. Con una sola partición el orden
global se habría conservado por accidente y ese modo no se habría ejercido —
verde sin haber corrido el riesgo.

## 4 · Los dos defectos, y los dos eran del instrumento

| # | Qué | Por qué importa |
|---|---|---|
| 1 | El bombeo traía las lecturas **de una en una**, con una confirmación de avance por cada una. A tamaño real no terminaba dentro del tope y la corrida salía **INVÁLIDA** | El tope era **fijo**, así que no era un tope: era un límite de tamaño disfrazado. Declaraba inválida una corrida por ser grande, no por estar atascada |
| 2 | La salida imprimía **«Medido sobre un mecanismo directo»** mientras corría sobre el otro transporte | Un artefacto **publicando la leyenda en vez del hecho medido** — y justo la leyenda que una condición del proyecto impone. Estaba escrita a mano y sobrevivió intacta al cambio que la volvió falsa |

Los dos se arreglaron **quitando la excepción, no añadiéndola**: el tope ahora
crece con el trabajo, y la frase de alcance **se deriva** del transporte real.

**Y un tercero que no es del instrumento sino de mi predicción**, registrado en
el inventario: escribí que el intermediario no añadiría volúmenes porque no le
puse ninguno nombrado. Salieron **tres**, anónimos, creados por la propia
imagen. «Sin volumen nombrado» no es «sin volumen», y un volumen anónimo es
**más** difícil de atribuir, no menos. Se dejó escrito el error en vez de
corregir el texto: una predicción refutada por la medición es exactamente lo
que CE-3 existe para producir.

## 5 · CE-5 no se borró: cambió de objeto

Levantar una regla y no poner nada en su sitio habría sido cambiarla por un
hueco. Lo que hay ahora, y corre en cada push `[M]`:

- **`arquitectura distribuida` y `sistema por eventos`** — las compra M11, y se
  permiten **solo si la evidencia que las respalda está publicada y en verde**:
  una corrida sobre el transporte por eventos con veredicto APROBADO, y el
  comando que la reproduce publicado en el README. Sin eso, el push se pone
  rojo por *afirmar de más*.
- **La tercera expresión que el cinturón vigilaba** — la que habla de aguantar
  fallos en general — **sigue prohibida, y no se escribe aquí ni siquiera para
  explicarla.** El tramo autoriza hablar de la arquitectura y de los eventos; no
  autoriza esa. Lo medido es la muerte del **proceso** dentro de una ventana, en
  una máquina, y eso no es aguantar fallos en general. Su forma literal vive en
  `cinturon.py`, que es el único sitio donde tiene efecto.

La lista de artefactos revisados **se sigue derivando**, no escribiendo a mano.

### El guardián nuevo se estrenó cazándome a mí

La primera corrida con esta regla salió **FALLO**, y la culpable era esta misma
sección: escribí la expresión prohibida **para explicar que estaba prohibida**,
y el patrón literal se autoacusó.

**Es la cuarta vez que pasa exactamente esto en este proyecto** — antes fue un
patrón de tipos, un raspado de una palabra, y los patrones de anulación de
veredicto. Y se arregló como las otras tres: **quitando la excepción, no
añadiéndola.** No se excluyó este fichero de la revisión —eso habría creado un
sitio donde la regla no mira, que es peor que el problema— sino que se dejó de
escribir la frase.

Que la regla nueva fallara en su primera corrida, y por una razón real, es la
única evidencia disponible de que **mira**.

## 6 · Lo que este tramo NO compró

- **Un nodo, una máquina, tres particiones.** Sin partición de red, sin varias
  máquinas, sin relojes que discrepen `[NV]`.
- **Sin carga y sin concurrencia externa.** El servidor sigue siendo de un solo
  hilo a propósito, y el consumidor **se bombea desde el mismo bucle** en vez de
  desde un hilo aparte: con dos hilos sobre el mismo almacén el camino dejaría
  de ser reproducible y las carreras se leerían como fallos del sistema siendo
  del instrumento. El control optimista por versión **sigue sin ejercitarse**.
- **Que corra orquestado.** No se afirma y no se ha medido.
- **Las siete comprobaciones de los dos servicios** siguen corriendo **solo
  sobre el transporte directo**: no están en los cinco criterios de este tramo,
  y se declara en vez de dejar que parezca cubierto.
- **Memoria y minutos de CPU**, que siguen sin medirse.
