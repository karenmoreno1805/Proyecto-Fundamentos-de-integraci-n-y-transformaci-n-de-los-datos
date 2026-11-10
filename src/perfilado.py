"""ETAPA 2 - PERFILAR: diagnóstico de calidad de las fuentes (antes de transformar).

Las mismas métricas se vuelven a calcular sobre los datos limpios para poder
comparar "antes vs. después" en el reporte de calidad.
"""
from __future__ import annotations

import pandas as pd

from src import config

# Secuencias típicas de texto UTF-8 mal decodificado ("mojibake")
MARCAS_MOJIBAKE = ("Ã", "Â", "�")


def _columnas_texto(df: pd.DataFrame) -> list[str]:
    return [c for c in config.COLUMNAS_TEXTO if c in df.columns]


def contar_celdas_mojibake(df: pd.DataFrame) -> int:
    """Cuenta celdas de texto con caracteres corruptos (Ã, Â, �)."""
    total = 0
    for col in _columnas_texto(df):
        serie = df[col].dropna().astype(str)
        total += int(serie.apply(lambda t: any(m in t for m in MARCAS_MOJIBAKE)).sum())
    return total


def contar_prefijo_basura(df: pd.DataFrame) -> int:
    """Cuenta celdas contaminadas con el prefijo de sistema '$hNo Codigo vacante$'."""
    total = 0
    for col in _columnas_texto(df):
        serie = df[col].dropna().astype(str)
        total += int(serie.str.contains(config.PREFIJO_BASURA, regex=False).sum())
    return total


def contar_atipicos_iqr(serie: pd.Series) -> int:
    """Atípicos por rango intercuartílico: fuera de [Q1 - 1.5*IQR, Q3 + 1.5*IQR]."""
    s = pd.to_numeric(serie, errors="coerce").dropna()
    if len(s) < 4:
        return 0
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())


def perfilar_comfatolima(df: pd.DataFrame) -> dict:
    """Métricas de calidad de la fuente de vacantes."""
    depto = df["DEPARTAMENTO"].astype(str).str.upper().str.strip()
    es_tolima = depto == config.DEPARTAMENTO_OBJETIVO
    exp = pd.to_numeric(df["MESES_EXPERIENCIA_CARGO"], errors="coerce")
    plazas = pd.to_numeric(df.loc[es_tolima, "CANTIDAD_VACANTES"], errors="coerce").sum()
    return {
        "Filas totales": int(len(df)),
        "Filas totalmente duplicadas": int(df.duplicated().sum()),
        "Códigos de vacante duplicados": int(df.duplicated(subset=["CODIGO_VACANTE"]).sum()),
        "Celdas de texto con mojibake": contar_celdas_mojibake(df),
        "Celdas con prefijo de sistema": contar_prefijo_basura(df),
        f"Vacantes con experiencia > {config.MAX_MESES_EXPERIENCIA} meses": int(
            (exp > config.MAX_MESES_EXPERIENCIA).sum()
        ),
        "Experiencia máxima registrada (meses)": None if exp.dropna().empty else int(exp.max()),
        "Atípicos de experiencia (criterio IQR)": contar_atipicos_iqr(exp),
        "Vacantes con salario 'A Convenir'": int((df["RANGO_SALARIAL"] == "A Convenir").sum()),
        "Ofertas del Tolima": int(es_tolima.sum()),
        "Plazas de trabajo en el Tolima": int(plazas),
    }


def perfilar_dane_crudo(df: pd.DataFrame) -> dict:
    """Métricas de la matriz DANE tal como llega (formato ancho)."""
    return {
        "Filas": int(df.shape[0]),
        "Columnas": int(df.shape[1]),
        "Filas totalmente nulas": int(df.isna().all(axis=1).sum()),
        "Celdas nulas": int(df.isna().sum().sum()),
        "Formato": "Matriz ancha (una fila por indicador, una columna por año)",
    }


def perfilar_dane_limpio(df: pd.DataFrame) -> dict:
    """Métricas del DANE ya normalizado (formato largo / tidy)."""
    return {
        "Filas": int(df.shape[0]),
        "Columnas": int(df.shape[1]),
        "Filas totalmente nulas": int(df.isna().all(axis=1).sum()),
        "Celdas nulas": int(df.isna().sum().sum()),
        "Formato": f"Tabla tidy ({df['CONCEPTO'].nunique()} indicadores x "
                   f"{df['ANIO'].nunique()} años)",
    }


def diagnostico_inicial(df_comfa: pd.DataFrame, df_dane: pd.DataFrame) -> dict:
    """Imprime la evidencia de calidad y devuelve las métricas (para el reporte)."""
    comfa = perfilar_comfatolima(df_comfa)
    dane = perfilar_dane_crudo(df_dane)

    print("--- ComfaTolima ---")
    print(f"[EVIDENCIA 1] Filas totalmente duplicadas: {comfa['Filas totalmente duplicadas']}")
    print(f"[EVIDENCIA 1] Códigos de vacante duplicados: {comfa['Códigos de vacante duplicados']}")
    tol, tot = comfa["Ofertas del Tolima"], comfa["Filas totales"]
    pct = tol / tot * 100 if tot else 0
    print(f"[EVIDENCIA 2] Ofertas del Tolima: {tol} de {tot} ({pct:.1f}%) | "
          f"plazas: {comfa['Plazas de trabajo en el Tolima']}")
    llave = f"Vacantes con experiencia > {config.MAX_MESES_EXPERIENCIA} meses"
    print(f"[EVIDENCIA 3] {llave}: {comfa[llave]} "
          f"(máximo registrado: {comfa['Experiencia máxima registrada (meses)']} meses)")
    conv = comfa["Vacantes con salario 'A Convenir'"]
    print(f"[EVIDENCIA 4] Salario 'A Convenir': {conv} ({conv / tot * 100 if tot else 0:.1f}%)")
    print(f"[EVIDENCIA 5] Celdas de texto con mojibake: {comfa['Celdas de texto con mojibake']}")
    print("--- DANE ---")
    print(f"[EVIDENCIA 6] Formato: {dane['Formato']}")
    print(f"[EVIDENCIA 7] Filas totalmente nulas: {dane['Filas totalmente nulas']}")
    return {"comfatolima": comfa, "dane": dane}
