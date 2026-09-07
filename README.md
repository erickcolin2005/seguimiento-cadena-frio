# Cadena de frío en transporte · P1

> **Estado: la afirmación de §2 está medida, sobre DOS transportes distintos.** Hay
> un **banco de reglas de cadena de frío que se ejecuta** — 64 casos, trece piezas
> apagables— y hoy su corrida termina en **VERDE**.
>
> Y hay **dos servicios separados que hablan**, cada uno con su almacén, cuyas
> siete comprobaciones también pasan (§4c).
>
> Y sobre eso se midió §2: **cero divergencias de orden** sobre 440 inversiones
> que sí cambiaban la conclusión, y **exactamente una acción en 56 de 56 hechos**,
> con 56 muertes de proceso provocadas entre decidir y registrar (§4d).
>
> **Y después se volvió a medir entera sobre otro transporte** —una arquitectura
> distribuida, con los servicios hablando por un intermediario de eventos y
> **consumidores muertos a propósito**— y **dio lo mismo, campo a campo**. Eso es
> lo que dice que la garantía no vivía en el transporte: si viviera ahí,
> cambiarlo la habría cambiado.
>
> **Sobre qué se midió esa segunda vez, y sin lo cual la frase de arriba afirma
> de más:** un nodo del intermediario, en una máquina, tres particiones, 168
> muertes de proceso por corrida. **Sin partición de red, sin carga, sin
> concurrencia externa y sin varias máquinas.** La afirmación fuerte y su
> denominador van pegados, igual que las 440 inversiones decisivas van pegadas a
> las 1248 observadas.
>
> Lo que sigue sin existir: **nadie externo ha leído esto**, no hay carga, no hay
> nada que un transportista pueda usar, y los valores del dominio siguen siendo
> valores de trabajo que el negocio no ha validado.
>
> **El verde llegó tarde y a propósito.** Durante un tramo la corrida terminó en
> **INVÁLIDO** —ni verde ni rojo— porque una de las condiciones no se podía
> evaluar con los datos que había. No se relajó la condición: se declaró el dato
> que faltaba. La historia está en §4b, y es lo más parecido a una prueba de que
> este instrumento sabe negarse.

En los documentos internos el proyecto figura con el nombre «logística en tiempo
real con cadena de frío». Aquí no se usa ese nombre: la inmediatez es una decisión
justificada por el plazo físico de una desviación de temperatura `[A]`, no una
propiedad de nada que exista.

---

## 1 · El problema

Lo que se transporta refrigerado o congelado tiene una temperatura que no puede
salirse de un rango, y salirse tiene consecuencias que no se deshacen. **Un pedido
que llega tarde se entrega tarde; un lote que rompió la cadena de frío no se
recupera: se pierde** `[V — entendimiento §3]`.

Tres hechos del negocio hacen que esto no sea «poner un termómetro»:

1. **No toda desviación cuenta.** Una lectura fuera de rango durante unos minutos
   no es lo mismo que una desviación sostenida. Hay que decidir **a partir de
   cuánto tiempo una desviación abre una excursión** — y esa frontera es una
   decisión de negocio, no un dato de la naturaleza.
2. **La consecuencia se acumula y llega un punto en que es irreversible.** Las
   desviaciones de un lote suman; pasado el límite tolerado, el lote queda **no
   apto**, y ninguna lectura posterior lo rehabilita.
3. **Actuar tiene plazo.** Una excursión detectada a tiempo se puede rescatar; la
   misma excursión conocida demasiado tarde solo se puede documentar. **Enterarse
   tarde y enterarse mal no producen el mismo daño, pero los dos producen daño.**

Sobre el registro existe además una obligación: la normativa sanitaria colombiana
exige que el medio de transporte cuente con indicadores y sistemas de registro
—Resolución 2674 de 2013, Art. 29 num. 3, y el verbo es «deben» `[V — marco
normativo]`—. **Lo que la norma NO fija es una temperatura numérica de
refrigeración para el transporte** `[V]`: las cifras que este proyecto usa se
toman prestadas de artículos que regulan manipulación y esperas entre etapas, y
eso se declara aquí en vez de disimularse. La lectura completa de ese marco
**todavía no está firmada por el rol de cumplimiento** `[NV]`.

---

## 2 · La afirmación que este proyecto se propone medir

Esta es la afirmación, escrita entera y en presente porque así es como se
intentó romper. **Está medida en §4d, y sobre los dos transportes de §4d-2**;
sobre cualquier tercero sigue siendo solo una frase:

> **El orden de los eventos de un mismo envío se respeta siempre; y una excursión
> se actúa exactamente una vez, incluso si el proceso muere entre decidir y
> registrar.**

