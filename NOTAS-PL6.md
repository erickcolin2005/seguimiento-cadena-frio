# Notas de PL-6 · la costura del transporte, y el tramo que NO está hecho

Marcas: `[M]` medido ejecutando · `[V]` verificado · `[A]` asumido · `[NV]` no
verificado.

> **PL-6 no está terminado, y este documento existe para decirlo con precisión.**
> Lo que se hizo es la parte que no dependía del bloqueo. Lo que falta es la que
> da nombre al tramo.

---

## 1 · Las cinco comprobaciones, y dónde está cada una

| # | Qué pedía | Estado |
|---|---|---|
| **1** | El transporte por eventos sustituye la llamada directa, y el instrumento mata consumidores | ❌ **NO HECHO** — bloqueado, §3 |
| **2** | C1-A y C1-B se vuelven a medir sobre el nuevo transporte, con sus tres modos de fallo | ❌ **NO HECHO** — depende de la 1 |
| **3** | CE-4 registrada: si el costo de la plomería coincidió con lo declarado | ❌ **NO HECHO** — no hay plomería que costar todavía |
| **4** | CE-3 aplicada: toda limpieza de disco comparada contra el inventario | ⚠️ **NO APLICA AÚN** — no se ha tocado el disco. §3 |
| **5** | **Solo aquí se levanta CE-5** | ❌ **NO SE LEVANTA.** Sigue vigente y el guardián sigue activo |

**Cero de cinco.** Lo que sí se hizo es trabajo que las cinco necesitan y que no
dependía del bloqueo: la costura.

## 2 · La costura existe, y ahora significa algo

El diseño afirma que **el transporte no sostiene ninguna garantía**, y que por eso
sustituirlo sería cambiar un adaptador en vez de rediseñar el sistema.

**Hasta ahora eso era una promesa.** La llamada estaba incrustada dentro del
drenaje, así que **no había ningún sitio donde enchufar otro transporte** — y una
afirmación que no se puede intentar romper no está comprobada, solo escrita.

Ahora hay un puerto (`sistema/transporte.py`): un adaptador recibe un hecho
actuable ya comprometido y devuelve el desenlace que el receptor le dio. Nada más.

### Lo que un adaptador NO puede hacer

- **No deduplica.** La unidad de «exactamente una vez» es la terna, que es de
  dominio y no de transporte.
- **No decide si reintentar.** Eso lo decide quien tiene la bandeja.
- **No ordena.** El orden se re-deriva del número de secuencia, y el sistema no
  depende del orden de entrega **ni cuando el transporte lo garantiza**.

### Y no es una promesa: se comprueba por estructura

El preflight del cinturón lee el módulo del transporte y **falla si importa
almacenamiento o reglas** `[M]`:

```
el transporte importa: protocolo
de eso, memoria o reglas: nada
```

**Un adaptador sin memoria no puede deduplicar aunque quisiera.** Si pudiera, la
garantía viviría en él, cambiar de transporte la cambiaría, y el tramo que falta
no sería cambiar un adaptador: sería rediseñar.

### Lo que la costura todavía NO demuestra

**Que sobreviva al cambio.** Hoy hay **un solo** adaptador. La comprobación real
—que la medición completa de C1 dé lo mismo con dos transportes distintos— **no
está hecha, porque el segundo no existe**.

Está declarado en el propio módulo, no solo aquí: *escribir que «el transporte es
intercambiable» sin haber cambiado ninguno sería exactamente la clase de
afirmación que este proyecto no publica.*

## 3 · Por qué está bloqueado, con la medición delante

El transporte por eventos necesita un intermediario corriendo en contenedores, y
**el demonio de contenedores de esta máquina no está en marcha** `[M]`:

```
cliente presente, version 28.5.1
demonio: no responde
disco C: 68 GB libres   ·   disco E: 566 GB libres
```

Arrancarlo es una acción sobre **un entorno compartido con los activos locales de
otro proyecto del portafolio**, y esa condición **tiene dueño, y no es este
tramo**: es de Erick. El inventario de referencia registra **nueve volúmenes**, y
los volúmenes son lo único irreemplazable — las imágenes se vuelven a descargar;
los datos de un volumen, no.

**Lo que no se ha hecho, a propósito:** no se ha arrancado nada, no se ha
descargado ninguna imagen y **no se ha ejecutado ninguna limpieza de disco**. La
condición dice que cualquier limpieza se compara contra el inventario antes y
después, y esa comparación la firma su dueño.

## 4 · CE-5 sigue vigente, y eso es lo correcto

Este es **el único tramo que puede levantarla**, y no está hecho. Así que:

- El README **sigue diciendo** lo que dice hoy, y ninguna otra cosa.
- El guardián automático **sigue revisando los ocho artefactos publicables** en
  cada corrida y poniendo el push en rojo si alguno se adelanta.
- Cuando el tramo se haga, levantarla **no basta con borrar la prohibición**: la
  condición 5 exige que el README diga **sobre qué se midió**, no solo que se
  midió.

**Tenerla vigente no es una limitación pendiente de arreglar: es el estado
correcto mientras el tramo no exista.** Lo que sería un defecto es levantarla
antes.

## 5 · Lo que este tramo cambió, y que sigue verde

| | |
|---|---|
| El drenaje pasa por el puerto en vez de llamar al transporte directamente | ✅ |
| Las siete comprobaciones de los dos servicios | ✅ verde |
| El cinturón entero, con sus tres desenlaces | ✅ **0 · 20 · 30** `[M]` |
| El preflight comprueba que la garantía no se filtró al transporte | ✅ nuevo |
