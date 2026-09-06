# Notas de PL-5 · publicable, y con la evidencia dentro

El tramo donde **todo el retorno del proyecto pasa por el texto**. Marcas: `[M]`
medido ejecutando · `[V]` verificado · `[A]` asumido · `[NV]` no verificado.

---

## 1 · Las ocho comprobaciones

| # | Qué pedía | Resultado |
|---|---|---|
| **1** | Un extraño levanta todo con un comando y obtiene uno de los tres desenlaces | ✅ `python cinturon.py`, documentado en el README |
| **2** | Evidencia grabada con semilla, digesto, versión y **dónde corrió de verdad** | ✅ y la etiqueta se **deriva del entorno**, no se teclea |
| **3** | La tabla publicada trae los fallos dentro, sin promediar | ✅ se genera con `tabla.py` desde el artefacto crudo |
| **4** | Al menos una MEDICIÓN INVÁLIDA publicada, con su explicación | ✅ dos, en `evidencia/pl-3/` y `evidencia/pl-5/invalido/` |
| **5** | SEC-6 elemento por elemento: los siete en el artefacto | ✅ bloque `sec6` en `corrida.json` |
| **6** | SEC-7 (ii): ninguna ruta personal en el artefacto publicado | ✅ **comprobación mecánica**, con dientes probados |
| **7** | V-1 repetido sobre el README, o declarado no medido | ⚠️ **NO MEDIDO**, por segunda vez. Declarado en `evidencia/tanda-0.md` §8 |
| **8** | Puente con los otros proyectos escrito, con DP-03 aplicado | ✅ README §7, **sin levantar CE-5** |

## 2 · «Dónde corrió» se deriva, no se teclea

La regla es *etiquetada por dónde corrió **de verdad**, nunca por dónde se
suponía*. Por eso el campo no es una constante: se deriva de las variables de
entorno del propio CI. **Una corrida etiquetada «CI» porque alguien lo escribió a
mano no dice nada** — dice lo que el autor creía, que es justo lo que no se
quiere medir.

Y **no lleva ninguna ruta**. Es el campo por el que se cuela una ruta personal
con más naturalidad, y SEC-7 (ii) las prohíbe en lo publicado.

## 3 · SEC-7 (ii) es mecánico, y tiene dientes

No es una inspección que alguien deba acordarse de hacer: **la etapa 0 recorre
toda la evidencia publicable** —contenido incluido, no solo los campos
declarados— y pone rojo si encuentra una ruta personal. Una ruta se cuela igual
de bien en un mensaje de error copiado que en un campo con nombre.

**Probado con rutas metidas a propósito** `[M]`: caza rutas de Windows escapadas
y crudas, `/home/…` y `AppData`. Sobre la evidencia real: ninguna.

## 4 · Los siete elementos de SEC-6, y por qué uno lleva etiqueta

El artefacto trae la lista **cerrada**: si falta uno, SEC-6 no está cumplida. Cada
elemento dice qué es, y **el sexto dice además qué NO es**:

> `entrega_repetida` · **EVIDENCIA DE REINTENTO, NO DE MUERTE EN VENTANA**

Son entregas que llegaron dos veces y contaron una — es decir, **el mecanismo
funcionando**. Leerlas como muertes en ventana convertiría un éxito en un
hallazgo que no existe. La etiqueta va pegada al dato, no en una nota al pie,
porque quien copie el número copiará también la etiqueta.

## 5 · La lista de publicables se deriva

El guardián de CE-5 revisaba una **lista escrita a mano**, y una lista escrita a
mano deja escapar al fichero nuevo: basta con que alguien olvide añadirlo. Ahora
se deriva del árbol.

**Al derivarla aparecieron dos artefactos que nadie estaba vigilando** `[M]`: la
declaración de la lectura externa y el fichero de decisiones de negocio. Los dos
son publicables y ninguno estaba en la lista.

Es la tercera vez en este proyecto que el defecto es *«una lista que hay que
mantener»* — antes fueron dos listas de exclusión— y la respuesta es la misma:
**no mantener la lista, sino no tenerla**.

## 6 · El puente, y lo que el puente NO autoriza

Está en el README §7: de qué fallo concreto salió cada práctica heredada, y por
qué este proyecto **no desplaza** al otro repositorio del portafolio sino que
cubre el eje que aquel declaró que no compraba.

**La regla que importa, y es fácil de romper sin querer:** que la *conversación*
vaya del eje ambicioso **no autoriza al README a afirmarlo**. Son dos cosas
distintas, y confundirlas es exactamente el modo de fallo que el proyecto
persigue en su parte técnica. Hasta que exista el tramo que lo compra, la frase
exacta sigue siendo la de §4d y ninguna otra.

Por eso el puente está escrito **sin usar la expresión reservada ni una sola
vez**, y el guardián automático lo confirma en cada corrida.

## 7 · V-1, otra vez sin medir

**Dos tandas, dos NO MEDIDO.** No hay lector externo, y esta vez sin la excusa de
que no había nada que leer: hay problema, afirmación, medición con sus dos
denominadores, calibración y dos corridas que salieron mal a propósito.

Lo que se declara y no se disimula:

- **La tanda 0 no se sustituye.** Sigue diciendo NO MEDIDA para siempre. La
  tanda 1 **se añade**.
- **La pregunta de la tanda 0 ya no se puede contestar.** Preguntaba *«¿aguanta
  este planteamiento antes de que cueste algo?»*, y ya cuesta. Presentar una
  respuesta tardía como si contestara esa pregunta sería la sustitución que el
  propio documento prohibió por escrito **antes de saber el resultado**.
- **No bloquea nada, y esa es la razón por la que lleva dos tandas sin hacerse.**

## 8 · Lo que sigue sin poder afirmarse

- **Nada sobre ningún mecanismo que no sea el medido.** El eje ambicioso sigue
  sin comprarse.
- **Nada sobre carga ni concurrencia externa.** El servidor es de un solo hilo,
  así que el control de concurrencia optimista **sigue sin ejercitarse** — no
  roto: sin probar.
- **Nada sobre la muerte de la máquina** `[NV]`, solo sobre la del proceso.
- **Nada sobre si los valores del dominio son los correctos.** Lo medido es que
  el sistema aplica el valor declarado.
- **Nada sobre si el planteamiento se entiende desde fuera** `[NV]`. Sigue sin
  leerlo nadie.