Dicha en palabras llanas, son dos mitades, y **fallar cualquiera es fallar**:

- **Orden.** Si las lecturas de un mismo envío se procesan en un orden distinto
  del que ocurrieron, «subió» seguido de «bajó» leído al revés da **la conclusión
  contraria sobre si el lote se perdió**. La mitad de orden dice que eso no pasa.
- **Exactamente una vez.** Entre el momento en que se decide actuar sobre una
  excursión y el momento en que queda constancia de haberlo hecho hay un hueco. Si
  algo se interrumpe justo ahí, nadie sabe si se actuó. La mitad de cardinalidad
  dice que cada excursión que merece acción recibe **una, ni cero ni dos**.

**Nota sobre una palabra.** En la frase de arriba «eventos» significa **las
lecturas de temperatura del dominio**, los hechos que ocurren en el camión. **No
describe ningún mecanismo, ninguna herramienta y ninguna forma de construir nada**,
y este repositorio no afirmará lo contrario hasta que exista algo construido y
medido sobre lo que afirmarlo.

**Por qué esta afirmación y no otra.** Una redacción anterior —«ninguna excursión
se pierde y ninguna se actúa dos veces»— **fue refutada el mismo día en que se
escribió** `[V]`: sus dos mitades son el comportamiento por defecto de
herramientas conocidas, y un revisor competente habría dicho «sí, eso es para lo
que sirve esa herramienta». La redacción vigente cambia porque las dos mitades
pasan a ser **decisiones con alternativas**, no configuración por defecto. **Si
esta redacción tampoco aguanta, el sitio para descubrirlo es aquí y ahora.**

Los umbrales con los que se mide —cuántas inversiones, de cuántos envíos, cuántas
muertes, con qué criterio de invalidez— **se fijaron antes de medir**, en el
documento de requerimientos que vive fuera de este repositorio. Los resultados
contra esos umbrales están en §4d. **Mientras no hubo medición no se citó ni un
número: un número de medición en un repositorio sin medición se lee como un
resultado.**

---

## 3 · Lo que este repositorio NO afirma

Esta es la sección más importante del documento. Cada punto es comprobable.

1. **No afirma que exista un producto.** Hay dos servicios que hablan, cada uno
   con su almacén, y un banco de reglas que se ejecuta. **No hay nada que un
   transportista pueda usar**: ninguna interfaz, ninguna sonda real, ningún
   envío que no salga de un guion sintético. Comprobación: listar el repositorio
   y correr los comandos de §4b y §4c.
2. **No afirma que §2 se cumpla sobre ningún mecanismo que no sea uno de los dos
   medidos.** Los medidos son **una llamada directa** y **un transporte por
   eventos con consumidores muertos a propósito**. Sobre los dos la medida existe
   y está publicada con sus denominadores, y **coincide campo a campo**. Sobre
   cualquier tercero, **este repositorio no afirma nada y no lo hará hasta que
   ese tercero exista y se mida**.

   **Y lo que la palabra «distribuida» NO cubre aquí, dicho antes de que lo
   pregunte nadie:** un nodo del intermediario, una máquina, tres particiones.
   **No hay partición de red, ni varias máquinas, ni relojes que discrepen.** Lo
   que se ejerció de verdad son los modos de fallo que trae cambiar el
   transporte: reconsumo tras un reequilibrado, orden entre particiones que
   desaparece, y el desacople entre el avance del consumidor y el compromiso
   local. Los tres los absorbe una clave que ya existía, y por eso ninguno
   obligó a rediseñar.
3. **No afirma nada sobre carga ni sobre concurrencia externa.** El servidor es
   de un solo hilo a propósito, para que el camino sea reproducible, así que el
   control de concurrencia optimista **sigue sin ejercitarse** — no roto: sin
   probar, que no es lo mismo que estar bien. Y **no afirma nada sobre la muerte
   de la máquina**: lo medido es la muerte del proceso. Un corte de corriente no
   está cubierto `[NV]`.
4. **No afirma que los valores del dominio estén validados.** Cuánto dura una
   desviación antes de contar, cuánto se tolera antes de perder el lote y cuánto
   tiempo se conserva el registro son **valores de trabajo adoptados, no
   validados por el negocio**. Están en `decisiones/decisiones-de-negocio.md` con
   la línea de quién los decidió. Uno de ellos mueve directamente el denominador
   de §4d, y allí se dice cuál: **con otro valor, los 56 hechos actuables serían
   otro número.** Lo que §4d mide es que el sistema aplica el valor declarado, no
   que el valor sea el correcto.
