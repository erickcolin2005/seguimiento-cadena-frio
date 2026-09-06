# Cadena de frío en transporte · P1

> **Estado: hay código, y no mide la afirmación de §2.** Lo que existe es un
> **banco de reglas de cadena de frío que se ejecuta** — 64 casos, trece piezas
> apagables— y hoy su corrida termina en **VERDE**.
>
> **Ese verde no dice nada sobre §2.** Dice que las reglas de temperatura viven
> en el código, que cada conclusión nombra la regla que la produjo, y que apagar
> cualquiera de las trece piezas se nota. El banco **no mata ningún proceso** y
> **no mide ni el orden ni la no duplicación**. Nadie externo ha leído esto
> todavía.
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

Esta es la afirmación. **No es un resultado.** Se escribe entera y en presente
porque así es como se va a intentar romper, no porque hoy se sostenga:

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

Los números concretos con los que se medirá —cuántos casos, de cuántos envíos, con
qué criterio de medición inválida— **existen y están fijados en el documento de
requerimientos, fuera de este repositorio**. No se citan aquí a propósito: **un
número de medición en un repositorio sin medición se lee como un resultado.**

---

## 3 · Lo que este repositorio NO afirma

Esta es la sección más importante del documento. Cada punto es comprobable.

1. **No afirma que exista un producto.** Lo que hay es el banco de reglas de §4b,
   que se ejecuta y no sirve a nadie: no hay ingesta, ni almacenamiento, ni
   interfaz, ni nada que un transportista pueda usar. Comprobación: listar el
   contenido del repositorio y correr el único comando que hay.
2. **No afirma que la afirmación de §2 se cumpla, ni en parte.** El banco mide si
   las reglas de temperatura concluyen lo que deben y nombran cuál de ellas lo
   concluyó. **De orden y de no duplicar acciones no mide nada**, y su propia
   salida lo dice en la última línea. **El verde de §4b es el verde del banco de
   reglas, y de nada más**: no hay porcentaje ni resultado sobre §2. **Cualquier
   cifra de cumplimiento de §2 que alguien lea aquí, la habrá puesto él.**
3. **No afirma nada sobre cómo se comportaría ante una caída, una carga o una
   interrupción.** En el banco **no muere ningún proceso**: las muertes de los
   casos X-01…X-07 están modeladas como decidir dos veces lo mismo, que es una
   regla del dominio y no una caída real.
4. **No afirma que los valores del dominio estén validados.** Cuánto dura una
   desviación antes de contar, cuánto se tolera antes de perder el lote y cuánto
   tiempo se conserva el registro son **valores de trabajo adoptados, no
   validados por el negocio**. Están en `decisiones/decisiones-de-negocio.md` con
   la línea de quién los decidió. Uno de ellos mueve directamente el denominador
   de la futura medición, y allí se dice cuál.
5. **No afirma que las cifras de temperatura vengan de la norma.** No vienen: para
   transporte, la norma no fija ninguna `[V]`. Se toman prestadas y se declara.
6. **No afirma haber sido leído por nadie que no sea su autor.** La tanda 0 de
   lectura externa está **NO MEDIDA**, y por qué está en `evidencia/tanda-0.md`.
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
| Código de producto | **Ninguno.** Lo que hay es el banco de reglas de §4b |
| Banco de reglas | **Ejecutable.** 64 casos pasan; la corrida termina en **VERDE** |
| Medición de la afirmación de §2 | **Ninguna** |
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

Y una cosa que ejecutar: `python ejecutar.py`. Tarda menos de lo que se tarda en
leer esta línea y no deja nada instalado.

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

**Las respuestas se transcriben sin corregir** en `evidencia/tanda-0.md`, incluidas
las que dejen mal al planteamiento. Una respuesta editada no sirve para nada.

---

## 7 · Cómo leer las marcas

| Marca | Significa |
|---|---|
| `[V]` | Verificado contra una fuente que se puede citar |
| `[A]` | Asumido o decidido, sin fuente externa que lo respalde |
| `[NV]` | No verificado, y se dice en vez de darse por bueno |

**Un texto sin marcas no distingue lo que sabe de lo que supone.** Este las lleva
para que la diferencia sea visible desde fuera.
