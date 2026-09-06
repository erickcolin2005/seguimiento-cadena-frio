# Notas de PL-3 · C1 cerrado, medido y calibrado

La parada más peligrosa del plan, y por qué su verde significa algo. Marcas:
`[M]` medido ejecutando · `[V]` verificado · `[A]` asumido · `[NV]` no verificado.

---

## 1 · El veredicto

```
python veredicto.py
```

**APROBADO**, código de salida 0 `[M]`. La salida completa está en
`evidencia/pl-3/veredicto-aprobado.txt`.

| | |
|---|---|
| **C1-A** · divergencias contra la referencia | **0** sobre **440 inversiones decisivas**, 7 envíos, **5 de 5 clases** |
| **C1-B** · hechos con 0 acciones · con ≥2 · sobre hechos no actuables | **0 · 0 · 0** sobre **56 hechos** y **56 muertes** |
| **Entregas repetidas absorbidas** | **28** |
| **Calibración** | C1-A: 18 divergencias con el mutante · C1-B: 28 + 28 anomalías |

---

## 2 · Las siete comprobaciones del tramo

| # | Qué pedía | Resultado |
|---|---|---|
| **0** | **VB-1 pasa** y su salida queda guardada | ✅ `python -m sistema.vb1` |
| **1** | C1-A: 0 divergencias · ≥30 decisivas · ≥5 envíos · ≥3 clases | ✅ 0 / 440 / 7 / 5 |
| **2** | C1-B: exactamente 1 · ≥50 muertes · ≥50 hechos · ≥20 en ventana | ✅ 56 / 56 / 56 anomalías |
| **3** | Calibración con **DOS** mutantes · omitirla **no puede** dar APROBADO | ✅ y demostrado: `veredicto-sin-calibracion.txt` sale **INVÁLIDA** |
| **4** | Al menos una corrida provocada inválida, con su salida guardada | ✅ dos: `veredicto-sin-calibracion.txt` y `veredicto-invalido-mi1.txt` |
| **5** | SEC-5: veredicto con SV-1 detenido, B-2 marcada no comprobada | ✅ |
| **6** | Salida DP-02: veredicto primero, denominadores siempre, MI con su motivo | ✅ |

## 3 · VB-1 iba primero, y por qué

**Si el compromiso del almacén no fuera duradero frente a la muerte del proceso,
`PS-A` no estaría donde el diseño dice y todo lo medido después mediría otra
cosa.** Se comprueba en dos mitades, porque una sola no decide nada:

- **(A) durabilidad** — 25 filas comprometidas, `kill()` por la vía más brusca de
  la plataforma, y las 25 se releen **en un proceso nuevo** `[M]`.
- **(B) atomicidad** — 25 filas escritas **sin** comprometer, mismo `kill()`, y no
  sobrevive ninguna `[M]`.

Con (A) sola pasaría un almacén que escribe siempre y nunca deshace; con (B)
sola, uno que no escribe nunca.

**Lo que VB-1 no mide, declarado:** la muerte de la **máquina**. Un corte de
corriente o un pánico del sistema operativo no están cubiertos `[NV]`.

## 4 · C1-A · los dos denominadores, y por qué nunca se publica uno

**Inversiones observadas: 1248. Inversiones decisivas: 440.** El denominador es
el segundo. Barajar lecturas que no cruzan ningún umbral no cambia nada: 808 de
esos pares no cambian ninguna conclusión por sí solos, y publicar el 1248 sería
publicar algo que no se midió.

Una inversión es decisiva si, **procesada tal como llega**, produciría una
conclusión distinta. Se comprueba **par a par y de una en una**: se parte del
orden real, se intercambian esas dos lecturas y solo esas, y se evalúa con el
modelo ingenuo —el de un sistema que trata la posición de llegada como el
instante en que ocurrió—.

**Una inversión puede caer en varias clases.** Se cuenta una vez en el total y
una vez en cada clase, así que la suma por clases (922) es mayor que el total
(440). Sumarlas sería inventarse un tercer número. Hay además **1 decisiva que
ninguna de las cinco clases nombra**, y se declara en vez de repartirla.

### El defecto que C1-A encontró, y era del sistema

La primera corrida salió **FALLO con 18 divergencias**. `SV-1` tomaba como
instante de decisión la producción de **la lectura recién llegada**, así que una
lectura tardía y antigua hacía **retroceder la conclusión**: el sistema olvidaba
lo que ya sabía. Eso es depender del orden de entrega, que es justo lo que la
afirmación dice que no pasa. El instante de decisión pasa a ser **la marca de
agua del envío**, derivada del prefijo persistido y monótona por construcción.

## 5 · C1-B · la ventana no se observa, se refuta

La ventana es el intervalo entre que la decisión **queda comprometida** y que su
efecto **queda registrado en el receptor**. Por definición, ahí la decisión **no
ha dejado rastro donde se cuenta**: preguntarle al receptor si la muerte cayó
dentro no sirve, porque si hubiera rastro no habría ventana.