5. **No afirma que las cifras de temperatura vengan de la norma.** No vienen: para
   transporte, la norma no fija ninguna `[V]`. Se toman prestadas y se declara.
6. **No afirma haber sido leído por nadie que no sea su autor.** Se intentó dos
   veces y **las dos salieron NO MEDIDO**: una antes de que existiera código y
   otra sobre este mismo texto ya completo. Están declaradas en
   `evidencia/tanda-0.md`, y la primera **no se ha reescrito**: sigue diciendo lo
   que dijo.
   **Esa ausencia es un dato del proyecto, no una omisión del texto.**
7. **No afirma fechas, plazos ni compromisos de entrega.** No hay hoja de ruta con
   fechas en este repositorio, y no se va a añadir una.
8. **No afirma ser una plataforma de logística.** Pedidos, rutas, facturación,
   predicción, gestión de transportistas y aplicación de conductor están **fuera del
   alcance y no se reabren** `[V]`.
9. **No afirma que este repositorio contenga el análisis que lo sostiene.** Los
   documentos de descubrimiento, requerimientos y plan de trabajo viven fuera y
   **no forman parte de este repositorio en este punto**.

---

## 4 · Estado real

| Qué | Estado |
|---|---|
| Código de producto | **Ninguno.** Nada que un transportista pueda usar |
| Banco de reglas | **Ejecutable.** 64 casos pasan; la corrida termina en **VERDE** |
| Dos servicios con fronteras reales | **En pie.** Las siete comprobaciones de §4c pasan; **VERDE** |
| Medición de la afirmación de §2 | **APROBADO** sobre una llamada directa · §4d |
| La misma medición, sobre otro transporte | **APROBADO** sobre eventos, con consumidores muertos · §4d-2 · **coincide campo a campo** |
| Calibración de esa medición | **Hecha**, y omitirla a propósito sale INVÁLIDA |
| Lectura por alguien externo | **NO MEDIDA** — declarada por escrito, ver `evidencia/tanda-0.md` |
| Valores del dominio | **Cerrados como valores de trabajo**, sin validación uno a uno |

**Por qué se publicó primero algo que no hacía nada.** Porque el plan de trabajo
tiene un primer tramo que es **el único sin código**, y su producto entero era
este planteamiento escrito de forma que se pudiera atacar. Si el encuadre estaba
mal, corregirlo costaba editar un texto. Los tramos que aún no existen no se
describen aquí: describirlos sería contar lo que no hay.

---

## 4b · El banco de reglas, y por qué tardó en ponerse verde

```
python ejecutar.py
```

Un solo comando. Sin instalar nada, sin imagen, sin credencial y sin conexión —
solo Python y su biblioteca estándar. Imprime la tabla entera **con los fallos
dentro**: no se promedia, no se descarta y no se resume en un porcentaje.

Lo que hay dentro son las doce reglas de cadena de frío y los 64 casos que las
ejercen, **escritos como datos** en `banco/casos/*.json`, no como funciones de
prueba. Cada conclusión tiene que **nombrar la regla que la produjo**, también
cuando la conclusión es permisiva: «dentro de rango» no es la ausencia de
veredicto, es un veredicto. Un valor correcto sin regla que lo nombre **no cuenta
como conclusión** y el caso falla.

Hoy la corrida termina así:

| | |
|---|---|
| 64 casos ejecutados, 61 atribuibles a una regla | **64 pasan, 0 fallan** |
| Determinismo · dos corridas con reloj distinto | **PASA** |
| Ninguna conclusión sin nombrar su regla | **PASA** |
| Al apagar cada pieza, ¿caen todos sus casos? | **13/13** |
| ¿Dice la mutación **cuál** pieza falta, y no solo que falta una? | **13/13** |
| ¿Se queda la mutación dentro de su regla? | **13/13** |
| ¿Hasta dónde puede llegar legítimamente su cascada? | **13/13** |
| El tipo de producto vive en el lote, no en el envío | **PASA** |
| Un solo comando, sin dependencias | **PASA** |
| **Desenlace** | **VERDE** (código de salida 0) |

**La última fila estuvo un tramo en NO EVALUABLE, y el desenlace era INVÁLIDO —
ni verde ni rojo.** Merece contarse, porque es lo único de este repositorio que
demuestra algo en vez de afirmarlo.

El dominio encadena: apagar el umbral de temperatura hace que no haya
excursiones, ni acumulado, ni lote perdido, y con ello cambian cuarenta y tres
casos. Para juzgar si una cascada llegó **demasiado** lejos hay que saber primero
**qué regla alimenta a qué regla** — y eso es una afirmación sobre el dominio,
no algo que se pueda leer del código. Quien lo dedujera del código estaría
midiendo el código contra sí mismo.

