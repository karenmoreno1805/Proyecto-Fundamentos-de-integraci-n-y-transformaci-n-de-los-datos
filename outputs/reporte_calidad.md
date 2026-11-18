# Reporte de calidad del pipeline

_Generado automáticamente el 2026-11-17 23:31._

## 1. Vacantes (ComfaTolima): antes vs. después de limpiar

El 'después' se mide sobre todo el archivo ya limpio (T1-T3), antes de filtrar al Tolima.

| Métrica | Antes (crudo) | Después (limpio) |
|---|---:|---:|
| Filas totales | 1.000 | 998 |
| Filas totalmente duplicadas | 2 | 0 |
| Códigos de vacante duplicados | 2 | 0 |
| Celdas de texto con mojibake | 313 | 0 |
| Celdas con prefijo de sistema | 52 | 0 |
| Vacantes con experiencia > 120 meses | 164 | 0 |
| Experiencia máxima registrada (meses) | 999 | 120 |
| Atípicos de experiencia (criterio IQR) | 167 | 63 |
| Vacantes con salario 'A Convenir' | 186 | 186 |
| Ofertas del Tolima | 11 | 11 |
| Plazas de trabajo en el Tolima | 67 | 67 |

> Nota: 'A Convenir' se mantiene en el rango original, pero queda como nulo en `SALARIO_ESTIMADO_NUM` (no se inventa un salario).

## 2. Indicadores DANE: antes vs. después

| Métrica | Antes (matriz ancha) | Después (tidy) |
|---|---:|---:|
| Filas | 16 | 247 |
| Columnas | 20 | 4 |
| Filas totalmente nulas | 1 | 0 |
| Celdas nulas | 40 | 0 |
| Formato | Matriz ancha (una fila por indicador, una columna por año) | Tabla tidy (13 indicadores x 19 años) |

## 3. Validaciones (20 de 20 aprobadas)

| Estado | Validación | Detalle |
|---|---|---|
| OK | Existe al menos una vacante del Tolima | 11 vacantes |
| OK | CODIGO_VACANTE único y sin nulos (clave primaria) | 0 duplicados |
| OK | CANTIDAD_VACANTES sin nulos y mayor que cero | 0 nulos |
| OK | Todas las vacantes son del departamento Tolima |  |
| OK | Todos los municipios pertenecen al Tolima (47 municipios) | fuera de cobertura: [] |
| OK | Experiencia sin valores > 120 meses | máximo: 12 |
| OK | SALARIO_ESTIMADO_NUM solo contiene valores del mapa definido |  |
| OK | Sin mojibake residual en columnas de texto | 0 celdas con caracteres corruptos |
| OK | Coherencia temporal: vencimiento >= publicación | 0 vacantes incoherentes |
| OK | CONCEPTO y ANIO sin nulos |  |
| OK | Un solo valor por (CONCEPTO, ANIO) | 0 repetidos |
| OK | Tasas y porcentajes dentro del rango 0-100 | min=0.00, max=79.53 |
| OK | Volúmenes de población no negativos |  |
| OK | VALOR sin nulos | 0 valores nulos |
| OK | Serie anual continua (sin años faltantes) | 2007-2025 |
| OK | La integración no pierde ni duplica vacantes | vacantes=11, integrado=11 |
| OK | CODIGO_VACANTE sigue siendo único tras integrar |  |
| OK | Toda vacante encontró su año en el DANE | 0 sin pareja |
| OK | Los indicadores DANE integrados coinciden con la fuente | 13 indicadores verificados |
| OK | Sin nulos en los indicadores DANE integrados | 0 celdas nulas |

## 4. Resultado final

| Dato | Valor |
|---|---:|
| Vacantes del Tolima (filas) | 11 |
| Plazas de trabajo en el Tolima | 67 |
| Registros DANE normalizados | 247 |
| Filas del dataset integrado | 11 |
| Columnas del dataset integrado | 36 |
