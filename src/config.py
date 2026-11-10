"""Configuración central del pipeline: rutas, nombres de archivo y reglas de negocio.

Todo lo que se pueda querer cambiar (un umbral, un nombre de archivo, el mapa de
salarios) vive aquí, para no tener "números mágicos" regados por el código.
"""
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Rutas (relativas a la raíz del repositorio, funcionan en Windows, Linux y Colab)
# --------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_PROCESSED = RAIZ / "data" / "processed"
DIR_OUTPUTS = RAIZ / "outputs"

# --------------------------------------------------------------------------
# Fuentes de entrada (deben estar en data/raw/)
# --------------------------------------------------------------------------
ARCHIVO_COMFATOLIMA = "COMFATOLIMA.xlsx"
ARCHIVO_DANE = "dane.xlsx"
HOJA_DANE = "Hoja1"

# --------------------------------------------------------------------------
# Archivos de salida
# --------------------------------------------------------------------------
SALIDA_VACANTES = "Fact_Vacantes_Tolima_Limpio.csv"          # -> data/processed/
SALIDA_DANE = "Fact_Indicadores_DANE_Tolima_Limpio.csv"      # -> data/processed/
SALIDA_INTEGRADO = "Dataset_Integrado_Tolima.csv"            # -> outputs/
SALIDA_REPORTE = "reporte_calidad.md"                        # -> outputs/

# --------------------------------------------------------------------------
# Reglas de negocio
# --------------------------------------------------------------------------
DEPARTAMENTO_OBJETIVO = "TOLIMA"
MAX_MESES_EXPERIENCIA = 120  # 10 años; por encima se considera error de captura

# Columnas de texto donde se corrige la codificación (mojibake)
COLUMNAS_TEXTO = [
    "TITULO_VACANTE",
    "DESCRIPCION_VACANTE",
    "CARGO",
    "SECTOR_ECONOMICO",
    "NOMBRE_PRESTADOR",
    "MUNICIPIO",
    "NIVEL_ESTUDIOS",
    "TIPO_CONTRATO",
]
PREFIJO_BASURA = "$hNo Codigo vacante$"

# Rango salarial (texto) -> valor numérico estimado (punto medio del rango, en COP)
SALARIO_MAP = {
    "$1.000.001 - $1.500.000": 1250000,
    "$1.500.001 - $2.000.000": 1750000,
    "$2.000.001 - $3.000.000": 2500000,
    "$3.000.001 - $4.000.000": 3500000,
    "$4.000.001 - $6.000.000": 5000000,
    "$6.000.001 - $8.000.000": 7000000,
    "Mayor de $15.000.001": 15000000,
    "$589.500 - $884.250": 736875,
    "$884.251 - $1.000.000": 942125,
    "Menos del Salario Mínimo": 650000,
    "A Convenir": np.nan,  # no se inventa un salario: queda como nulo
}

# Los 47 municipios del Tolima (se comparan sin tildes ni mayúsculas)
MUNICIPIOS_TOLIMA = [
    "Alpujarra", "Alvarado", "Ambalema", "Anzoátegui", "Armero", "Armero Guayabal",
    "Ataco", "Cajamarca", "Carmen de Apicalá", "Casabianca", "Chaparral", "Coello",
    "Coyaima", "Cunday", "Dolores", "Espinal", "El Espinal", "Falan", "Flandes",
    "Fresno", "Guamo", "El Guamo", "Herveo", "Honda", "Ibagué", "Icononzo", "Lérida",
    "Líbano", "Mariquita", "San Sebastián de Mariquita", "Melgar", "Murillo",
    "Natagaima", "Ortega", "Palocabildo", "Piedras", "Planadas", "Prado",
    "Purificación", "Rioblanco", "Roncesvalles", "Rovira", "Saldaña", "San Antonio",
    "San Luis", "Santa Isabel", "Suárez", "Valle de San Juan", "Venadillo",
    "Villahermosa", "Villarrica",
]