Ese dato no existía. Había dos salidas fáciles y las dos producen un verde falso:
ensanchar las listas hasta que nada quede fuera —la condición se vuelve
trivialmente cierta— o deducir la cadena del número de cada regla, que **está
medido que da dos respuestas equivocadas**. Se tomó la tercera: **publicar
INVÁLIDO y decir exactamente qué dato faltaba.** Publicarlo como rojo habría
dicho que el código falla, y no fallaba. Publicarlo como verde habría dicho que
la condición se comprobó, y no se había comprobado.

Después alguien declaró la relación —doce filas, con la razón de cada una— y la
corrida se puso verde **sin tocar una línea de código**. Ese es el punto:
**la condición no se relajó, se alimentó.** Un instrumento de medición tiene que
saber negarse, y este se negó durante el tiempo que le faltó un dato.

**Y la corrida enseña que las condiciones pueden ponerse rojas**, en vez de
afirmarlo: cada ejecución las ejerce contra defectos fabricados a propósito
—fusionar las dos mitades de una regla, acoplar dos reglas que deberían ser
independientes, declarar una cascada vacía— y publica el resultado. *Una
comprobación que no se ha visto fallar no está demostrado que mida.*

El detalle, con los números pieza por pieza y con lo que deliberadamente **no** se
tocó para no fabricar un verde, está en **`banco/NOTAS-IMPLEMENTACION.md`**.

---

## 4c · Dos servicios que hablan, y el que cuenta no es el que muere

```
python levantar.py     los dos servicios en pie, con los almacenes vacíos
python comprobar.py    las siete comprobaciones de este tramo
```

**Cuatro procesos y dos ficheros. Ni un demonio, ni una cuenta, ni un secreto,
ni una imagen.** Todo es biblioteca estándar, y el arranque de un comando **no
depende de Docker**: si algún día hay contenedores, serán una segunda forma de
levantar lo mismo, no la primera.

Lo que hay dentro son dos servicios de verdad separados. **SV-1** aplica las
reglas —las mismas de §4b, importadas, no reescritas— y **SV-2** guarda el libro
de acciones. Cada uno tiene su propio almacén, y la separación es comprobable:
ninguna tabla aparece en los dos, ninguna clave foránea cruza, y ninguno de los
dos tiene siquiera camino en el código para abrir el fichero del otro.

Hoy las siete comprobaciones pasan y el desenlace es **VERDE**. Dos merecen
contarse:

**El camino entero, y por qué el número no se descuadra.** Cien lecturas entran,
SV-1 las persiste antes de mirarlas, evalúa, y acaba proponiendo actuar **muchas
veces sobre los mismos cuatro hechos** — porque reevalúa en cada lectura. En el
libro acaban **cuatro acciones, no muchas**. Quien deduplicó no fue la memoria
del proceso, que se muere con él: fue **la clave del hecho mismo** — qué lote,
qué excursión, qué clase de acción.

**El que cuenta no es el que muere.** Se mata a SV-1, se comprueba que su puerto
ya no acepta conexiones, y se le pregunta el recuento a SV-2: sigue contestando
el mismo número. Y lo cuenta contando filas, no leyendo una columna que dice
cuántas hay — una columna así se puede desincronizar de lo que dice contar.

**Lo que este verde no dice, y es la mitad del asunto.** Aquí a SV-1 se le mata
**después** de haber entregado todo y en un punto tranquilo. Matarlo **entre
decidir y registrar**, que es el único sitio donde la afirmación de §2 se juega
algo, no se ha hecho. Este tramo enseña que el testigo existe y sobrevive; **no
mide nada de §2**.

El resto —incluidas cuatro cosas declaradas en vez de dadas por cubiertas— está
en **`NOTAS-PL2.md`**.

---

## 4d · La afirmación de §2, medida

```
python veredicto.py
```

**APROBADO.** La salida completa está guardada en
`evidencia/pl-3/veredicto-aprobado.txt`, y empieza así:

> **C1 medido sobre un mecanismo directo.** Esta corrida no dice nada sobre
> ningún otro mecanismo, y no lo dirá hasta que exista y se mida.

Esa frase es de **esta** corrida, la del transporte directo, y sigue siendo
verdad para ella. El otro transporte ya existe y ya se midió: **§4d-2**. Y la
frase de aquella corrida no se ha editado a posteriori — la evidencia guardada
dice lo que dijo cuando se ejecutó.

