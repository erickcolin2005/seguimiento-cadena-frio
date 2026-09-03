# Tanda 0 · Lectura externa del planteamiento — **NO MEDIDA**

> **Desenlace: NO MEDIDO.** No hubo lector externo. Ni V-1 ni V-2 se ejecutaron.
>
> Esto no es un trámite cumplido. **Es una deuda abierta, y este documento existe
> para que siga siendo visible mientras lo esté.**

La regla que gobierna este documento es exacta: **no se exige que haya lector; se
exige que conste qué pasó** `[V — condición CE-1, puerta G3]`. Lo que no se
permite es el silencio. Aquí consta.

---

## 1 · Qué es la tanda 0

La tanda 0 son **dos comprobaciones sobre una misma conversación**, con **una sola
persona que no es el autor**, hechas **antes de que exista código**:

| # | Qué comprueba | Cómo se hace | Estado |
|---|---|---|---|
| **V-1** | Que un lector externo **nombra el problema sin ayuda** después de leer el README | Se le pregunta *«¿qué problema resuelve esto?»* y **se transcribe la respuesta sin corregirla** | **NO MEDIDO** |
| **V-2** | Que un lector externo **sabe qué esperaría ver** y por dónde entraría | Misma conversación, mismo lector | **NO MEDIDO** |

**V-1 es la única medición del retorno principal del proyecto** `[V]`. También es
la más barata de todas: cuesta pedírselo a una persona.

---

## 2 · Qué se iba a preguntar, literalmente

Se deja escrito para que, si mañana aparece un lector, **la pregunta no se
improvise ni se filtre a favor del autor**:

**Para V-1** — se entrega el README y nada más. Sin introducción hablada, sin
contexto previo, sin «te explico rápido de qué va».

1. *«¿Qué problema resuelve esto?»*
2. *«¿Te parece un problema difícil, o te parece el comportamiento por defecto de
   una herramienta que ya conoces?»*
3. *«¿Qué frase de este texto no te crees?»*

**Para V-2** — a continuación, con el mismo lector.

4. *«Si quisieras comprobar por ti mismo que esto es cierto, ¿por dónde
   entrarías?»*
5. *«¿Qué esperarías ver si funcionara? ¿Y si no funcionara?»*

**La regla de transcripción, que es la mitad del valor:** la respuesta se copia
**tal como se dice**, incluidas las que dejan mal al planteamiento, las confusas y
las que no contestan la pregunta. **Una respuesta corregida mide al corrector, no
al lector.**

---

## 3 · Por qué tiene que ser alguien que no es Erick

**Porque el autor ya sabe la respuesta, y por eso no puede darla.** V-1 no mide si
el problema está bien planteado en la cabeza de quien lo planteó; **mide si el
planteamiento sobrevive fuera de esa cabeza.**

Tres consecuencias concretas:

1. **El único fallo que V-1 detecta es invisible desde dentro.** Un texto puede ser
   perfectamente claro para quien conoce el contexto y completamente opaco para
   quien no. **Quien lo escribió no puede distinguir los dos casos**, porque no
   puede dejar de saber lo que sabe.
2. **El riesgo declarado del proyecto es exactamente no distinguirse** `[V]`. «Usé
   la herramienta» y «entiendo la herramienta» **se ven idénticos desde fuera**. El
   único que puede decir si se distinguen es alguien que mira desde fuera.
3. **Es el mismo principio que el proyecto aplica a su propia medición:** el
   testigo no puede ser la víctima, y el guardia que se compara consigo mismo no
   compara con la realidad `[V]`. **Un autor que se autoevalúa el encuadre está
   cometiendo, sobre el texto, el error que el proyecto entero existe para evitar
   sobre el software.**

---

## 4 · Qué se pierde por no haberlo hecho

Sin adornos, y en orden de gravedad:

1. **El retorno principal queda sin medir.** No hay ninguna otra comprobación en el
   proyecto que diga si el proyecto sirvió para lo que existe. Que la futura
   medición técnica salga bien **no responde esta pregunta**: diría que el software
   cumple, no que el planteamiento comunica.
2. **Se pierde la ventana barata.** La refutación tiene precio creciente: aquí
   cuesta reescribir un texto; con el dominio ya construido cuesta reescribir
   código; más adelante cuesta rehacer la medición. **La tanda 0 era el momento más
   barato del proyecto entero para descubrir que el encuadre no se entiende, y ese
   momento no se recupera: se puede repetir la pregunta, pero ya no será antes de
   que exista código.**
3. **Sigue sin comprobarse la única hipótesis que sostiene el resto.** Que la
   afirmación del README le parezca difícil a alguien competente es un supuesto
   `[A]`, no un hecho. Si a un lector externo le pareciera trivial, **cambiaría el
   problema con nombre**, y con él buena parte de lo que hay planificado detrás.
4. **Sería el tercer proyecto consecutivo del portafolio afirmando una señal que
   nadie comprobó** `[V — lleva dos de dos]`. Este documento no arregla eso.
   **Lo hace imposible de olvidar.**

---

## 5 · Cómo se cierra más adelante sin dejar de ser honesto

