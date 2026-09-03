# Decisiones de negocio · DN-01 y DN-05…DN-08

> **Estado de las cinco: valores de trabajo adoptados, NO validados.**
>
> **La constancia, dicha con precisión:** **Erick ordenó cerrar la puerta G3; no
> revisó los valores uno a uno.** Cerrar la puerta y validar los valores **no son
> el mismo acto**, y este documento existe para que no se confundan.
>
> **Son reversibles sin coste mientras no empiece el tramo siguiente**, que es el
> primero que produce código. A partir de ahí, cambiar uno deja de costar editar
> una tabla.

---

## 1 · Por qué este documento existe antes que nada

Estos cinco valores **parecen requisitos y no lo son**: son decisiones de negocio
con consecuencia, tomadas sin que la norma las obligue. Escritas dentro de una
especificación técnica, se leen como datos; **y un dato no se discute, mientras que
una decisión sí**.

**El precedente, que es lo que hace esto urgente:** en el proyecto hermano **P2, las
reglas de negocio equivalentes (RN-02…RN-07) quedaron aceptadas por defecto y
nunca validadas, y siguen siendo deuda abierta** `[V]`. Nadie las rechazó; nadie
las aprobó; simplemente dejaron de estar en discusión por el hecho de estar
escritas. **Aquí se nombran desde el principio, mientras cambiarlas cuesta editar
una tabla.**

---

## 2 · Contexto mínimo: los tres tipos de producto

Los valores de DN-05 y DN-06 **son por tipo de producto**, no globales.

| Código | Tipo | Rango admisible |
|---|---|---|
| **P-REF** | Refrigerado | 2 ºC a 6 ºC, ambos inclusive |
| **P-CON** | Congelado | ≤ −18 ºC |
| **P-FRE** | Fresco controlado | 12 ºC a 18 ºC, ambos inclusive |

**Los rangos son de otras dos decisiones (DN-02 y DN-09) y no se cierran en este
documento.** Se muestran solo para que los valores de abajo se puedan leer. **Lo
que sí hay que saber al leerlos:** para el transporte, la norma **no fija ninguna
temperatura numérica** `[V]`; las cifras de refrigerado se toman prestadas de
artículos que regulan manipulación y esperas entre etapas, y se declara. La de
congelado sí está en la norma `[V]`, pero **el artículo exacto no está verificado**
`[NV]`.

---

## 3 · Las cinco decisiones, con valor y con dueño

### DN-01 · Retención del registro de temperatura de transporte

| | |
|---|---|
| **Valor** | **12 meses**, igual para los tres tipos de producto |
| **¿La norma lo exige?** | **NO.** El plazo de conservación de la norma es para **registros de lote**, no de transporte `[V]`. Se elige por debajo del techo de dos años que aparece en el marco, **por prudencia, no por obligación** |
| **Quién lo decidió** | **Propuesto por el análisis de requerimientos** como decisión de negocio `[A]`. **Adoptado por orden de Erick de cerrar la puerta G3. Erick no revisó este valor.** |
| **Riesgo si está mal** | **Bajo.** Es un plazo de conservación: cambiarlo no altera ninguna conclusión sobre ningún lote |

### DN-05 · Duración mínima para que una desviación abra excursión

| | |
|---|---|
| **Valor** | **P-REF: 5 minutos · P-CON: 2 minutos · P-FRE: 10 minutos** |
| **¿La norma lo exige?** | **NO. Sin ningún anclaje normativo** `[A]` |
| **Qué decide** | Por debajo de esa duración, una lectura fuera de rango es **desviación transitoria** y no cuenta. Por encima, **abre excursión** |
| **Quién lo decidió** | **Propuesto por el análisis de requerimientos, sin fuente externa** `[A]`. **Adoptado por orden de Erick de cerrar la puerta G3. Erick no revisó estos valores uno a uno.** |
| **Riesgo si está mal** | **ALTO — el segundo de la lista.** Ver §4 |

### DN-06 · Duración tolerada acumulada antes de la pérdida del lote

| | |
|---|---|
| **Valor** | **P-REF: 30 minutos · P-CON: 10 minutos · P-FRE: 60 minutos** |
| **¿La norma lo exige?** | **NO. Sin ningún anclaje normativo** `[A]` |
| **Qué decide** | Las excursiones de un lote **suman**. Si el acumulado supera este valor, **el lote se pierde** |
| **Quién lo decidió** | **Propuesto por el análisis de requerimientos, sin fuente externa** `[A]`. **Adoptado por orden de Erick de cerrar la puerta G3. Erick no revisó estos valores uno a uno.** |
| **Riesgo si está mal** | **EL MÁS ALTO DE LAS CINCO.** Ver §4 |

### DN-07 · «Lote no apto» es irreversible

