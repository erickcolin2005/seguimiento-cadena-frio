# Cadena de frío en transporte · P1

> **Estado: sin código.** Este repositorio contiene tres textos y nada más.
> Nada está construido. Nada está medido. Nadie externo lo ha leído todavía.
>
> Este texto existe para que alguien pueda **refutar el planteamiento antes de que
> exista código**, cuando refutarlo cuesta reescribir un texto y no reescribir un
> sistema.

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

1. **No afirma que exista software.** No hay una sola línea de código de producto.
   Comprobación: listar el contenido del repositorio.
2. **No afirma que la afirmación de §2 se cumpla, ni en parte.** No se ha ejecutado
   ninguna medición. No hay corrida, ni resultado, ni porcentaje, ni verde.
   **Cualquier cifra de rendimiento o de cumplimiento que alguien lea aquí, la
   habrá puesto él.**
3. **No afirma nada sobre cómo está construido ni sobre cómo se comportaría ante
   una caída, una carga o una interrupción.** No está construido.
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
| Código de producto | **Ninguno**, y esa es la condición de este punto del plan |
| Medición de la afirmación de §2 | **Ninguna** |
| Lectura por alguien externo | **NO MEDIDA** — declarada por escrito, ver `evidencia/tanda-0.md` |
| Valores del dominio | **Cerrados como valores de trabajo**, sin validación uno a uno |
| Contenido del repositorio | Este README y los dos textos que enlaza |

**Por qué se publica algo que no hace nada.** Porque el plan de trabajo tiene un
primer tramo que es **el único sin código**, y su producto entero es este
planteamiento escrito de forma que se pueda atacar. Si el encuadre está mal, hoy
corregirlo cuesta editar un texto. Los demás tramos no se describen aquí:
describirlos sería contar lo que aún no existe.

---

## 5 · Qué leer, y en qué orden

1. **Este README** — el problema y la afirmación.
2. **`evidencia/tanda-0.md`** — qué se iba a preguntar a un lector externo, por qué
   no se preguntó, qué se pierde por eso y cómo se cierra más adelante sin dejar
   de ser honesto.
3. **`decisiones/decisiones-de-negocio.md`** — los valores del dominio, con valor
   exacto y con la línea de quién decidió cada uno.

No hay nada más que leer, y no hay nada que ejecutar.

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
