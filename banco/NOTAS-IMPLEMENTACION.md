# Notas de implementación del banco · PL-1

Lo que esta corrida encontró y **no** arregló por su cuenta, más lo que sí
arregló y por qué. Se escribe aquí porque un hallazgo que solo vive en la cabeza
de quien lo encontró no es un hallazgo.

Marcas: `[M]` medido en esta corrida · `[V]` verificado ejecutando ·
`[A]` asumido, no verificado.

---

## 1 · El desenlace de PL-1 es INVÁLIDO, y es lo correcto

`python ejecutar.py` termina con **código 2 · INVÁLIDO**. No es un verde y no es
un rojo.

| | |
|---|---|
| 64 casos ejecutados, 61 atribuibles a una regla | **64 pasan, 0 fallan** `[M]` |
| Criterio 1 · determinismo | **PASA** `[M]` |
| Criterio 2 · ninguna conclusión sin nombrar su regla | **PASA** `[M]` |
| Criterio 3 · (a) sensibilidad | **13/13** `[M]` |
| Criterio 3 · (b) discriminación | **13/13** `[M]` — *con la redacción vigente; con la anterior, 0/13. Ver el recuadro de §2* |
| Criterio 3 · (c1) localización | **13/13** `[M]` |
| Criterio 3 · (c2) extensión de la cascada | **NO EVALUABLE en las 13** — falta `cascada_declarada` `[M]` |
| Criterio 4 · `tipo_producto` vive en el lote | **PASA** `[M]` |
| Criterio 5 · un solo comando, sin dependencias | **PASA** `[M]` |

Lo que falla no es el banco: es que **la condición (c) no se puede evaluar con
el mapa de mutación vigente**. Publicar eso como rojo diría que el código está
mal, y no lo está. Publicarlo como verde diría que la condición se comprobó, y
no se comprobó. Por eso hay un tercer desenlace.

---

## 2 · El hallazgo: las listas de §8 no llevan cláusula de cascada

**Qué se midió** `[M]`. Al apagar una pieza, nueve de las trece hacen caer casos
que no están en su lista de `banco-reglas-cadena-frio.md §8`. «Caer» aquí
significa *cambiar de valor*, no *quedarse sin regla*: los casos que solo pierden
el identificador porque la pieza apagada era la que lo ponía se descartan como
eco y no cuentan.

| Pieza apagada | Casos en su lista | Casos de fuera que **cambian de valor** |
|---|---|---|
| RC-04 | 4 | **45** |
| RC-06 | 4 | **25** |
| RC-09 | 9 | **17** |
| RC-05 | 5 | **11** |
| RC-08-umbral | 6 | **10** |
| RC-12 | 2 | 5 |
| RC-10 | 5 | 3 |
| RC-01 | 2 | 2 |
| RC-02 | 7 | 1 |
| RC-03 · RC-07 · RC-08-irreversibilidad · RC-11 | — | **0** |

Las listas completas se imprimen en cada corrida; no hay que fiarse de esta
tabla.

**Por qué pasa.** La explicación no es que el código esté mal, es que el dominio
encadena. Apagar RC-04 significa que ninguna lectura queda fuera de rango; sin
lecturas fuera de rango no hay excursiones; sin excursiones no hay acumulado, ni
pérdida del lote, ni clase de acción, ni hecho actuable que registrar. Cuarenta y
cinco casos cambian de valor porque **el dominio es así**, no porque la
implementación se desborde.

**De dónde salió.** El banco decía en su origen, para RC-04:
`L-03…L-09, A-03, y toda la cadena de excursión`. Al cerrar el hallazgo EX-3 se
quitaron de esas listas los casos permisivos —correcto, porque un desenlace
permisivo no cambia cuando se apaga una regla que restringe— **pero se fue con
ellos la cláusula de la cascada**. Las listas pasaron de sobre-inclusivas a
sub-inclusivas para las reglas que están al principio de la cadena causal. EX-3
arregló un extremo y destapó el otro.

**Qué NO se ha hecho, a propósito** `[V]`. No se ampliaron las listas, no se tocó
el clasificador de eco y no se relajó la condición (c). El banco es de
`analyst-agent` y el criterio de mutación es de `qa-agent`; ajustar el código
hasta que salga verde destruiría exactamente la señal que este tramo existe para
producir.

