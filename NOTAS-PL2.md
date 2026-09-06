# Notas de PL-2 · la rebanada vertical

Qué quedó funcionando, qué mide cada comprobación y —sobre todo— **qué NO
permite afirmar este tramo**. Se escribe porque un verde sin su letra pequeña se
lee como más de lo que es.

Marcas: `[M]` medido ejecutando · `[V]` verificado · `[A]` asumido · `[NV]` no
verificado.

---

## 1 · Qué quedó funcionando

```
python levantar.py     los dos servicios en pie, con los almacenes vacíos
python comprobar.py    las siete comprobaciones de PL-2
```

Cuatro procesos y dos ficheros. **Ni un demonio, ni una cuenta, ni un secreto,
ni una imagen.** Biblioteca estándar y nada más.

| Pieza | Qué es |
|---|---|
| **EM** | El emisor. Recorre el guion en orden de producción y se lo da a SV-1 |
| **SV-1** | El núcleo de reglas, la bandeja de salida y su drenaje. **El proceso que muere** |
| **SV-2** | El testigo: el libro de acciones y el recuento. **El proceso que no muere** |
| **IN** | La calculadora de referencia, sobre el guion y nunca sobre el sistema |
| **AL-1 / AL-2** | Dos ficheros SQLite, uno por servicio, sin nada que los cruce |

**Las reglas no están aquí.** SV-1 importa `banco`, que es el mismo código que
los 64 casos ejercen y que la mutación apaga pieza a pieza. Una segunda
implementación produciría *la regla escrita dos veces con media viva* —el defecto
real que la mutación estricta encontró en P4— y ninguna de las dos copias
quedaría cubierta.

## 2 · La corrida, con sus números

`python comprobar.py` → **VERDE, código 0** `[M]`. Las siete pasan.

| # | Comprobación | Lo que se midió |
|---|---|---|
| 1 | Un solo comando en máquina limpia | Los dos almacenes se crean **vacíos**; los dos servicios responden `/salud`; **todo lo que se arranca es el propio intérprete** |
| 2 | El camino entero | **100 lecturas → 4 entradas en bandeja → 4 entregadas → 4 contadas**, y el conjunto de ternas **coincide con la referencia** |
| 3 | La referencia sobre el guion | Se ejecuta **con SV-1 apagado**, código 0; y **se niega** si el digesto no es el de su guion |
| 4 | El recuento fuera del que muere | Con SV-1 detenido y su puerto cerrado, `GET /recuentos` sigue dando **4** |
| 5 | SEC-1 (i) y (ii) | Los **tres desenlaces distinguibles**; ni la repetición ni el rechazo mueven el recuento |
| 6 | Semilla y digesto | Misma semilla → mismo digesto; otra semilla → otro; el par queda escrito en el almacén |
| 7 | Fronteras reales | Dos ficheros, **ninguna tabla compartida**, **ninguna clave foránea que cruce**, y ningún servicio con camino para abrir el almacén del otro |

**El detalle que enseña que el mecanismo funciona, y no solo el camino:** SV-1
reevalúa cada lote **en cada lectura**, así que propuso el mismo hecho actuable
muchas veces. La bandeja acabó con **cuatro** entradas. Quien dedujo no fue una
memoria de proceso —esa muere con él— sino **la clave primaria de la terna**.

---

## 3 · Lo que este tramo NO permite afirmar

**Nada de C1.** Ni la mitad de orden ni la mitad de cardinalidad.

- **Ningún proceso muere entre decidir y registrar.** En la comprobación 4 se
  mata a SV-1 **después** de drenar y en un punto tranquilo, para enseñar que el
  recuento vive fuera de él. Matarlo en el peor instante y contar qué pasa es
  **PL-3**.
- **El orden no se ha tocado.** El emisor entrega en orden de producción. No hay
  desorden, no hay reconstrucción y no hay nada que medir todavía.
- **La durabilidad frente a la muerte del proceso no está medida** `[NV]`. Se usa
  `PRAGMA synchronous = FULL`, que es una decisión, no una medición. Quien lo
  mide es VB-1 en PL-3, y **puede tirar el tramo abajo**.

## 4 · Cuatro cosas declaradas, en vez de dadas por cubiertas

**El servidor es de un solo hilo, a propósito** `[V]`. Hace el camino
reproducible, y la consecuencia se dice: **el control de concurrencia optimista
por versión (ADR-03) queda sin ejercitar en PL-2.** No está roto — está sin
probar, que no es lo mismo, y no es lo mismo que estar bien.

**La ventana del puerto** `[A]`. El instrumento pide un puerto que el sistema
declara libre y se lo pasa al hijo. Entre las dos cosas hay una ventana en la que
otro proceso podría tomarlo; si ocurre, el hijo no arranca y se ve. La ventana es
estrecha y **no se cierra aquí**.

**Dos campos nuevos en el banco, y por qué no perturban su medición.** El almacén
exige RC-08 en **dos columnas** —un único `no_apto` haría indistinguible apagar
el umbral de apagar la irreversibilidad—, y la conclusión del banco las colapsaba
en `aptitud`. Se añadieron `umbral_superado` e `irreversible_activa`, **sin
cambiar el significado de ninguna regla** y **sin meterlas en la representación
que se compara**: son derivables de `aptitud` y `acumulado`, que ya estaban ahí,
así que no añaden información al digesto y sí habrían movido la mutación.
Comprobado: `python ejecutar.py` sigue en **VERDE con las cuatro condiciones
13/13** `[M]`.

**Un defecto de la comprobación 1, cazado antes de publicarla.** La primera
versión buscaba la palabra «docker» en el texto de `levantar.py` — y la
encontraba, en la línea que informa de si está en el `PATH`. Daba **rojo sobre
código correcto**. Se sustituyó por lo que de verdad importa: recorrer el árbol
sintáctico y exigir que **todo arranque de proceso empiece por el propio
intérprete**. *Un raspado de cadenas es como se pierde la confianza en una
comprobación barata.* Lo que esa comprobación **no** ve —una forma de arrancar
procesos que no esté en su lista— está declarado en el código, junto a la lista.

## 5 · El orden de arranque no es casual

**SV-2 primero.** El testigo tiene que estar en pie antes de que exista nada que
atestiguar. Al revés, SV-1 podría decidir un hecho actuable sin que hubiera nadie
a quien contárselo — y la bandeja de salida existe justamente para que eso no se
pierda, pero **probarlo es PL-3, no esto**.