**La oportunidad sigue viva.** El plan vuelve a exigir V-1 en el tramo que produce
el README completo (M10) `[V — plan de trabajo, PL-5]`, y ahí se repite sobre un
texto mucho más grande. Para que ese cierre valga y no sea un maquillaje, se fijan
aquí **cinco condiciones**, antes de saber el resultado:

1. **Esta declaración no se borra ni se sustituye.** Si más adelante hay lector, su
   transcripción **se añade** a este documento como tanda 1. La tanda 0 seguirá
   diciendo NO MEDIDA para siempre, porque eso es lo que pasó.
2. **La transcripción va sin corregir**, incluida la respuesta mala, la vaga y la
   que no entiende nada. Si no hay respuestas incómodas en una transcripción,
   probablemente se editó.
3. **Sin cebar al lector.** Nada de explicar antes de que lea. El lector lee y
   responde; el autor calla y anota.
4. **Se dice qué mide la tanda tardía, que no es lo mismo que medía esta.** Una
   lectura hecha cuando ya existe software responde *«¿se entiende este proyecto?»*.
   **La tanda 0 respondía otra cosa: «¿aguanta este planteamiento antes de que
   cueste algo?»**. Esa segunda pregunta ya no se puede contestar, y presentar la
   respuesta tardía como si la contestara sería exactamente el tipo de sustitución
   que este proyecto persigue en el software.
5. **Si tampoco entonces hay lector, se vuelve a declarar NO MEDIDO por escrito y
   se publica igual.** No bloquea nada. **Lo único prohibido es callarlo.**

---

## 6 · Quién sostiene esta deuda

| | |
|---|---|
| **Dueño** | **Erick.** Es suya la condición CE-1 y suya la decisión de quién es el lector |
| **Decisión abierta** | *¿Quién es el lector externo?* Sigue **sin cerrar**. Es la decisión abierta más barata del proyecto y la que más veces se ha dejado sin cerrar `[V]` |
| **Qué bloquea** | **Nada.** Y ese es justamente el motivo por el que lleva dos proyectos sin hacerse |
| **Estado** | **Abierta.** No se marca como resuelta por el hecho de estar documentada |

---

## 7 · Avisos del `product-agent` sobre los documentos de análisis

Esta sección **no corrige nada en su origen**: son recomendaciones para quien
mantiene los documentos de análisis, escritas aquí porque el encargo prohíbe
editarlos desde este tramo.

### A-1 · V-2 no es contestable en su forma plena en la tanda 0

V-2 está definido como *«un lector externo encuentra el comando y sabe qué
esperaría ver»* `[V — visión de producto §4.1]`. **En este punto no hay comando**,
porque no hay código: es la condición del tramo. La forma que la tanda 0 admite es
la degradada de §2 —*por dónde entrarías, qué esperarías ver*—, y **eso no es lo
mismo que V-2**.

**Recomendación:** que la visión de producto distinga **V-2 en tanda 0** de **V-2
plena**, o que el plan diga cuál de las dos exige su comprobación 3. Hoy no
bloquea, porque el desenlace es NO MEDIDO en ambas lecturas; **si mañana aparece un
lector, sí hay que saber qué se le pregunta.**

### A-2 · «Ordenó cerrar» no es «validó los valores», y el elemento M0 no los distingue

El elemento M0 lista *«cierre de los valores DN con Erick»* `[V]`. Lo que ocurrió
fue que **Erick ordenó cerrar la puerta; no revisó los valores uno a uno**. M0
queda por tanto **cerrado en su forma administrativa y abierto en su forma
sustantiva**.

**Recomendación:** que el estado de M0 registre esa diferencia. Aquí se registra en
`decisiones/decisiones-de-negocio.md`, que es donde tiene consecuencias.

### A-3 · La frase de cabecera de la visión de producto contiene una frase prohibida

La condición CE-5 prohíbe que **ningún artefacto** afirme cierta clase de
propiedad estructural antes de que exista el tramo que la compra `[V]`. **La frase
de «en una frase» de la visión de producto contiene literalmente una de esas
expresiones, en presente y en la línea más copiable del documento.**

No es un fallo de ese documento hacia dentro —es análisis interno, y su §7.4
declara la prohibición correctamente unas páginas después—, pero **es la frase con
más probabilidad de acabar copiada tal cual en un README, en un titular o en una
publicación**, que es precisamente el modo de fallo que CE-5 describe.

**Recomendación:** marcar esa línea en el origen como *«no publicable hasta M11»*,
o reescribirla en presente honesto. **Este README no la usa, y por eso rodea la
palabra «eventos» con una nota de desambiguación explícita.**

### A-4 · El disparador del riesgo de V-1 no se activa, pero el riesgo sí está vivo

El riesgo registrado dispara si el tramo termina **sin transcripción y sin
declaración escrita** `[V]`. Con esta declaración, **el disparador no se cumple**.
**El riesgo, en cambio, se ha materializado entero:** el retorno principal sigue
sin medirse. **Marcar el riesgo como controlado porque existe este fichero sería
confundir el registro con la medición** — y es la misma confusión que el proyecto
combate en su parte técnica.

### A-5 · Publicar la ausencia en el README es decisión mía `[A]`

El plan exige que la ausencia **conste**; no dice **dónde**. Se publica también en
el README, además de aquí, porque **una ausencia que solo vive en un fichero de
evidencia no la ve el lector externo, y el lector externo es el punto**.