**Lo que queda por decidir, y no lo decide este tramo.** Si la condición (c) se
enuncia sobre la caída directa o sobre la caída directa más su cascada, y en el
segundo caso cómo se escribe la cascada en el mapa sin que la lista se vuelva
«todos los casos». `[A]` — y esto es una sospecha, no una medición: los números
grandes (45, 25, 17, 11, 10) parecen cascada pura, mientras que los pequeños
(5, 3, 2, 1) **podrían** además contener omisiones reales de la lista. No se
comprobó caso por caso cuál es cuál.

> ### RESUELTO por `qa-agent` · reapertura de `cinturon-calidad.md` §4.4
>
> **La pregunta de arriba tenía un supuesto falso, y el supuesto era mío al
> escribir el criterio, no de este tramo.** La lista de `banco §8` dice *«casos
> que **deben** caer»*: es un **límite inferior**. La condición (a) la usa así y
> funciona. **La condición (c) la usaba además como límite superior**, y una
> misma lista no puede ser suelo y techo a la vez. **Ampliarla con la cascada
> era la salida equivocada**: la de RC-04 pasaría a 47 de 64 casos y (c) sería
> trivialmente cierta. **§8 no se toca.**
>
> **Qué se hizo, y está en `mutacion.py`:**
>
> * **(b)** se retira *«y con ninguna otra»*. Se exige que el discriminante
>   caiga **y** que su conclusión con esa pieza apagada sea **distinta de la de
>   las otras doce**. Razón medida: la redacción literal daba **0/13 sobre el
>   código correcto y 0/13 sobre el código defectuoso** — no separaba los dos
>   estados del mundo. La nueva da **13/13** y **roja exactamente en las dos
>   mitades de RC-08 cuando se fusionan** `[M]`.
> * **(c)** se parte. **(c1) localización**: todo caso que cambia de valor tiene
>   que ser un caso donde la propia regla de la pieza dejó de firmar algo.
>   **13/13** `[M]`, sin usar §8 y sin dato nuevo. **(c2) extensión**: hasta
>   dónde llega la cascada — **NO EVALUABLE**, porque exige la relación
>   regla→regla y el banco no la declara.
> * **Los tres controles quedan fuera de (c)**, como `cinturon-calidad.md` §4.4
>   punto 1 ya decía desde G3 y el código no implementaba: eran **6 entradas**
>   contadas de más (X-05 y X-06 en RC-04, X-05 en RC-05, X-05 y X-06 en RC-09,
>   X-06 en RC-10) `[M]`. Por eso las cifras de la tabla de arriba pasan a
>   43, 25, 15, 10, 10, 5, 2, 2, 1.
> * **Los dos dientes** —fusionar RC-08 y fabricar un acoplamiento RC-10→RC-03—
>   corren en cada corrida y se publican. Si una condición no se puede poner
>   roja, la corrida es **ROJA por defecto del cinturón**.
>
> **El orden numérico de §3 NO sirve de sustituto de la cascada, y está medido,
> no supuesto** `[M]`: marca contaminación falsa en **RC-06** (7 casos, vía
> RC-05) y en **RC-12** (1 caso, vía RC-07, RC-09 y RC-10). El propio banco lo
> dice dos veces (§3 y §7): el número es orden de **evaluación**, no de
> dependencia.
>
> **La sospecha de arriba —que los números pequeños escondieran omisiones reales
> de la lista— queda sin efecto**, no resuelta: con §8 leída como límite
> inferior, caer fuera de la lista **no es un defecto por sí solo**, así que no
> hay nada que separar. Lo que sí queda medido es que **(a) se cumple 13/13**,
> es decir que ningún caso listado sobrevive.
>
> **El desenlace sigue siendo INVÁLIDO**, con un motivo más estrecho: **falta
> `cascada_declarada` en `mapa-mutacion.json`**, que es un dato de
> `analyst-agent`. El encargo exacto está en `cinturon-calidad.md` §9.

---

## 3 · Un defecto de modelado, encontrado y corregido

`cerrada_en` llevaba dos cosas distintas en el mismo campo:

* **la conclusión se cerró** porque el lote se entregó — eso lo produce RC-12;
* **hasta dónde se conoce** el prefijo de lecturas — eso lo fija el instante de
  decisión, y ninguna regla lo produce.

El código antiguo hacía dos cosas mal. Cuando el lote no se había entregado,
guardaba el último instante conocido con `regla_cierre_conclusion = None`: un
valor afirmado sin regla que lo nombre, sesenta y ocho veces en la corrida `[M]`.
Y cuando el lote sí se había entregado pero la entrega caía después del instante
de decisión, recortaba el valor hasta ese instante **conservando `"RC-12"`**: una
conclusión atribuida a una regla que no había producido ese valor. El criterio 2
prohíbe las dos: *concluir bien por la regla equivocada también es fallo*.

**Corrección** (`motor.py`, `conclusion.py`, `verificar.py`): el horizonte del
prefijo se va a su propio campo, `conocido_hasta`, que no está en
`REGLA_DE_CAMPO` porque no es un veredicto. `cerrada_en` queda para lo que RC-12
produce, y vale `None` cuando la entrega todavía no ha ocurrido para quien
decide.

La condición se eligió mirando los datos, no razonando en el aire: **A-18** no
tiene instante de decisión y su lote LT-21 se entrega en T0+90 con lecturas hasta
T0+70, y el caso declara que cierra en 90. Así que el horizonte de lecturas no
limita la entrega —la entrega es un hecho del registro del lote, no una
inferencia de las lecturas—; lo que sí la limita es el instante de decisión.

Efecto medido `[M]`: 68 → **0** veredictos sin regla, los 64 casos siguen
pasando, y RC-12 pasa de arrastrar 4 casos a arrastrar 5. Ese quinto (R-02) es
consecuencia del cambio y está contado en la tabla de arriba.

---

## 4 · Tres defectos de las comprobaciones, no del banco

Las tres daban rojo sobre código correcto. Un instrumento que da rojo falso es
tan inútil como uno que da verde falso.

**Determinismo.** La comprobación corre el banco dos veces con dos T0 distintos y
compara. Pero tomaba el digesto de la segunda corrida *después* de restaurar el
T0 original, y el digesto escribe los instantes como desplazamientos desde T0:
la segunda corrida aparecía entera desplazada +7 minutos y los 64 casos
divergían por cómo se comparaba, no por lo que hace el banco. Ahora cada corrida
se digiere con su propio T0 puesto. **Se comprobó que sigue teniendo dientes**
`[V]`: con un campo de la conclusión falseado para que mire `datetime.now()` en
vez de las marcas de las lecturas, la comprobación detecta los 64 casos.

**Umbrales fuera del lote.** La comprobación busca el texto `TIPOS[` en los
módulos para asegurarse de que nadie alcanza los umbrales sin pasar por un lote
— y se encontraba a sí misma, porque ese texto está en su propio código. La
salida fácil habría sido excluirse de la búsqueda, y una lista de exclusiones es
justo el sitio por donde una comprobación se queda ciega. El patrón se arma
partido en dos trozos, y así no hay nada que excluir.

**Dependencias externas.** La comprobación miraba `sys.modules` y encontraba
`_distutils_hack` y `pywin32_bootstrap`, que el intérprete de esta máquina carga
por ficheros `.pth` antes de que corra una sola línea nuestra. No son
dependencias del banco. Ahora se mide sobre las importaciones del código propio,
leídas del fuente con `ast` — y los módulos precargados **se siguen imprimiendo**,
etiquetados como ajenos, porque no mencionarlos sería esconder el entorno.

**Lo que esta última comprobación no detecta, declarado**: un fichero puesto en
el árbol con el nombre de un módulo estándar. Está escrito en el docstring de la
propia función, no solo aquí.

---

## 5 · Lo que esta corrida NO permite afirmar

Que las reglas de cadena de frío viven en el código y se ejecutan: eso sí.

**Nada sobre el orden de los eventos y nada sobre no duplicar acciones.** RC-10
se ejerce aquí como regla de dominio —dos decisiones del mismo hecho actuable son
una acción—, pero en este tramo **no muere ningún proceso**. Las muertes de los
casos X-01…X-07 están modeladas como redecisiones, no como caídas reales. C1-A y
C1-B no se han medido y no se miden aquí.