| | |
|---|---|
| **Valor** | **Una vez que un lote queda no apto, ninguna lectura posterior lo rehabilita.** No hay recuperación, ni parcial ni por mejora sostenida |
| **¿La norma lo exige?** | **NO.** Deriva del hecho de negocio *«un lote que rompió la cadena de frío no se recupera»* `[V]`, **pero el umbral exacto que lleva a ese estado es una decisión** `[A]`, y ese umbral es DN-06 |
| **Quién lo decidió** | **Propuesto por el análisis de requerimientos** `[A]`. **Adoptado por orden de Erick de cerrar la puerta G3. Erick no revisó este valor.** |
| **Riesgo si está mal** | **Medio.** La regla en sí es la que el negocio afirma; lo discutible **no es la irreversibilidad, es dónde se pone la frontera** — es decir, DN-06 otra vez |

### DN-08 · Un hueco de datos mayor que la duración mínima impide declarar apto un lote

| | |
|---|---|
| **Valor** | **Si falta información durante más tiempo que la duración mínima del tipo (DN-05), el lote NO se puede declarar apto**, y su conclusión queda provisional. **No lo declara perdido**: no consta que se perdiera |
| **¿La norma lo exige?** | **NO. Es una decisión entera** `[A]`. Es el principio *«lo que no se midió no se afirma»* aplicado al dominio |
| **Quién lo decidió** | **Propuesto por el análisis de requerimientos, sin fuente externa** `[A]`. **Adoptado por orden de Erick de cerrar la puerta G3. Erick no revisó este valor.** |
| **Riesgo si está mal** | **Medio.** Un valor mal puesto convierte huecos normales en conclusiones provisionales, o al revés, **da por bueno un lote del que no se sabe nada durante un tramo del viaje** |

---

## 4 · Cuál tiene riesgo real, y por qué

**No las cinco pesan igual. Dos sí, y en este orden.**

### 1.º · DN-06 — mueve el denominador de la medición

DN-06 fija **cuánto se tolera antes de perder el lote**, y con eso fija **cuántas
situaciones del banco de pruebas terminan siendo hechos sobre los que hay que
actuar**. Esa cantidad **es el denominador de la futura medición** de la afirmación
del proyecto.

**La consecuencia, dicha sin rodeos:** un DN-06 más generoso produce **menos**
hechos accionables; uno más estricto produce **más**. Es decir: **cambiar un valor
que nadie validó cambia el número contra el que se va a medir la afirmación
central del proyecto.** No cambia si el software es correcto; **cambia cuánta
evidencia hay de que lo sea**, y por tanto cuánto significa el resultado.

**Por eso es la más peligrosa de las cinco: es la única que puede alterar el
significado de una medición sin que la medición se entere.**

### 2.º · DN-05 — decide de qué se predica «exactamente una vez»

DN-05 decide **cuándo empieza a existir una excursión**. Y la excursión es **la
cosa** de la que la afirmación del proyecto dice *«se actúa exactamente una vez»*.

**Si la frontera se mueve, se mueve la identidad de lo contado:** dos desviaciones
cortas y separadas pueden ser **una excursión o ninguna**, según DN-05. La
afirmación seguiría siendo verdad en su forma —una acción por hecho, ni cero ni
dos—, **pero estaría hablando de otros hechos.**

**Y hay un matiz que no conviene perder:** la afirmación es de **cardinalidad** (una
sola acción), no de identidad de la acción. **DN-05 no toca la cardinalidad; toca
la identidad del hecho que se cuenta.** Es una dependencia silenciosa: no rompe
nada visible, redefine el sujeto.

### Las otras tres

**DN-07 y DN-08** heredan su riesgo de DN-06 y DN-05 respectivamente: la regla es
razonable, **el umbral que la dispara es el discutible**. **DN-01** es la de menor
riesgo: es un plazo de conservación y no participa de ninguna conclusión.

---

## 5 · La pregunta que sigue sin contestarse

El análisis dejó **una sola pregunta** para Erick sobre estos cinco valores:

> **¿Son los valores que defenderías en una entrevista, o son los míos?**

**Sigue sin contestarse uno a uno.** Lo que hubo fue la orden de cerrar la puerta,
que es **una decisión de proceso**, no una respuesta sobre el contenido.

**Qué hace falta para que dejen de ser valores de trabajo** —y es poco—:

1. **Recorrer los cinco y decir «sí» o «cambio esto por esto»** sobre cada uno.
2. **Para DN-05 y DN-06, decir de dónde sale el número**, aunque sea «es una
   estimación razonable de alguien que conoce el dominio». **Hoy no sale de
   ninguna parte, y eso es lo que está declarado.**
3. **Anotarlo aquí, con quién lo dijo.** Sustituir la línea «Erick no revisó este
   valor» por la que corresponda.

**Mientras eso no ocurra, estas cinco decisiones se citan como valores de trabajo
adoptados y no validados** — nunca como reglas del negocio, y nunca como
requisitos derivados de la norma.

---

## 6 · Cómo leer las marcas

| Marca | Significa |
|---|---|
| `[V]` | Verificado contra una fuente que se puede citar |
| `[A]` | Asumido o decidido, sin fuente externa que lo respalde |
| `[NV]` | No verificado, y se dice en vez de darse por bueno |
