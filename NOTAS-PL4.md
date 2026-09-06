# Notas de PL-4 · el cinturón entero, y su factura

Marcas: `[M]` medido ejecutando · `[V]` verificado · `[A]` asumido · `[NV]` no
verificado.

---

## 1 · Qué quedó funcionando

```
python cinturon.py                              el cinturón entero
python tabla.py evidencia/pl-4/verde/corrida.json   la tabla, desde el artefacto
```

Ocho etapas agrupadas en cuatro pasos, **de la más barata a la más cara**. La
tabla de arriba no está tecleada: se genera desde el artefacto crudo.

## 2 · Las seis comprobaciones del tramo

| # | Qué pedía | Resultado |
|---|---|---|
| **1** | Mutación por regla completa y automática sobre todas las reglas | ✅ 13 piezas × 4 condiciones, dentro de EP-1+2 |
| **2** | El CI ejecuta en cada push: banco + C1-A + C1-B + calibración + mutación | ✅ `cinturon.py` y `.github/workflows/cinturon.yml` |
| **3** | **CE-2 medida**, con el número escrito | ✅ **244,0 s · 168 muertes de proceso** — *y con un hueco declarado, abajo* |
| **4** | Si no cabe: excepción firmada, nunca recorte silencioso | ⚠️ **NO EVALUABLE.** No hay proveedor elegido |
| **5** | Constancia de al menos un rojo real | ✅ `evidencia/pl-4/desenlace-rojo.txt`, código 20 |
| **6** | Número de repeticiones antes de declarar invalidez persistente | ✅ 3 ejecuciones, y solo para causas no deterministas |

## 3 · Los códigos de salida, y por qué no son 0 y 1

```
0   APROBADO
20  FALLO
30  MEDICION INVALIDA
cualquier otro   MEDICION INVALIDA por causa no atribuida
```

**El espacio no reservado es lo importante.** El código 1 lo produce cualquier
excepción no atendida de casi cualquier runtime; el 137, una muerte por falta de
memoria. Si `FALLO` fuera 1, **una excepción del instrumento se leería como «el
sistema perdió una acción»** — y *«la prueba dejó de ejercer el fallo»* no es *«el
sistema perdió una acción»*. Reservar solo los códigos que el proceso **elige**
hace que la confusión sea imposible **por construcción, no por disciplina**.

Para un CI que solo entiende éxito y fallo: **éxito ⟺ código 0 exacto**. FALLO e
INVÁLIDO se representan los dos como fallo, y la asimetría es deliberada.

## 4 · Por qué las etapas van en este orden

| Etapa | Segundos `[M]` | Procesos directos |
|---|---|---|
| EP-0 · el gate de texto | **0,0** | **0** |
| EP-1+2 · banco y mutación por regla | 15,7 | 1 |
| EP-3 · preflight | 0,5 | 1 |
| EP-4..7 · la medición | **227,7** | 1 |

**El 93 % del coste está en la última etapa**, y las tres anteriores existen para
no pagarla en vano:

- **EP-0 no arranca un solo proceso** y aun así puede poner rojo el push entero.
  Un push que va a salir rojo por una frase prohibida no debe pagar cientos de
  muertes antes de descubrirlo.
- **EP-1+2 va antes de medir** porque C1 sobre un sistema al que le falta una
  regla compara dos conclusiones igualmente equivocadas **y sale verde**.
- **EP-3 cuesta una muerte de proceso; la tanda cuesta ciento sesenta y ocho.**
  Comprobar aquí que el compromiso es duradero y que los dos mutantes existen
  evita pagar la medición entera para descubrirlo al final.

## 5 · La auto-guardia, y que muerde

La etapa 0 se lee a sí misma y al fichero del CI, y pone **ROJO** si encuentra
cualquiera de las formas conocidas de anular un veredicto. **Demostrado** `[M]`:
con un `continue-on-error` metido a propósito en el fichero del CI, la corrida
sale **código 20 en 0,0 segundos y 0 procesos**, señalando fichero y línea.

