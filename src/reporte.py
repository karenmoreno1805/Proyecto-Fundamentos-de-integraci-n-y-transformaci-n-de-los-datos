"""Genera outputs/reporte_calidad.md: comparación antes vs. después y validaciones."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _fmt(valor) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return str(valor)


def _tabla_comparativa(antes: dict, despues: dict) -> list[str]:
    filas = ["| Métrica | Antes (crudo) | Después (limpio) |", "|---|---:|---:|"]
    for clave in antes:
        filas.append(f"| {clave} | {_fmt(antes[clave])} | {_fmt(despues.get(clave))} |")
    return filas


def escribir_reporte(ruta: Path, diag_antes: dict, comfa_despues: dict, dane_despues: dict,
                     resultados: list, resumen: dict) -> None:
    """Escribe el reporte de calidad en Markdown."""
    ok = sum(r.ok for r in resultados)
    lineas = [
        "# Reporte de calidad del pipeline",
        "",
        f"_Generado automáticamente el {datetime.now():%Y-%m-%d %H:%M}._",
        "",
        "## 1. Vacantes (ComfaTolima): antes vs. después de limpiar",
        "",
        "El 'después' se mide sobre todo el archivo ya limpio (T1-T3), antes de filtrar al Tolima.",
        "",
        *_tabla_comparativa(diag_antes["comfatolima"], comfa_despues),
        "",
        "> Nota: 'A Convenir' se mantiene en el rango original, pero queda como nulo en "
        "`SALARIO_ESTIMADO_NUM` (no se inventa un salario).",
        "",
        "## 2. Indicadores DANE: antes vs. después",
        "",
        "| Métrica | Antes (matriz ancha) | Después (tidy) |",
        "|---|---:|---:|",
    ]
    for clave, valor in diag_antes["dane"].items():
        lineas.append(f"| {clave} | {_fmt(valor)} | {_fmt(dane_despues.get(clave))} |")

    lineas += [
        "",
        f"## 3. Validaciones ({ok} de {len(resultados)} aprobadas)",
        "",
        "| Estado | Validación | Detalle |",
        "|---|---|---|",
    ]
    for r in resultados:
        lineas.append(f"| {r.estado} | {r.nombre} | {r.detalle} |")

    lineas += ["", "## 4. Resultado final", "", "| Dato | Valor |", "|---|---:|"]
    for clave, valor in resumen.items():
        lineas.append(f"| {clave} | {_fmt(valor)} |")
    lineas.append("")

    ruta.write_text("\n".join(lineas), encoding="utf-8")
