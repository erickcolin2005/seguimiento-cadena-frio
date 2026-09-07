# CE-4 · Lo que costó la plomería

> **La condición, literal:** *«En M11 se registra si la plomería costó lo que la
> experiencia declarada supone. Si no coincide, se corrige el plan, no la
> evidencia.»*

**Esto es un dato, no un juicio.** No dice si Erick es bueno en esto; dice qué
pasó en un tramo, con qué criterio se decide, y qué salió.

---

## 1 · El criterio, que estaba escrito de antes

Las dos ramas se dejaron calculadas antes de empezar, para que el resultado no
se pudiera acomodar después:

| Rama | Qué supone | Qué implica |
|---|---|---|
| **A** · declaración exacta | La plomería es barata | El eje se compra y el retorno es casi todo señal |
| **B** · declaración optimista | **FF2 se materializa** | El eje no se compra y el retorno se muda a capacidad adquirida |

Y **FF2 tiene forma detectable**, que es lo que hace esto medible en vez de
opinable:

> **Tres sesiones** en un elemento del nivel Ampliado **sin que cambie ninguna
> de las seis conductas observables.**

## 2 · Qué pasó, contado contra ese criterio

| Criterio de FF2 | Lo ocurrido | ¿Se cumple FF2? |
|---|---|---|
| Tres sesiones o más | **Una** | No |
| Ninguna conducta observable cambia | **D-E producida**: la garantía deja de apoyarse en una llamada en proceso y queda medida sobre un segundo transporte, con consumidores muertos a propósito | No |

**Veredicto de CE-4: rama A.** FF2 **no** se materializó, según su propio
criterio declarado y no según una impresión.

**D-E era el único de los seis comportamientos que podía no llegar**, y es el
que justifica que este proyecto exista en vez de otro. Ahora existe.

## 3 · Lo que sí costó, porque un dato que solo trae buenas noticias no es un dato

### 3.1 · Coste recurrente: el cinturón casi se duplica

Las dos corridas, **del mismo código y de la misma máquina**:

| | directo | eventos | factor |
|---|---|---|---|
| EP-4..7 (la medición) | 202,7 s | 389,0 s | 1,92× |
| **Cinturón completo** | **221,3 s** | **408,6 s** | **1,85×** |
| Muertes provocadas | 168 | 168 | 1,00× |
| Veredicto | APROBADO · 0 | APROBADO · 0 | — |

**Esto no es un coste que se paga una vez: se paga en cada corrida.** Y con el
intermediario configurado para *no* esperar antes de reagrupar altas de
consumidor — sin esa configuración sería bastante peor. La cifra no es
interpretable sin esa línea al lado, y por eso van siempre juntas.

### 3.2 · Dos defectos, los dos en el instrumento

| # | Qué | De quién |
|---|---|---|
| 1 | El bombeo traía **una lectura por vuelta**, con una confirmación de avance propia cada una. A tamaño real la ingesta no terminaba dentro del tope y la corrida se declaraba inválida | Instrumento |
| 2 | La salida imprimía **«Medido sobre un mecanismo directo»** *mientras corría sobre el otro transporte*. Escrita a mano, sobrevivió intacta al cambio que la volvió falsa | Instrumento |

**Ninguno del sistema medido.** Es el mismo patrón que este proyecto ya tenía
registrado tres veces, y estos son el cuarto y el quinto caso. El segundo es
además de la peor familia: un artefacto **publicando la leyenda en vez del
hecho medido**, y precisamente la leyenda que una condición del proyecto
impone.

Los dos se arreglaron quitando la excepción, no añadiéndola: el tope de espera
ahora **crece con el trabajo** (uno fijo no es un tope, es un límite de tamaño
disfrazado), y la frase de alcance **se deriva** del transporte real, así que no
puede quedarse vieja.

### 3.3 · Dos huecos del diseño, que la plomería sacó a la luz

El diseño afirmaba que sustituir el transporte sería **cambiar un adaptador**.
Se cumplió en lo esencial —la bandeja de salida, la clave de la terna, la
re-derivación del orden por secuencia, el sellado y los tres niveles de
conclusión no se tocaron— pero **dos cosas no estaban donde el diseño las daba
por puestas**:

1. **El puerto de entrada no existía.** El diseño decía que en M11 cambian los
   dos adaptadores, pero solo había costura en el de salida: la ingesta atendía
   su ruta a pelo. Y sin puerto de entrada **no hay ningún consumidor matable**,
   porque el único que quedaría es el testigo, al que está prohibido matar. La
   comprobación que da nombre al tramo no se habría podido ni intentar.
2. **El desenlace del drenaje se quedaba corto.** Un productor asíncrono **no
   conoce el veredicto del receptor**, y devolver `registrada` desde él habría
   sido inventarse una respuesta que nadie dio. Hizo falta un cuarto desenlace
   que informa de un hecho distinto: custodia duradera aceptada.

**Lo que estos dos huecos no son:** un rediseño. Nada de lo que sostiene la
garantía cambió. Pero decir «solo cambia un adaptador» habría sido inexacto, y
se corrige el plan, no la evidencia.

## 4 · Lo que este registro NO dice

- **No mide la experiencia declarada en general.** Mide un tramo. Una muestra
  de uno no es una tendencia, y tratarla como tal sería exactamente el error
  que este proyecto persigue.
- **No dice que la plomería sea barata en producción.** Dice que costó poco
  *aquí*, sobre una máquina, con un nodo, sin carga y sin operación.
- **No mide memoria ni minutos de CPU.** Siguen sin medirse.
