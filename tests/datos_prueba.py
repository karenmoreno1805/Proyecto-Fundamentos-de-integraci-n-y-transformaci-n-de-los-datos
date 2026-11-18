"""Datos sintéticos que imitan la estructura de COMFATOLIMA.xlsx y dane.xlsx.

Sirven para probar el pipeline sin depender de los archivos reales (y para que las
pruebas corran en cualquier computador). Incluyen, a propósito, los problemas que
el pipeline debe resolver: duplicados, mojibake, outliers y rangos salariales.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402

COLUMNAS_COMFA = [
    "CODIGO_VACANTE", "TITULO_VACANTE", "DESCRIPCION_VACANTE", "NIVEL_ESTUDIOS",
    "RANGO_SALARIAL", "NOMBRE_PRESTADOR", "DEPARTAMENTO", "MUNICIPIO", "TIPO_CONTRATO",
    "URL_DETALLE_VACANTE", "CANTIDAD_VACANTES", "CARGO", "FECHA_PUBLICACION",
    "FECHA_VENCIMIENTO", "SECTOR_ECONOMICO", "TELETRABAJO", "DISCAPACIDAD",
    "MESES_EXPERIENCIA_CARGO", "HIDROCARBUROS", "PLAZA_PRACTICA",
]

# 8 vacantes del Tolima (incluye municipios distintos a los 4 más comunes)
MUNICIPIOS_TOLIMA_PRUEBA = ["IBAGUÉ", "IBAGUÉ", "ESPINAL", "HONDA", "MELGAR", "LÉRIDA",
                            "IBAGUÉ", "LÍBANO"]
N_TOLIMA = 8
N_OTROS = 30


def crear_comfatolima_prueba() -> pd.DataFrame:
    rangos = list(config.SALARIO_MAP.keys())
    deptos = ["TOLIMA"] * N_TOLIMA + ["ANTIOQUIA"] * 10 + ["BOGOTÁ, D.C."] * 10 + ["SANTANDER"] * 10
    filas = []
    for i, depto in enumerate(deptos):
        filas.append({
            "CODIGO_VACANTE": f"V{i:04d}",
            "TITULO_VACANTE": f"Auxiliar {i}",
            "DESCRIPCION_VACANTE": f"Se requiere auxiliar número {i}",
            "NIVEL_ESTUDIOS": ["Media", "Técnico", "Universitarios", "No Aplica"][i % 4],
            "RANGO_SALARIAL": rangos[i % len(rangos)],
            "NOMBRE_PRESTADOR": "CAJA DE COMPENSACIÓN FAMILIAR",
            "DEPARTAMENTO": depto,
            "MUNICIPIO": MUNICIPIOS_TOLIMA_PRUEBA[i] if depto == "TOLIMA" else "MEDELLÍN",
            "TIPO_CONTRATO": "Por obra o labor",
            "URL_DETALLE_VACANTE": f"https://ejemplo.gov.co/{i}",
            "CANTIDAD_VACANTES": 1 + i % 5,
            "CARGO": f"Cargo {i}",
            "FECHA_PUBLICACION": pd.Timestamp("2026-10-29 19:00"),
            "FECHA_VENCIMIENTO": pd.Timestamp("2026-11-05 19:00") + pd.Timedelta(days=i),
            "SECTOR_ECONOMICO": "Comercio",
            "TELETRABAJO": 0, "DISCAPACIDAD": 0,
            "MESES_EXPERIENCIA_CARGO": 12 * (i % 4),
            "HIDROCARBUROS": 0, "PLAZA_PRACTICA": 0,
        })
    df = pd.DataFrame(filas, columns=COLUMNAS_COMFA)

    # Problemas inyectados a propósito
    df.loc[0, "TITULO_VACANTE"] = "AUXILIAR DE BODEGA/ALMACÃ‰N (MELGAR)"          # mojibake É
    df.loc[1, "TITULO_VACANTE"] = "CONDUCTOR DE VEHÃ�CULO LIVIANO"         # mojibake Í perdida
    df.loc[2, "TITULO_VACANTE"] = "$hNo Codigo vacante$ Vendedor de minimercado"    # prefijo basura
    df.loc[3, "SECTOR_ECONOMICO"] = "Obras de ingenierÃ­a civil"          # mojibake í
    df.loc[0, "MESES_EXPERIENCIA_CARGO"] = 999                                      # outlier
    df.loc[1, "MESES_EXPERIENCIA_CARGO"] = 150                                      # outlier
    df.loc[5, "RANGO_SALARIAL"] = "A Convenir"
    duplicada = df.iloc[[4]]                                                        # fila (Tolima) repetida
    return pd.concat([df, duplicada], ignore_index=True)


def crear_dane_prueba(anio_ini: int = 2007, anio_fin: int = 2025, formato: str = "real") -> pd.DataFrame:
    """Réplica de la hoja 'Hoja1' del DANE.

    formato="real":   fila 'Concepto' (solo en la 1ª columna), y en la FILA SIGUIENTE los años.
                      Es el formato del archivo dane.xlsx original.
    formato="antiguo": 'Concepto' y los años en la misma fila.
    """
    anios = list(range(anio_ini, anio_fin + 1))
    columnas = ["Tolima"] + [f"Unnamed: {i}" for i in range(1, len(anios) + 1)]
    tasas = ["% población en edad de trabajar", "Tasa Global de Participación (TGP)",
             "Tasa de Ocupación (TO)", "Tasa de Desocupación (TD)", "Tasa de Subocupación (TS)"]
    volumenes = ["Población total", "Población en edad de trabajar (PET)", "Fuerza de trabajo ",
                 "Población ocupada", "Población desocupada",
                 "Población fuera de la fuerza de trabajo", "Población subocupada",
                 "Fuerza de trabajo potencial"]
    if formato == "real":
        filas = [["Concepto"] + [np.nan] * len(anios), [np.nan] + anios]
    else:
        filas = [[np.nan] * len(columnas), ["Concepto"] + anios]
    for k, nombre in enumerate(tasas):
        filas.append([nombre] + [50 + 3 * k + 0.1 * j for j in range(len(anios))])
    filas.append([np.nan] * len(columnas))
    for k, nombre in enumerate(volumenes):
        filas.append([nombre] + [500 + 100 * k + 2.5 * j for j in range(len(anios))])
    return pd.DataFrame(filas, columns=columnas)


def guardar_excel_prueba(dir_raw: Path) -> None:
    """Escribe los dos .xlsx de prueba dentro de dir_raw (con los nombres reales)."""
    dir_raw = Path(dir_raw)
    dir_raw.mkdir(parents=True, exist_ok=True)
    crear_comfatolima_prueba().to_excel(dir_raw / config.ARCHIVO_COMFATOLIMA, index=False)
    crear_dane_prueba().to_excel(dir_raw / config.ARCHIVO_DANE, index=False, sheet_name=config.HOJA_DANE)
