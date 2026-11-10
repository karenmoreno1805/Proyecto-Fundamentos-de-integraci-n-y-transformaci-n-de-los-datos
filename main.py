"""Punto de entrada del pipeline.

Uso:
    python main.py                      # lee data/raw/, escribe data/processed/ y outputs/
    python main.py --raw-dir otra/ruta  # usa otra carpeta de entrada

Etapas (siguen el "ciclo completo del flujo de ingeniería de datos"):
    1. CARGAR     src/carga.py
    2. PERFILAR   src/perfilado.py
    3. LIMPIAR    src/limpieza.py    (5 transformaciones)
    4. INTEGRAR   src/integracion.py
    5. VALIDAR    src/validacion.py
    6. EXPORTAR   datasets + outputs/reporte_calidad.md
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from src import (carga, config, integracion, limpieza, perfilado, reporte,
                 validacion)


def _titulo(texto: str) -> None:
    print("\n" + "=" * 78)
    print(texto)
    print("=" * 78)


def ejecutar_pipeline(dir_raw=None, dir_processed=None, dir_outputs=None) -> dict:
    """Ejecuta el pipeline completo y devuelve los DataFrames resultantes."""
    inicio = time.time()
    dir_raw = Path(dir_raw) if dir_raw else config.DIR_RAW
    dir_processed = Path(dir_processed) if dir_processed else config.DIR_PROCESSED
    dir_outputs = Path(dir_outputs) if dir_outputs else config.DIR_OUTPUTS
    dir_processed.mkdir(parents=True, exist_ok=True)
    dir_outputs.mkdir(parents=True, exist_ok=True)

    _titulo("1. CARGAR - lectura de fuentes crudas")
    comfa_raw = carga.cargar_comfatolima(dir_raw)
    dane_raw = carga.cargar_dane(dir_raw)

    _titulo("2. PERFILAR - diagnóstico inicial de calidad")
    diagnostico = perfilado.diagnostico_inicial(comfa_raw, dane_raw)

    _titulo("3. LIMPIAR - cinco transformaciones")
    comfa_limpia = limpieza.limpiar_comfatolima(comfa_raw)          # T1, T2, T3
    dane_tidy = limpieza.t4_normalizar_dane(dane_raw)                # T4
    vacantes_tolima = limpieza.t5_segmentar_tolima(comfa_limpia)     # T5

    _titulo("4. INTEGRAR - vacantes del Tolima + indicadores DANE")
    integrado, dane_anual = integracion.integrar(vacantes_tolima, dane_tidy)

    _titulo("5. VALIDAR - controles de calidad e integridad")
    resultados = validacion.validar_todo(vacantes_tolima, dane_tidy, integrado, dane_anual)
    validacion.imprimir_resultados(resultados)

    resumen = {
        "Vacantes del Tolima (filas)": len(vacantes_tolima),
        "Plazas de trabajo en el Tolima": int(vacantes_tolima["CANTIDAD_VACANTES"].sum()),
        "Registros DANE normalizados": len(dane_tidy),
        "Filas del dataset integrado": len(integrado),
        "Columnas del dataset integrado": integrado.shape[1],
    }
    reporte.escribir_reporte(
        dir_outputs / config.SALIDA_REPORTE,
        diagnostico,
        perfilado.perfilar_comfatolima(comfa_limpia),
        perfilado.perfilar_dane_limpio(dane_tidy),
        resultados,
        resumen,
    )
    validacion.exigir_criticas(resultados)  # si algo crítico falló, no se exporta

    _titulo("6. EXPORTAR - datasets finales")
    destinos = {
        dir_processed / config.SALIDA_VACANTES: vacantes_tolima,
        dir_processed / config.SALIDA_DANE: dane_tidy,
        dir_outputs / config.SALIDA_INTEGRADO: integrado,
    }
    for ruta, df in destinos.items():
        df.to_csv(ruta, index=False, encoding="utf-8-sig")
        print(f" - {ruta.parent.name}/{ruta.name}  ({len(df)} filas x {df.shape[1]} columnas)")
    print(f" - {dir_outputs.name}/{config.SALIDA_REPORTE}")

    print(f"\nPipeline finalizado correctamente en {time.time() - inicio:.1f} s.")
    return {
        "comfa_limpia": comfa_limpia,
        "vacantes_tolima": vacantes_tolima,
        "dane_tidy": dane_tidy,
        "dane_anual": dane_anual,
        "integrado": integrado,
        "resultados": resultados,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # evita errores de acentos en consolas de Windows
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Pipeline de integración de datos laborales del Tolima")
    parser.add_argument("--raw-dir", default=None, help="Carpeta con COMFATOLIMA.xlsx y dane.xlsx")
    args = parser.parse_args()
    try:
        ejecutar_pipeline(dir_raw=args.raw_dir)
    except (FileNotFoundError, validacion.ValidacionError, ValueError) as error:
        print(f"\n[ERROR] {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