| | |
|---|---|
| **Orden** · divergencias contra la referencia | **0** |
| sobre inversiones que **sí** cambiaban la conclusión | **440**, en 7 envíos y las 5 clases |
| **Exactamente una vez** · hechos con 0 acciones · con 2 | **0 · 0** |
| sobre hechos actuables distintos · muertes de proceso | **56 · 56** |

### Los dos números que nunca van separados

Se barajaron lecturas hasta producir **1248 pares fuera de orden**. De esos,
**440 cambiaban la conclusión** por sí solos; los otros 808 no cambiaban nada.
**El denominador es 440**, no 1248: publicar el número grande sería publicar algo
que no se midió. Barajar por barajar no mide.

### Por qué el cero significa algo

Un cero de divergencias puede querer decir dos cosas muy distintas: *«el orden se
respeta»* o *«la medición no mira»*. Para separarlas, la misma medición se corre
contra versiones **rotas a propósito**:

| Se rompe | Qué pasa |
|---|---|
| El sistema deja de reconstruir el orden | **18 divergencias** |
| Se marca la acción como hecha *antes* de hacerla | **28 hechos se pierden** |
| El receptor deja de reconocer un hecho ya registrado | **28 hechos se duplican** |

Las tres se rompen. **Si no se rompieran, el verde no significaría nada** — y por
eso omitir esta calibración no da un aprobado con reservas: da **MEDICIÓN
INVÁLIDA**. Está ejecutado a propósito y guardado en
`evidencia/pl-3/veredicto-sin-calibracion.txt`: su **única** falta es que falta
la calibración; todo lo demás pasó.

### Lo que se ve cuando el mecanismo trabaja

De las 56 muertes, 28 ocurren **después** de que el receptor haya registrado la
acción y **antes** de que el emisor pueda anotar que lo hizo. Al revivir, el
emisor reenvía —no tiene forma de saber que ya llegó— y el receptor reconoce el
hecho en vez de apuntarlo dos veces. **28 entregas repetidas absorbidas, y 56
acciones para 56 hechos.** Eso es lo que la frase de §2 dice, ejecutado.

### Y lo que quedó sin comprobar, dicho en voz alta

El veredicto se emite **con el emisor muerto y su puerto cerrado**: si hiciera
falta preguntarle a él para saber cuántas acciones hay, el recuento viviría en el
proceso que se cae, y no serviría de nada. Sale completo sin él.

**Pero una de las líneas no se puede comprobar así**, y aparece con esas palabras:
*no se pudo comprobar*. Es la que cruza de un almacén al otro. Su ausencia no
invalida la corrida — pero **un aprobado con líneas sin comprobar es más débil, y
tiene que verse.**

El detalle está en **`NOTAS-PL3.md`**, incluidos **dos defectos del instrumento**
que se cazaron antes de publicar nada: uno hacía que la medición midiera otra
cosa, y otro dejaba una de las versiones rotas **sin romper, en silencio**.

---

## 4d-2 · La misma medición, sobre otro transporte

Todo lo de §4d se midió sobre una **llamada directa**. Que la garantía no
dependiera de ese mecanismo era, hasta aquí, **una afirmación de diseño sin
comprobar**: no había ningún sitio donde enchufar otro transporte, así que no
había forma de intentar romperla.

Ahora hay dos, y la medición entera se repitió sobre el segundo:

```
python cinturon.py --transporte eventos
```

| | llamada directa | eventos |
|---|---|---|
| **Orden** · divergencias | **0** | **0** |
| lotes × campos comparados | 10 × 9 | 10 × 9 |
| divergencias con la versión rota | 18 | **18** |
| **Exactamente una vez** · hechos actuables | 56 | **56** |
| muertes de proceso (antes · después de enviar) | 56 (28 · 28) | **56 (28 · 28)** |
| acciones contadas en el testigo | 56 | **56** |
| hechos con 0 acciones · con ≥2 | 0 · 0 | **0 · 0** |
| entregas repetidas absorbidas | 28 | **28** |
| anomalías de las dos versiones rotas | 28 / 28 | **28 / 28** |
| **Veredicto del cinturón** | **APROBADO** · 0 | **APROBADO** · 0 |

**Que las dos columnas coincidan es el resultado**, no la coincidencia. Si la
garantía hubiera vivido en el transporte, cambiarlo la habría cambiado. Vive
donde el diseño dice que vive: en la bandeja de salida del emisor y en la clave
de la terna del receptor.

### Qué se ejerció de verdad, y qué no

Cambiar de transporte **añade tres modos de fallo** que la llamada directa no
tiene. Los tres ocurrieron y los tres los absorbió una clave que ya existía:

