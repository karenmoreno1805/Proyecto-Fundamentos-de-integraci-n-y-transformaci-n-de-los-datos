# Diccionario de datos

## 1. Fuente DANE (`dane.xlsx`, hoja `Hoja1`)

Formato original: matriz ancha. Una fila por indicador, una columna por año (2007-2025), con filas vacías separadoras.

| Variable | Tipo original | Tipo sugerido | Descripción | Valores observados |
|---|---|---|---|---|
| Concepto | texto | string | Indicador macroeconómico del mercado laboral | Tasas (TGP, TO, TD, TS) y volúmenes de población |
| 2007 ... 2025 | float64 | float64 | Valor del indicador para cada año | Tasas en %; población en miles de personas |

### Después de T4 (`Fact_Indicadores_DANE_Tolima_Limpio.csv`)

| Columna | Tipo | Descripción |
|---|---|---|
| CONCEPTO | string | Nombre del indicador |
| ANIO | int | Año del dato (llave de integración) |
| VALOR | float | Valor del indicador |
| TIPO_UNIDAD | string | `Porcentaje (%)` o `Miles de personas` |

## 2. Fuente ComfaTolima (`COMFATOLIMA.xlsx`)

| Variable | Tipo original | Tipo sugerido | Descripción | Ejemplo observado |
|---|---|---|---|---|
| CODIGO_VACANTE | object | string | Identificador único de la oferta laboral pública (clave primaria) | "1626033383-227", "66781746" |
| TITULO_VACANTE | object | string | Título del puesto publicado | "CONDUCTOR DE VEHÍCULO LIVIANO" |
| DESCRIPCION_VACANTE | object | text | Detalle de requisitos y funciones | Texto en lenguaje natural |
| NIVEL_ESTUDIOS | object | category | Nivel educativo mínimo requerido | Media, Técnico, Universitarios, No Aplica |
| RANGO_SALARIAL | object | category | Banda de remuneración mensual | "$1.500.001 - $2.000.000", "A Convenir" |
| NOMBRE_PRESTADOR | object | category | Entidad gestora de la publicación | CAJA DE COMPENSACIÓN FAMILIAR, COMPUTRABAJO |
| DEPARTAMENTO | object | category | Departamento de la oferta | BOGOTÁ, D.C., ANTIOQUIA, TOLIMA |
| MUNICIPIO | object | category | Municipio de la vacante | IBAGUÉ, ESPINAL, HONDA, MELGAR |
| TIPO_CONTRATO | object | category | Modalidad de contratación | Por obra o labor, Término fijo, Término indefinido |
| URL_DETALLE_VACANTE | object | string | Enlace a la publicación | URL del portal de empleo |
| CANTIDAD_VACANTES | int64 | int | Número de plazas de la oferta | 1, 2, 30 |
| CARGO | object | string | Denominación estandarizada del cargo | "Supervisor de consumo masivo" |
| FECHA_PUBLICACION | datetime64 | datetime | Fecha en que se habilitó la vacante | 2026-10-29 |
| FECHA_VENCIMIENTO | datetime64 | datetime | Fecha límite para postularse | 2026-10-30 a 2027-04-27 |
| SECTOR_ECONOMICO | object | category | Sector productivo del oferente | Publicidad / RRPP, Obras de ingeniería civil |
| TELETRABAJO | int64 | boolean | 1 si admite trabajo remoto | 0 (No), 1 (Sí) |
| DISCAPACIDAD | int64 | boolean | 1 si es vacante inclusiva | 0 (No), 1 (Sí) |
| MESES_EXPERIENCIA_CARGO | int64 | int | Experiencia previa exigida (meses) | Hasta 999 (outlier en el crudo) |
| HIDROCARBUROS | int64 | boolean | 1 si pertenece al sector hidrocarburos | 0 (No), 1 (Sí) |
| PLAZA_PRACTICA | int64 | boolean | 1 si es contrato de aprendizaje/práctica | 0 (No), 1 (Sí) |

## 3. Columnas que agrega el pipeline

| Columna | Dataset | Origen | Descripción |
|---|---|---|---|
| SALARIO_ESTIMADO_NUM | Vacantes y integrado | T3 | Punto medio del rango salarial en pesos colombianos. Nulo si el salario es "A Convenir" |
| ANIO_PUBLICACION | Integrado | Integración | Año de `FECHA_PUBLICACION` |
| ANIO_REFERENCIA_DANE | Integrado | Integración | Año del DANE usado para esa vacante (el año de publicación, o el último disponible si el DANE aún no lo publica) |
| DANE_TGP, DANE_TO, DANE_TD, DANE_TS | Integrado | Integración | Tasa Global de Participación, de Ocupación, de Desocupación y de Subocupación (%) |
| DANE_PET y demás `DANE_*` | Integrado | Integración | Un indicador del DANE por columna (población en miles de personas, fuerza de trabajo, etc.) |

## 4. Notas

- En el dataset limpio, `MESES_EXPERIENCIA_CARGO` es un entero con nulos: los valores mayores a 120 meses se convierten en nulo (T2).
- Los textos de las columnas `TITULO_VACANTE`, `CARGO`, `SECTOR_ECONOMICO` y otras columnas de texto ya vienen con la codificación corregida (T1).
