"""ETAPA 1 - CARGAR: lectura de las fuentes crudas desde data/raw/."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import config


def _buscar_archivo(dir_raw: Path, nombre: str) -> Path:
    """Busca el archivo sin distinguir mayúsculas de minúsculas.

    Windows no distingue 'Dane.xlsx' de 'dane.xlsx', pero Linux/Colab sí.
    """
    exacto = dir_raw / nombre
    if exacto.exists():
        return exacto
    if dir_raw.exists():
        for candidato in dir_raw.iterdir():
            if candidato.name.lower() == nombre.lower():
                return candidato
    raise FileNotFoundError(
        f"No se encontró '{nombre}' en '{dir_raw}'.\n"
        f"Copia los archivos originales ({config.ARCHIVO_COMFATOLIMA} y "
        f"{config.ARCHIVO_DANE}) en la carpeta data/raw/ y vuelve a ejecutar."
    )


def cargar_comfatolima(dir_raw: str | Path | None = None) -> pd.DataFrame:
    """Carga las vacantes del Servicio Público de Empleo / ComfaTolima (microdatos)."""
    dir_raw = Path(dir_raw) if dir_raw else config.DIR_RAW
    ruta = _buscar_archivo(dir_raw, config.ARCHIVO_COMFATOLIMA)
    df = pd.read_excel(ruta)
    print(f"[OK] COMFATOLIMA cargado: {df.shape[0]} filas x {df.shape[1]} columnas.")
    return df


def cargar_dane(dir_raw: str | Path | None = None) -> pd.DataFrame:
    """Carga la matriz de indicadores laborales del DANE (macrodatos del Tolima)."""
    dir_raw = Path(dir_raw) if dir_raw else config.DIR_RAW
    ruta = _buscar_archivo(dir_raw, config.ARCHIVO_DANE)
    df = pd.read_excel(ruta, sheet_name=config.HOJA_DANE)
    print(f"[OK] DANE cargado: {df.shape[0]} filas x {df.shape[1]} columnas.")
    return df
