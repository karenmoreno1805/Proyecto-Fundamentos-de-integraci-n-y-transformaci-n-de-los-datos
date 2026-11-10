"""ETAPA 4 - INTEGRAR: unión de las vacantes del Tolima con los indicadores del DANE.

Llave de integración: el AÑO.
  - Vacantes (ComfaTolima): microdatos con fecha de publicación diaria.
  - DANE: indicadores anuales a nivel departamental.

Decisión de diseño: cada vacante recibe los indicadores macroeconómicos del año de
referencia (ANIO_REFERENCIA_DANE). Si el DANE aún no publica el año de la vacante
(por ejemplo, vacantes de 2026 y DANE hasta 2025), se usa el último año
disponible. Esa columna queda en el dataset para que la decisión sea transparente.

Tipo de unión: LEFT JOIN muchos-a-uno (vacantes -> año). Se conservan todas las
vacantes y ninguna fila se duplica (pandas lo verifica con validate="many_to_one").
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def nombre_columna_dane(concepto: str) -> str:
    """Nombre de columna corto y estable para un indicador del DANE.

    'Tasa de Desocupación (TD)'          -> 'DANE_TD'
    '% población en edad de trabajar'    -> 'DANE_PCT_POBLACION_EN_EDAD_DE_TRABAJAR'
    """
    sigla = re.search(r"\(([A-Za-z]{2,5})\)", concepto)
    if sigla:
        base = sigla.group(1).upper()
    else:
        texto = _sin_tildes(concepto).replace("%", " pct ")
        base = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").upper()
    return f"DANE_{base}"


def pivotar_dane(dane_tidy: pd.DataFrame) -> pd.DataFrame:
    """Convierte el DANE tidy en una tabla anual: una fila por año, una columna por indicador."""
    tabla = dane_tidy.copy()
    tabla["COLUMNA"] = tabla["CONCEPTO"].map(nombre_columna_dane)
    if tabla.groupby("COLUMNA")["CONCEPTO"].nunique().max() > 1:
        raise ValueError("Dos indicadores del DANE producen el mismo nombre de columna.")

    orden = list(dict.fromkeys(tabla["COLUMNA"]))
    ancha = tabla.pivot(index="ANIO", columns="COLUMNA", values="VALOR").reset_index()
    ancha.columns.name = None
    return ancha[["ANIO"] + orden]


def integrar(vacantes: pd.DataFrame, dane_tidy: pd.DataFrame):
    """Integra vacantes del Tolima + indicadores DANE.

    Devuelve (dataset_integrado, dane_anual) — el segundo se usa en las validaciones.
    """
    dane_anual = pivotar_dane(dane_tidy)
    anio_min, anio_max = int(dane_anual["ANIO"].min()), int(dane_anual["ANIO"].max())

    out = vacantes.copy()
    fecha = pd.to_datetime(out["FECHA_PUBLICACION"], errors="coerce")
    out["ANIO_PUBLICACION"] = fecha.dt.year.astype("Int64")
    out["ANIO_REFERENCIA_DANE"] = out["ANIO_PUBLICACION"].clip(lower=anio_min, upper=anio_max)

    integrado = out.merge(
        dane_anual,
        how="left",
        left_on="ANIO_REFERENCIA_DANE",
        right_on="ANIO",
        validate="many_to_one",
    ).drop(columns="ANIO")

    anios_usados = sorted(integrado["ANIO_REFERENCIA_DANE"].dropna().unique().tolist())
    print(f"[Integración completada] {len(integrado)} vacantes del Tolima + "
          f"{dane_anual.shape[1] - 1} indicadores DANE (año de referencia: {anios_usados}).")
    return integrado, dane_anual
