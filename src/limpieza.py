"""ETAPA 3 - LIMPIAR / TRANSFORMAR: las 5 transformaciones del pipeline.

Cada transformación es una función independiente que recibe un DataFrame y devuelve
uno nuevo (no modifica el original). En el docstring de cada una está la
JUSTIFICACIÓN técnica: qué problema detectado en el diagnóstico resuelve y por qué
se decidió así.

    T1  Corrección de codificación (mojibake)        -> ComfaTolima
    T2  Desduplicación y tratamiento de outliers     -> ComfaTolima
    T3  Estandarización del rango salarial a número  -> ComfaTolima
    T4  Normalización (unpivot/melt) de la matriz    -> DANE
    T5  Segmentación geográfica (solo Tolima)        -> ComfaTolima
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config

# --------------------------------------------------------------------------
# T1 - Mojibake
# --------------------------------------------------------------------------
# Pares (texto corrupto -> texto correcto). Se usan solo cuando la reversión exacta
# no es posible (por ejemplo, cuando hay una mezcla de texto bueno y corrupto).
# Los pares de DOS caracteres van primero y el 'Â' suelto al final: así no se
# daña un 'Ã³' al procesar primero un 'Ã' suelto.
REEMPLAZOS_MOJIBAKE = [
    ("Ã�", "Í"), ("Ã\x8d", "Í"), ("Ã\x81", "Á"),
    ("Ã¡", "á"), ("Ã©", "é"), ("Ã\xad", "í"), ("Ã³", "ó"), ("Ãº", "ú"),
    ("Ã±", "ñ"), ("Ã¼", "ü"),
    ("Ã‰", "É"), ("Ã“", "Ó"), ("Ãš", "Ú"),
    ("Ã‘", "Ñ"), ("Ãœ", "Ü"),
    ("Â", ""),
]


def corregir_texto(texto):
    """Repara un texto con mojibake y limpia prefijos de sistema.

    1) Intenta la reversión exacta: el texto UTF-8 se leyó como cp1252/latin-1, así
       que se codifica de vuelta con ese códec y se decodifica como UTF-8.
    2) Si no es posible (mezcla de texto bueno y corrupto, o bytes perdidos '�'),
       aplica la tabla de reemplazos REEMPLAZOS_MOJIBAKE.
    """
    if not isinstance(texto, str):
        return texto
    if any(marca in texto for marca in ("Ã", "Â")):
        for codec in ("cp1252", "latin-1"):
            try:
                texto = texto.encode(codec).decode("utf-8")
                break
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
        else:
            for malo, bueno in REEMPLAZOS_MOJIBAKE:
                texto = texto.replace(malo, bueno)
    texto = texto.replace(config.PREFIJO_BASURA, "")
    return texto.strip()


def t1_corregir_encoding(df: pd.DataFrame) -> pd.DataFrame:
    """T1 - Corrección de codificación (mojibake UTF-8).

    Problema: títulos, cargos y sectores traen caracteres corruptos
    ('VEHÃ�CULO', 'ingenierÃ­a') y el prefijo basura '$hNo Codigo vacante$'.
    Justificación: son las columnas que se van a agrupar y buscar por texto; con la
    codificación dañada, 'ALMACÉN' y 'ALMACÃ‰N' cuentan como categorías distintas y
    las búsquedas fallan.
    """
    out = df.copy()
    corregidas = 0
    for col in [c for c in config.COLUMNAS_TEXTO if c in out.columns]:
        antes = out[col]
        despues = antes.apply(corregir_texto)
        cambiadas = (antes != despues) & ~(antes.isna() & despues.isna())
        corregidas += int(cambiadas.sum())
        out[col] = despues
    print(f"[T1 Completada] Codificación UTF-8 corregida: {corregidas} celdas modificadas.")
    return out


# --------------------------------------------------------------------------
# T2 - Duplicados y outliers
# --------------------------------------------------------------------------
def t2_deduplicar_y_tratar_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """T2 - Desduplicación por CODIGO_VACANTE y tratamiento de outliers de experiencia.

    Problema: hay vacantes repetidas (mismo CODIGO_VACANTE) y experiencias de hasta
    999 meses, que son códigos de error del formulario web, no datos reales.
    Justificación: la clave primaria debe ser única para que el conteo de plazas no
    se infle y para poder integrar sin multiplicar filas. Los valores > 120 meses
    (10 años) se pasan a nulo en lugar de recortarlos: inventar un 120 sería falsear
    el dato; el nulo dice honestamente "no informado".
    """
    n_inicial = len(df)
    out = df.drop_duplicates(subset=["CODIGO_VACANTE"], keep="first").copy()
    duplicados = n_inicial - len(out)

    exp = pd.to_numeric(out["MESES_EXPERIENCIA_CARGO"], errors="coerce")
    outliers = int((exp > config.MAX_MESES_EXPERIENCIA).sum())
    exp = exp.where(exp <= config.MAX_MESES_EXPERIENCIA)
    try:
        exp = exp.astype("Int64")  # enteros con soporte de nulos (sin ".0" en el CSV)
    except (TypeError, ValueError):
        pass
    out["MESES_EXPERIENCIA_CARGO"] = exp

    print(f"[T2 Completada] {duplicados} vacantes duplicadas eliminadas; "
          f"{outliers} valores de experiencia > {config.MAX_MESES_EXPERIENCIA} meses "
          f"convertidos a nulo.")
    return out


# --------------------------------------------------------------------------
# T3 - Salario
# --------------------------------------------------------------------------
def t3_estandarizar_salario(df: pd.DataFrame) -> pd.DataFrame:
    """T3 - Mapeo del rango salarial (texto) a un valor numérico estimado.

    Problema: RANGO_SALARIAL es texto ('$1.500.001 - $2.000.000'); no se puede
    promediar, ordenar ni comparar contra nada.
    Justificación: se usa el punto medio de cada rango (estimación estándar para
    datos agrupados) y se crea una columna NUEVA (SALARIO_ESTIMADO_NUM) conservando
    el rango original. 'A Convenir' se deja como nulo porque no hay base para
    estimarlo.
    """
    out = df.copy()
    rango = out["RANGO_SALARIAL"].str.strip()
    out["SALARIO_ESTIMADO_NUM"] = rango.map(config.SALARIO_MAP).astype("float64")

    sin_mapa = out.loc[
        out["SALARIO_ESTIMADO_NUM"].isna() & rango.notna() & (rango != "A Convenir"),
        "RANGO_SALARIAL",
    ].unique()
    if len(sin_mapa):
        print(f"[AVISO T3] Rangos salariales sin valor en config.SALARIO_MAP: {list(sin_mapa)}")
    n_num = int(out["SALARIO_ESTIMADO_NUM"].notna().sum())
    print(f"[T3 Completada] Salario convertido a numérico: {n_num} de {len(out)} vacantes "
          f"con valor estimado.")
    return out


def limpiar_comfatolima(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica T1, T2 y T3 sobre las vacantes (todo el país, antes de segmentar)."""
    df = t1_corregir_encoding(df_raw)
    df = t2_deduplicar_y_tratar_outliers(df)
    df = t3_estandarizar_salario(df)
    return df