Por eso la misma tanda de 56 muertes se corre **tres veces**:

| Tanda | Qué es | Qué pasó `[M]` |
|---|---|---|
| **El sistema** | Bandeja de salida + receptor idempotente | **56 acciones para 56 hechos** |
| **M-1 · marca antes de enviar** | Marca la entrada entregada *antes* de entregarla | **28 hechos con CERO** |
| **M-2 · receptor no idempotente** | La terna deja de ser clave en el receptor | **28 hechos con DOS** (84 acciones) |

**Hacen falta los dos.** Con uno solo se demostraría que la tanda alcanza una de
las dos formas de romperse y la otra quedaría sin ejercer.

**Las 28 entregas repetidas absorbidas son la prueba de que el mecanismo
trabajó**: son las muertes posteriores al envío, donde el receptor ya había
registrado y SV-1 murió antes de anotarlo. Al revivir reenvía —no puede saber
que ya llegó— y la terna hace que el efecto siga siendo uno.

### Dos defectos del instrumento, cazados antes de publicar nada

**El bucle que medía otra cosa.** La tanda mataba en **cada** intento de entrega,
así que ninguna entrada llegaba a marcarse entregada y la bandeja no se vaciaba
nunca. Eso no mide *«se actúa exactamente una vez»*: mide *«no se llega a actuar
nunca»*. Ahora es **una muerte por hecho actuable**, apuntando a la terna, y
después se le deja terminar.

**El mutante que no estaba mutado, y es el que más preocupa.** `crear_almacenes`
creaba la tabla del receptor con el esquema normal **antes** de arrancar SV-2, y
`CREATE TABLE IF NOT EXISTS` no toca una tabla que ya existe: la clave primaria
de la terna seguía puesta y **M-2 corría sin mutar, en silencio**. Lo delató que
diera exactamente **0** anomalías. *Si hubiera dado una o dos por casualidad, se
habría leído como poca sensibilidad y la calibración habría quedado inútil sin
que nadie lo notara* — con el 56/56 pareciendo significar algo que no significaba.

## 6 · SEC-5 · el veredicto sin el proceso que muere

Es una prueba negativa barata sobre RF-10: **si el veredicto no se pudiera emitir
sin SV-1, el recuento viviría donde no debe.** Medido `[M]`: SV-1 detenido, su
puerto ya no acepta conexiones, y el veredicto sale completo.

El número sale **solo** de `GET /recuentos`, que es de SV-2. `GET /bandeja`
existe y es legítimo, **pero solo para B-2**: contar ahí está prohibido, porque
pondría el recuento en la víctima. Y no se afirma de palabra — se recorre el
árbol sintáctico del propio veredicto y **se publican las rutas que pide**.

**B-2 sale `NO SE PUDO COMPROBAR`, con esas palabras.** No omitida, no asumida.
Cruza la frontera entre los dos almacenes, y si un motor pudiera imponerla sería
porque los dos almacenes son uno — que es lo que RF-10 prohíbe—. Su
indisponibilidad **no invalida la corrida**, pero **un aprobado con líneas sin
comprobar es más débil y tiene que verse**.

## 7 · Las dos corridas inválidas a propósito

Un instrumento que no puede negarse no mide nada, así que se le hizo negarse:

| Fichero | Qué se rompió | Desenlace |
|---|---|---|
| `veredicto-sin-calibracion.txt` | Se omite la calibración **y solo eso** | **MEDICIÓN INVÁLIDA**, código 2 |
| `veredicto-invalido-mi1.txt` | Guion por debajo de todos los umbrales | **MEDICIÓN INVÁLIDA**, código 2 |

La primera es la que importa: **su única falta es la ausencia de calibración**.
Todo lo demás pasó, el sistema estaba bien, y aun así no es un aprobado. Eso es
T-23 leído estricto — *la ausencia de calibración no es un aprobado con
reservas*.

## 8 · Lo que esta corrida NO permite afirmar

- **Nada sobre ningún mecanismo que no sea el medido.** La salida lo dice en su
  propia cabecera: **C1 medido sobre un mecanismo directo**. Cualquier otra
  formulación tendría que esperar a que ese otro mecanismo exista y se mida.
- **Nada fuera de C1.** No hay carga, no hay concurrencia externa y no hay lector
  externo. El servidor sigue siendo de un solo hilo, así que **el control de
  concurrencia optimista por versión sigue sin ejercitarse** — no roto: sin
  probar.
- **Nada sobre la muerte de la máquina** `[NV]`, solo sobre la del proceso.
- **Nada sobre si los valores del dominio son los correctos.** El sistema aplica
  el valor declarado; que ese valor sea el que el negocio defendería es otra
  pregunta, y sigue abierta.
