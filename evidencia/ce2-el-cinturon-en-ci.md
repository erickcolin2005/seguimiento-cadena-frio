# CE-2 · El cinturón medido en CI, contra los límites citados de su proveedor

> **La condición, literal:** *«En M9 se mide el cinturón completo en CI antes de
> darlo por definido. Si no cabe, excepción firmada, nunca recorte silencioso.»*

**Desenlace: CABE, y con dos órdenes de magnitud de margen.** No hizo falta
ninguna excepción y no se recortó nada.

---

## 1 · Lo medido, en la máquina del proveedor

| | |
|---|---|
| Proveedor | GitHub Actions · `runs-on: ubuntu-latest` |
| Corrida | `cinturon #2`, commit `d93d88c`, rama `main` |
| Conclusión | **verde** |
| **Duración** | **1 min 16 s = 76 s** |
| Qué corrió | El cinturón entero, transporte directo, sin instalar nada |

**Etiquetado por dónde corrió de verdad:** el artefacto crudo deriva su etiqueta
de la variable de entorno del proveedor, no de una constante escrita a mano. Una
corrida etiquetada «CI» porque alguien lo tecleó no dice nada.

## 2 · Los límites, citados literalmente y no resumidos

Esta es la parte que el proyecto exigía antes de admitir **cualquier** cifra de
minutos, precio o nombre de plan. Las citas son textuales.

**De `docs.github.com/en/actions/reference/actions-limits`:**

> *«Each job in a workflow can run for up to 6 hours of execution time. If a job
> reaches this limit, the job is terminated and fails.»*

La tabla atribuye ese límite a **All GitHub-hosted runners**, que es el caso de
este repositorio.

> *«A job can be in the queue for 24 hours before it is automatically
> cancelled.»*

> *«These limits are subject to change.»*

**De `docs.github.com/en/actions/administering-github-actions/usage-limits-billing-and-administration`:**

> *«GitHub Actions usage is free for standard GitHub-hosted runners in public
> repositories, and for self-hosted runners.»*

### Una confusión que estuvo a punto de colarse, y se comprobó

La misma tabla contiene **otro** límite de ejecución: *«Each job in a workflow
can run for up to 5 days of execution time»*. **Su fila dice `Self-hosted`**, no
GitHub-hosted. Tomar ese número habría metido un factor 20 en el margen
publicado. Se comprobó la atribución en vez de copiar la primera coincidencia —
que es el mismo error que este proyecto ya cazó dos veces al raspar texto.

## 3 · El margen, con su denominador

| | |
|---|---|
| Límite del proveedor | 6 h = **21 600 s** |
| Medido | **76 s** |
| **Consumido** | **0,35 %** |
| Coste en minutos facturables | **Ninguno.** El repositorio es público |

**La pregunta que estaba abierta a propósito —«¿cabe en el plan gratuito?»— ya
tiene respuesta, y no es «probablemente».**

Y no cabe por suerte: **cabe porque el repositorio es público**, y esa fue una
decisión, no un accidente. En un repositorio privado la respuesta se mediría
contra una cuota de minutos y podría ser otra.

## 4 · Las dos cifras, etiquetadas y nunca promediadas

| Dónde corrió | Duración | Sistema |
|---|---|---|
| Máquina local del autor | **221,3 s** | Windows |
| Máquina efímera del proveedor | **76 s** | Linux |

**El CI es casi 3× más rápido, y eso NO es una mejora del proyecto.** Son dos
máquinas, dos sistemas y dos costes de arranque de proceso distintos. El
cinturón arranca **168 procesos** por corrida, y crear procesos en Windows es
sustancialmente más caro que en Linux; una corrida de comprobación en Linux
local dio 15,7 s en la etapa del banco frente a 18,2 s en Windows —casi igual—,
así que la diferencia se concentra donde están las muertes.

**Restarlas, promediarlas o quedarse con la menor sería publicar una mejora que
nadie midió.** Van las dos, con su etiqueta.

## 5 · Lo que esta corrida encontró, que es lo que justifica tener CI

**La corrida `cinturon #1` salió ROJA en 9 segundos**, y ese rojo era correcto.

El digesto del banco se calculaba sobre bytes crudos, y de los ocho ficheros del
banco uno tenía CRLF y siete LF. Git entrega CRLF en Windows y LF en Linux, así
que **el digesto de las dos plataformas no podía coincidir jamás**. U-13 no
vigilaba el banco: vigilaba el checkout.

**Ocho tramos de cinturón verde no lo vieron**, porque ninguno corrió fuera de la
máquina del autor. El CI lo encontró en su primera corrida y en nueve segundos.
Está arreglado en `d93d88c`: los finales de línea se normalizan antes de
resumir, porque un final de línea no es contenido del banco.

## 6 · Lo que este registro NO dice

- **No dice que el proyecto entero quepa en CI.** Lo medido es el transporte
  directo, que es lo que el fichero del CI ejecuta. **La medición sobre el otro
  transporte no corre allí**: necesita un intermediario en contenedores que este
  trabajo no levanta.
- **No dice nada sobre repositorios privados.** La gratuidad citada es para
  repositorios públicos y runners estándar.
- **No fija el número como estable.** La propia documentación citada dice que
  *«These limits are subject to change»*, y la duración depende del hardware que
  el proveedor asigne ese día.
- **No mide memoria ni minutos de CPU.** Siguen sin medirse.