| Modo de fallo | Qué lo absorbe |
|---|---|
| La misma lectura se procesa dos veces tras un reequilibrado | La ingesta es idempotente por `(envío, secuencia)`: la segunda no crea nada |
| El orden entre particiones desaparece | **Nunca se dependió de él.** El orden se re-deriva de la secuencia. Las lecturas se repartieron **26 / 50 / 24** entre tres particiones |
| El avance del consumidor y el compromiso local no son la misma transacción | El avance se confirma **después** del compromiso local, nunca antes. Morir en medio produce un reconsumo, y reconsumir no crea nada |

**Y lo que NO se ejerció, que es la mitad honesta de esto:** un nodo del
intermediario, una máquina, tres particiones. **Sin partición de red, sin varias
máquinas, sin relojes que discrepen, sin carga y sin concurrencia externa.** El
control de concurrencia optimista **sigue sin ejercitarse** también aquí.

### Lo que costó

| | directo | eventos |
|---|---|---|
| Cinturón completo | **221,3 s** | **408,6 s** (**1,85×**) |
| Muertes provocadas | 168 | 168 |

**Se paga en cada corrida, no una vez.** Y con el intermediario configurado para
*no* esperar antes de reagrupar altas de consumidor; sin eso sería peor. La
cifra no es interpretable sin esa línea al lado, y por eso van juntas. El
registro completo está en `evidencia/pl-6/ce4-costo-de-la-plomeria.md`.

### Dos defectos, los dos del instrumento

Ninguno del sistema medido. El primero traía las lecturas **de una en una** y
hacía que la corrida no terminara a tiempo: se declaraba inválida por ser
grande, no por estar atascada. El segundo es peor de familia: la salida seguía
imprimiendo **«medido sobre un mecanismo directo»** *mientras corría sobre el
otro transporte* — un artefacto publicando la leyenda en vez del hecho medido.
Estaba escrita a mano; ahora **se deriva del transporte real**, así que no puede
quedarse vieja.

---

## 4e · Todo lo anterior, en cada push

```
python cinturon.py
```

Ocho etapas **de la más barata a la más cara**. La primera no arranca un solo
proceso y aun así puede poner rojo el push entero; la última mata ciento sesenta
y ocho. Esta tabla **no está tecleada**: se genera desde el artefacto crudo de la
corrida con `python tabla.py evidencia/pl-6/verde/corrida.json`, y si no se pudiera regenerar, la publicación no
valdría.

| Etapa | Qué corre | Desenlace | Segundos |
|---|---|---|---|
| **EP-0** | ESTATICA · el gate de texto | **APROBADO** | 0.0 |
| **EP-1+2** | BANCO Y MUTACION POR REGLA | **APROBADO** | 15.8 |
| **EP-3** | PREFLIGHT DE LA MEDICION | **APROBADO** | 0.5 |
| **EP-4..7** | C1-A · C1-B · CALIBRACION · SEC-5 | **APROBADO** | 232.2 |
| | **TOTAL** | **APROBADO** | **248.6** |

### Tres desenlaces, no dos

El cinturón no devuelve «bien o mal». Devuelve **APROBADO**, **FALLO** o
**MEDICIÓN INVÁLIDA**, y **cualquier código que el proceso no haya elegido cuenta
como inválido**. No es cosmética: si «fallo» fuera el código 1, una excepción del
instrumento se leería como *«el sistema perdió una acción»* — y esas son dos cosas
distintas. Para un CI que solo entiende éxito y fallo, **éxito es el código 0
exacto**; los otros dos son rojo, y la asimetría es deliberada.

**Los tres están demostrados, no afirmados**, y se vuelven a demostrar cada vez
que el pipeline cambia:

| Desenlace | Cómo se provocó | Código |
|---|---|---|
| **APROBADO** | La corrida normal | 0 |
| **FALLO** | Se metió una anulación de veredicto en el fichero del CI | 20 |
| **MEDICIÓN INVÁLIDA** | Se omitió la calibración, y solo eso | 30 |

El segundo lo cazó **la etapa que se vigila a sí misma**: el cinturón lee su
propio fichero y el del CI, y se pone rojo si encuentra cualquiera de las formas
conocidas de anular un veredicto. Tardó **0,0 segundos y 0 procesos**.

### Lo que no se reintenta, y por qué

**Un fallo válido no se repite jamás; repetir un rojo hasta que salga verde es
lavarlo.** Como fallo e inválido comparten color, un reintento automático del
proveedor reintentaría un fallo válido — así que aquí no hay ninguno. Repetir es
decisión del instrumento, que lee **su propio motivo** y solo repite lo que puede
salir distinto.

### Lo que cuesta, y lo que no se sabe

