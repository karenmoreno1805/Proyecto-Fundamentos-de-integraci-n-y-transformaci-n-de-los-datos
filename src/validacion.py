"""ETAPA 5 - VALIDAR: reglas de negocio y de integridad sobre el resultado.

Cada validación produce un `Resultado`. Las validaciones CRÍTICAS detienen el
pipeline si fallan (no se exporta un dataset incorrecto); las de AVISO solo se
reportan. Se ejecutan todas antes de decidir, para ver todos los problemas juntos.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import config
from src.perfilado import contar_celdas_mojibake


class ValidacionError(Exception):
    """Se lanza cuando falla al menos una validación crítica."""


@dataclass
class Resultado:
    nombre: str
    ok: bool
    detalle: str = ""
    critica: bool = True

    @property
    def estado(self) -> str:
        if self.ok:
            return "OK"
        return "FALLO" if self.critica else "AVISO"


def _normalizar(texto) -> str:
    """Mayúsculas, sin tildes y sin espacios sobrantes (para comparar nombres)."""
    if not isinstance(texto, str):
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.upper().split())


MUNICIPIOS_TOLIMA_NORM = {_normalizar(m) for m in config.MUNICIPIOS_TOLIMA}


# --------------------------------------------------------------------------
def validar_vacantes(df: pd.DataFrame) -> list[Resultado]:
    """Validaciones del dataset de vacantes limpio (Tolima)."""
    r: list[Resultado] = []

    r.append(Resultado("Existe al menos una vacante del Tolima", len(df) > 0,
                       f"{len(df)} vacantes"))

    unica = bool(df["CODIGO_VACANTE"].notna().all() and df["CODIGO_VACANTE"].is_unique)
    r.append(Resultado("CODIGO_VACANTE único y sin nulos (clave primaria)", unica,
                       f"{int(df['CODIGO_VACANTE'].duplicated().sum())} duplicados"))

    plazas = pd.to_numeric(df["CANTIDAD_VACANTES"], errors="coerce")
    r.append(Resultado("CANTIDAD_VACANTES sin nulos y mayor que cero",
                       bool(plazas.notna().all() and (plazas > 0).all()),
                       f"{int(plazas.isna().sum())} nulos"))

    depto_ok = df["DEPARTAMENTO"].map(_normalizar).eq(config.DEPARTAMENTO_OBJETIVO).all()
    r.append(Resultado("Todas las vacantes son del departamento Tolima", bool(depto_ok)))

    fuera = df.loc[~df["MUNICIPIO"].map(_normalizar).isin(MUNICIPIOS_TOLIMA_NORM), "MUNICIPIO"]
    r.append(Resultado("Todos los municipios pertenecen al Tolima (47 municipios)",
                       fuera.empty, f"fuera de cobertura: {sorted(fuera.unique().tolist())}"))

    exp = pd.to_numeric(df["MESES_EXPERIENCIA_CARGO"], errors="coerce")
    r.append(Resultado(f"Experiencia sin valores > {config.MAX_MESES_EXPERIENCIA} meses",
                       not bool((exp > config.MAX_MESES_EXPERIENCIA).any()),
                       f"máximo: {exp.max() if exp.notna().any() else 'sin datos'}"))

    validos = {v for v in config.SALARIO_MAP.values() if pd.notna(v)}
    r.append(Resultado("SALARIO_ESTIMADO_NUM solo contiene valores del mapa definido",
                       bool(df["SALARIO_ESTIMADO_NUM"].dropna().isin(validos).all())))

    moji = contar_celdas_mojibake(df)
    r.append(Resultado("Sin mojibake residual en columnas de texto", moji == 0,
                       f"{moji} celdas con caracteres corruptos", critica=False))

    pub = pd.to_datetime(df["FECHA_PUBLICACION"], errors="coerce")
    ven = pd.to_datetime(df["FECHA_VENCIMIENTO"], errors="coerce")
    incoherentes = int((ven < pub).sum())
    r.append(Resultado("Coherencia temporal: vencimiento >= publicación", incoherentes == 0,
                       f"{incoherentes} vacantes incoherentes", critica=False))
    return r


def validar_dane(df: pd.DataFrame) -> list[Resultado]:
    """Validaciones de los indicadores DANE normalizados."""
    r: list[Resultado] = []

    r.append(Resultado("CONCEPTO y ANIO sin nulos",
                       bool(df[["CONCEPTO", "ANIO"]].notna().all().all())))
    r.append(Resultado("Un solo valor por (CONCEPTO, ANIO)",
                       not bool(df.duplicated(subset=["CONCEPTO", "ANIO"]).any()),
                       f"{int(df.duplicated(subset=['CONCEPTO', 'ANIO']).sum())} repetidos"))

    tasas = df.loc[df["TIPO_UNIDAD"] == "Porcentaje (%)", "VALOR"].dropna()
    r.append(Resultado("Tasas y porcentajes dentro del rango 0-100",
                       bool(tasas.between(0, 100).all()),
                       f"min={tasas.min():.2f}, max={tasas.max():.2f}" if len(tasas) else ""))

    pobl = df.loc[df["TIPO_UNIDAD"] == "Miles de personas", "VALOR"].dropna()
    r.append(Resultado("Volúmenes de población no negativos", bool((pobl >= 0).all())))

    nulos = int(df["VALOR"].isna().sum())
    r.append(Resultado("VALOR sin nulos", nulos == 0, f"{nulos} valores nulos", critica=False))

    anios = sorted(df["ANIO"].dropna().unique().tolist())
    continuo = bool(anios) and anios == list(range(int(anios[0]), int(anios[-1]) + 1))
    r.append(Resultado("Serie anual continua (sin años faltantes)", continuo,
                       f"{anios[0]}-{anios[-1]}" if anios else "", critica=False))
    return r


def validar_integracion(integrado: pd.DataFrame, vacantes: pd.DataFrame,
                        dane_anual: pd.DataFrame) -> list[Resultado]:
    """Validaciones del dataset integrado (vacantes + DANE)."""
    r: list[Resultado] = []

    r.append(Resultado("La integración no pierde ni duplica vacantes",
                       len(integrado) == len(vacantes),
                       f"vacantes={len(vacantes)}, integrado={len(integrado)}"))
    r.append(Resultado("CODIGO_VACANTE sigue siendo único tras integrar",
                       bool(integrado["CODIGO_VACANTE"].is_unique)))

    pareadas = integrado["ANIO_REFERENCIA_DANE"].isin(dane_anual["ANIO"])
    r.append(Resultado("Toda vacante encontró su año en el DANE", bool(pareadas.all()),
                       f"{int((~pareadas).sum())} sin pareja"))

    cols = [c for c in integrado.columns if c.startswith("DANE_")]
    esperado = (dane_anual.set_index("ANIO")
                .reindex(integrado["ANIO_REFERENCIA_DANE"].to_numpy())[cols]
                .to_numpy(dtype=float))
    real = integrado[cols].to_numpy(dtype=float)
    r.append(Resultado("Los indicadores DANE integrados coinciden con la fuente",
                       bool(np.allclose(real, esperado, equal_nan=True)),
                       f"{len(cols)} indicadores verificados"))

    nulos = int(integrado[cols].isna().sum().sum())
    r.append(Resultado("Sin nulos en los indicadores DANE integrados", nulos == 0,
                       f"{nulos} celdas nulas", critica=False))
    return r


# --------------------------------------------------------------------------
def validar_todo(vacantes, dane_tidy, integrado, dane_anual) -> list[Resultado]:
    return (validar_vacantes(vacantes) + validar_dane(dane_tidy)
            + validar_integracion(integrado, vacantes, dane_anual))


def imprimir_resultados(resultados: list[Resultado]) -> None:
    for res in resultados:
        extra = f" -> {res.detalle}" if res.detalle else ""
        print(f"[{res.estado}] {res.nombre}{extra}")
    ok = sum(r.ok for r in resultados)
    print(f"Validaciones aprobadas: {ok} de {len(resultados)}")


def exigir_criticas(resultados: list[Resultado]) -> None:
    """Lanza ValidacionError si alguna validación crítica falló."""
    fallos = [r for r in resultados if r.critica and not r.ok]
    if fallos:
        lista = "; ".join(r.nombre for r in fallos)
        raise ValidacionError(f"Fallaron {len(fallos)} validaciones críticas: {lista}")
