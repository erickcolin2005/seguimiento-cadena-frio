"""Genera la tabla publicable DESDE el artefacto crudo de una corrida.

    python tabla.py evidencia/pl-4/verde/corrida.json

**Nunca se escribe a mano.** Una tabla tecleada es una tabla en la que alguien
pudo elegir qué filas copiaba — y este proyecto publica la salida cruda, con los
fallos dentro, sin promediar ni descartar corridas. Si la tabla del README no se
puede regenerar desde el artefacto, la publicación no es válida.

Por eso este fichero es tan corto: **no decide nada**. Lee el artefacto y lo
formatea. Cualquier número que aparezca en la tabla y no esté en el artefacto es
un defecto de este fichero, y se ve comparando los dos.
"""

import json
import sys
from pathlib import Path


def tabla(artefacto):
    lineas = []
    lineas.append("| Etapa | Qué corre | Desenlace | Segundos |")
    lineas.append("|---|---|---|---|")
    for e in artefacto["etapas"]:
        lineas.append("| **%s** | %s | **%s** | %.1f |"
                      % (e["codigo"], e["nombre"], e["veredicto"], e["segundos"]))
    lineas.append("| | **TOTAL** | **%s** | **%.1f** |"
                  % (artefacto["veredicto"], artefacto["segundos_total"]))
    return "\n".join(lineas)


def pie(artefacto):
    muertes = artefacto.get("muertes_provocadas_por_la_medicion")
    lineas = [
        "",
        "**Código de salida: %d.** Corrida del %s, en `%s`, con Python %s."
        % (artefacto["codigo"], artefacto["instante"], artefacto["donde_corrio"],
           artefacto["python"]),
        "Digesto del banco: `%s`." % artefacto["digesto_banco"][:16],
        "",
        "Procesos arrancados directamente por el cinturón: **%d**."
        % artefacto["procesos_directos"],
    ]
    if muertes:
        lineas.append("Procesos que la medición mata por dentro: **%d**." % muertes)
    lineas.append("")
    lineas.append("**Lo que esta corrida NO midió**, declarado en el propio artefacto:")
    for cosa in artefacto["no_medido"]:
        lineas.append("- %s" % cosa)
    if artefacto["motivos"]:
        lineas.append("")
        lineas.append("**Motivos del desenlace:**")
        for m in artefacto["motivos"]:
            lineas.append("- %s" % m)
    return "\n".join(lineas)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__.strip().splitlines()[2].strip())
        return 2
    artefacto = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    print(tabla(artefacto))
    print(pie(artefacto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