**Y se encontró a sí misma en el primer intento**, porque los patrones estaban
escritos enteros en su propia declaración y en su documentación. La salida fácil
habría sido excluir el fichero de la búsqueda; **una lista de exclusiones es justo
el sitio por donde una comprobación se queda ciega**. Los patrones se arman
partidos en trozos, y así no hay nada que excluir.

**Excepción única y nombrada:** la ejecución incondicional es obligatoria en el
paso que sube la evidencia, porque ahí lo que garantiza es que el INVÁLIDO **se
publique**. Se permite en la publicación; se prohíbe en el veredicto.

## 6 · Ningún reintento por color

FALLO e INVÁLIDO comparten color, así que un reintento automático del proveedor
**reintentaría un FALLO válido** — y un fallo válido no se repite jamás; repetir
un rojo hasta que salga verde es lavarlo.

La política de repeticiones vive **dentro del instrumento**, que lee su propio
motivo: **3 ejecuciones**, y **solo para causas no deterministas**. Medido en la
corrida inválida `[M]`: *«la causa de la invalidez es determinista: repetirla
leería el mismo hueco. No se repite.»*

## 7 · Los tres desenlaces, demostrados

Un pipeline que nunca se ha visto emitir un INVÁLIDO no ha demostrado que pueda.
Y no es una demostración de una vez: **cada vez que el fichero del pipeline
cambia, los tres se vuelven a demostrar**. Estos son de la versión actual:

| Fichero | Cómo se provocó | Código |
|---|---|---|
| `evidencia/pl-4/desenlace-verde.txt` | La corrida normal | **0** |
| `evidencia/pl-4/desenlace-rojo.txt` | `continue-on-error` en el fichero del CI | **20** |
| `evidencia/pl-4/desenlace-invalido.txt` | Se omite la calibración, y solo eso | **30** |

## 8 · CE-2 · lo medido y lo que falta

**Medido `[M]`:** 244,0 segundos de reloj de pared y 168 muertes de proceso, en
esta máquina, con esta versión de Python.

**Lo que ese número NO es, y por eso la comprobación 4 queda abierta:** no son
minutos de un proveedor de CI. **No hay proveedor elegido**, y este proyecto no
admite ninguna cifra de minutos, ningún precio y ningún nombre de plan sin **la
cita literal** de su documentación de límites. En este portafolio ya murió una
premisa exactamente así — *«existe alojamiento gratuito de contenedores»*— y
costó horas.

Por tanto: **la comprobación 4 de PL-4 no es evaluable hoy** `[NV]`. No se declara
cumplida y no se inventa un límite para compararse con él. Lo que hay es el
número de esta máquina y la lista, escrita, de lo que se recortaría primero si no
cupiera — y **C1 y la calibración no están en esa lista**.

**Tampoco medidos** `[NV]`: memoria y minutos de CPU. La biblioteca estándar no
los da de forma portable en esta plataforma, y no se instala nada.

## 9 · Dos defectos que la propia corrida destapó

**La evidencia de una corrida sobrescribía la de otra.** El aprobado y el
inválido escribían en la misma carpeta, así que el artefacto que acompañaba al
verde acabó siendo el de la corrida sin calibración. **La tabla publicada se
genera desde el artefacto crudo; si el crudo no corresponde a su corrida, la
publicación no vale.** Ahora cada corrida tiene carpeta propia.

**«3 procesos» era un número engañoso.** El contador solo veía hijos directos,
pero la medición mata 168 por dentro. Publicar «3» a secas para un cinturón que
provoca cientos de muertes es exactamente el tipo de cifra que este proyecto no
publica. Ahora se leen del artefacto de la medición —del dato, no estimadas— y
**si el artefacto no está, la línea no se imprime en vez de inventarse**.