# --------------------------------------------------------------------------
# T4 - DANE (unpivot)
# --------------------------------------------------------------------------
def _tipo_unidad(concepto: str) -> str:
    """Tasas y porcentajes vs. volúmenes de población (miles de personas)."""
    c = concepto.strip().lower()
    if c.startswith("%") or c.startswith("tasa"):
        return "Porcentaje (%)"
    return "Miles de personas"


def t4_normalizar_dane(df_raw: pd.DataFrame) -> pd.DataFrame:
    """T4 - Normalización (unpivot / melt) de la matriz del DANE a formato tidy.

    Problema: el DANE entrega una matriz ancha (una fila por indicador, una columna
    por año), con filas vacías separadoras y unidades mezcladas (porcentajes y miles
    de personas en la misma columna).
    Justificación: un formato largo [CONCEPTO, ANIO, VALOR, TIPO_UNIDAD] permite
    filtrar por año, que es justamente la llave para integrar con las vacantes, y
    deja explícita la unidad de cada indicador.
    """
    primera = df_raw.columns[0]
    es_encabezado = df_raw[primera].astype(str).str.strip().str.lower() == "concepto"
    if not es_encabezado.any():
        raise ValueError(
            "No se encontró la fila de encabezado ('Concepto') en la matriz del DANE; "
            "revisa que la hoja y el formato del archivo sean los originales."
        )
    pos = int(np.flatnonzero(es_encabezado.to_numpy())[0])

    anios = [str(int(a)) for a in df_raw.iloc[pos, 1:].tolist()]
    cuerpo = df_raw.iloc[pos + 1:].copy()
    cuerpo.columns = ["CONCEPTO"] + anios
    cuerpo = cuerpo.dropna(subset=["CONCEPTO"])  # quita las filas separadoras vacías
    cuerpo["CONCEPTO"] = cuerpo["CONCEPTO"].astype(str).str.strip()

    largo = cuerpo.melt(id_vars=["CONCEPTO"], var_name="ANIO", value_name="VALOR")
    largo["ANIO"] = largo["ANIO"].astype(int)
    largo["VALOR"] = pd.to_numeric(largo["VALOR"], errors="coerce")
    largo["TIPO_UNIDAD"] = largo["CONCEPTO"].map(_tipo_unidad)
    largo = largo.reset_index(drop=True)

    print(f"[T4 Completada] Matriz DANE convertida a formato tidy: "
          f"{cuerpo.shape[0]} indicadores x {len(anios)} años = {len(largo)} registros.")
    return largo


# --------------------------------------------------------------------------
# T5 - Segmentación geográfica
# --------------------------------------------------------------------------
def t5_segmentar_tolima(df: pd.DataFrame) -> pd.DataFrame:
    """T5 - Segmentación geográfica: conservar solo las vacantes del Tolima.

    Problema: el archivo de ComfaTolima trae vacantes de todo el país; solo una
    fracción pequeña (~1% en la muestra) es del Tolima.
    Justificación: el objetivo del proyecto es el mercado laboral del Tolima y el
    DANE se entrega a nivel departamental; mezclar vacantes de otros departamentos
    con indicadores del Tolima produciría conclusiones erróneas.
    """
    depto = df["DEPARTAMENTO"].astype(str).str.upper().str.strip()
    out = df[depto == config.DEPARTAMENTO_OBJETIVO].copy().reset_index(drop=True)
    print(f"[T5 Completada] Vacantes filtradas al Tolima: {len(out)} de {len(df)} ofertas.")
    return out