Durante siete tramos esta sección dijo que la pregunta *«¿cabe en el plan
gratuito?»* estaba **sin responder a propósito**, porque no había proveedor
elegido y aquí no entra ninguna cifra de minutos, ningún precio ni ningún nombre
de plan **sin la cita literal de su documentación**. En este portafolio ya murió
una premisa así, y costó horas.

**Ya está respondida, y con las dos mitades que hacían falta:**

| | |
|---|---|
| **Límite citado** | *«Each job in a workflow can run for up to 6 hours of execution time»* — atribuido a **All GitHub-hosted runners** |
| **Medido en la máquina del proveedor** | **76 s** · corrida verde · commit `d93d88c` |
| **Margen consumido** | **0,35 %** |
| **Coste** | Ninguno · *«GitHub Actions usage is free for standard GitHub-hosted runners in public repositories»* |

**Cabe, y no por suerte: cabe porque el repositorio es público.** En uno privado
la respuesta se mediría contra una cuota de minutos y podría ser otra.

Y las dos duraciones van **etiquetadas, nunca promediadas**: **221,3 s** en la
máquina del autor (Windows) y **76 s** en la del proveedor (Linux). El CI es casi
3× más rápido y **eso no es una mejora del proyecto**: el cinturón arranca 168
procesos, y crear procesos cuesta muy distinto en cada sistema. Quedarse con la
cifra menor sería publicar una mejora que nadie midió.

**Lo que ese CI encontró en su primera corrida, en nueve segundos:** que el
digesto del banco vigilaba el checkout y no el banco — un fichero con CRLF y
siete con LF hacían imposible que Windows y Linux coincidieran. **Ocho tramos de
verde local no lo vieron**, porque ninguno corrió fuera de una sola máquina. El
detalle está en `evidencia/ce2-el-cinturon-en-ci.md`.

**Lo que sigue sin correr en CI:** la medición sobre el otro transporte. Necesita
un intermediario en contenedores que ese trabajo no levanta, y se dice en vez de
dejar que parezca cubierto.

El detalle está en **`NOTAS-PL4.md`**, con dos defectos más que la propia corrida
destapó.

---

## 5 · Qué leer, y en qué orden

1. **Este README** — el problema y la afirmación.
2. **`evidencia/tanda-0.md`** — qué se iba a preguntar a un lector externo, por qué
   no se preguntó, qué se pierde por eso y cómo se cierra más adelante sin dejar
   de ser honesto.
3. **`decisiones/decisiones-de-negocio.md`** — los valores del dominio, con valor
   exacto y con la línea de quién decidió cada uno.
4. **`banco/NOTAS-IMPLEMENTACION.md`** — por qué la corrida estuvo en INVÁLIDO y
   qué la sacó de ahí, qué defecto de modelado se encontró por el camino y qué
   tres comprobaciones daban rojo sobre código correcto.

5. **`NOTAS-PL2.md`** — qué mide cada una de las siete comprobaciones de los dos
   servicios, y las cuatro cosas que se declaran en vez de darse por cubiertas.
6. **`NOTAS-PL3.md`** — cómo se midió §2, por qué el cero significa algo, y los
   dos defectos del instrumento que se cazaron antes de publicar nada.
7. **`NOTAS-PL4.md`** — el cinturón, sus tres desenlaces demostrados y su factura.
8. **`evidencia/`** — la salida real de las corridas, incluidas **las que salieron
   inválidas y roja a propósito**.

Y una sola cosa que ejecutar si solo se va a ejecutar una: `python cinturon.py`,
que corre todo lo demás en orden. Ninguna deja nada instalado.

---

## 6 · Cómo refutar esto sin ejecutar nada

Este texto se considera **exitoso si alguien lo derriba**. Tres preguntas bastan, y
ninguna exige instalar nada:

1. **¿Qué problema crees que resuelve esto?** Si tu respuesta no se parece a la
   §1, el planteamiento falla — y falla barato.
2. **¿La afirmación de §2 te parece difícil, o te parece el comportamiento por
   defecto de una herramienta que ya conoces?** Si es lo segundo, dilo: es
   exactamente lo que tumbó la redacción anterior.
3. **¿Defenderías los valores de `decisiones/decisiones-de-negocio.md`?** Si no,
   di cuál y con qué lo cambiarías. Todavía son reversibles sin coste.

Y una cuarta que sí exige ejecutar, y que es la que más interesa:

4. **¿Te parece que el INVÁLIDO que cuenta §4b fue honestidad o fue una excusa?**
   Hoy la corrida está verde, así que es fácil contarlo bonito. Si crees que fue
   una forma elegante de no dar un rojo, dilo. Lo comprobable: la condición se
   puso verde **sin que se tocara una línea de código**, solo añadiendo un dato
   — y `banco/NOTAS-IMPLEMENTACION.md` §2 dice exactamente qué se decidió **no**
   tocar mientras tanto. Esa decisión se puede atacar.

5. **Ahora que §4d existe: ¿te convence el denominador?** Son 440 inversiones, no
   1248. Si crees que quedarse con las que cambian la conclusión infla el
   resultado —o que 1248 lo desinflaría— dilo con números: los dos están
   publicados justamente para que se pueda discutir cuál es el bueno.

**Las respuestas se transcriben sin corregir** en `evidencia/tanda-0.md`, incluidas
las que dejen mal al planteamiento. Una respuesta editada no sirve para nada.

---

## 7 · De dónde viene esto, y con qué se relaciona

Este repositorio no es el primero de su autor, y **casi todo lo que aquí se hace
bien se aprendió fallando en los anteriores**. Decir de dónde viene cada cosa es
parte de lo que se publica: una práctica sin su origen parece una opinión.

### Lo que se hereda, y de qué fallo concreto salió

| Práctica | De dónde salió |
|---|---|
| **Una prueba negativa afirma la CLASE del fallo**, no que «algo falló» | De un proyecto anterior donde una prueba pasaba por el motivo equivocado |
| **La mutación tiene que tirar los casos DE ESA regla**, no casos cualesquiera | Es lo que encontró **una regla implementada dos veces, con media viva** — un defecto real que ninguna otra capa vio |
| **Un número en pantalla necesita un guardia** | De publicar una cifra que nadie podía recalcular |
| **Publicar la tabla CON los fallos dentro** | De aprender que promediar una tabla es elegir qué filas se copian |
| **Declarar lo que no se midió** | De confundir «no salió mal» con «se comprobó» |
| **Un instrumento tiene que saber negarse** | De una medición que salía verde sin haber ejercido nada |

Las tres últimas son las que más se usan aquí: **este proyecto publica dos
corridas que salieron mal a propósito**, y una lista de lo que no midió pegada a
cada resultado.

### Con qué NO compite

Hay otro repositorio del portafolio que **sí tiene algo que se puede pinchar**, y
contra la indiferencia —que es el enemigo real— un enlace vivo gana a un
repositorio que hay que clonar. Este proyecto **no lo desplaza**: cubre un eje
distinto, el que aquel declaró explícitamente que no compraba.

La regla que se aplica es sencilla: **cuando lo que hace falta es algo que se
pueda abrir y ver, ese otro; cuando lo que hace falta es una garantía medida y
refutable, este.** No son el mismo argumento y no se sustituyen.

### La frase que este README no podía decir, y qué hizo falta para decirla

Durante ocho tramos hubo aquí una prohibición explícita: **este texto no podía
decir «arquitectura distribuida»** —ni un par de expresiones vecinas— hasta que
existiera el tramo que las compra. No era una formalidad. Había un guardián
automático que revisaba todos los textos publicables en cada corrida y ponía el
push en rojo si alguno se adelantaba, con la lista de textos **derivada y no
escrita a mano**, porque una lista escrita a mano deja escapar al fichero nuevo.

**Ese tramo ya existe, y por eso la frase aparece ahora en el encabezado.** Lo
que la compró no es haber montado la plomería: es que **la medición entera se
repitió sobre ella y dio lo mismo, campo a campo** (§4d-2).

La prohibición no se ha borrado: **ha cambiado de objeto.** El guardián sigue
corriendo en cada push, y ahora lo que exige es que **quien use la frase diga
sobre qué se midió**. Una afirmación fuerte sin su denominador al lado es
exactamente lo que este repositorio lleva desde el principio negándose a
publicar, y levantar la prohibición sin poner nada en su sitio habría sido
cambiar una regla por un hueco.

**Y lo que sigue sin poder decirse**, porque no se ha medido: que esto corra
orquestado, que aguante carga, que sobreviva a una partición de red o a varias
máquinas, o que la muerte de la máquina —no la del proceso— esté cubierta. Lo
medido es un nodo, una máquina, tres particiones y 168 muertes de proceso por
corrida. Está en §4d-2, con esas palabras.

---

## 8 · Cómo leer las marcas

| Marca | Significa |
|---|---|
| `[V]` | Verificado contra una fuente que se puede citar |
| `[A]` | Asumido o decidido, sin fuente externa que lo respalde |
| `[NV]` | No verificado, y se dice en vez de darse por bueno |

**Un texto sin marcas no distingue lo que sabe de lo que supone.** Este las lleva
para que la diferencia sea visible desde fuera.
