"""Pruebas del pipeline. Ejecutar desde la raíz del repo:

    python -m unittest discover tests -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datos_prueba as dp  # noqa: E402
from main import ejecutar_pipeline  # noqa: E402
from src import config, integracion, limpieza, validacion  # noqa: E402


class TestT1Encoding(unittest.TestCase):
    def test_corrige_variantes_de_mojibake(self):
        casos = {
            "ALMACÃ‰N": "ALMACÉN",                      # reversión exacta
            "ingenierÃ­a civil": "ingeniería civil",
            "VEHÃ�CULO": "VEHÍCULO",           # byte perdido -> tabla de reemplazos
            "VEHÃ\x8dCULO": "VEHÍCULO",             # variante con byte de control
            "$hNo Codigo vacante$ Vendedor": "Vendedor",  # prefijo de sistema
            "ZAPATERÃ­a y Ã±andÃº": "ZAPATERía y ñandú",
        }
        for malo, esperado in casos.items():
            self.assertEqual(limpieza.corregir_texto(malo), esperado)

    def test_no_toca_texto_correcto_ni_nulos(self):
        self.assertEqual(limpieza.corregir_texto("IBAGUÉ - Año nuevo"), "IBAGUÉ - Año nuevo")
        self.assertTrue(np.isnan(limpieza.corregir_texto(np.nan)))

    def test_t1_sobre_dataframe(self):
        df = limpieza.t1_corregir_encoding(dp.crear_comfatolima_prueba())
        self.assertEqual(df.loc[0, "TITULO_VACANTE"], "AUXILIAR DE BODEGA/ALMACÉN (MELGAR)")
        self.assertEqual(df.loc[2, "TITULO_VACANTE"], "Vendedor de minimercado")
        self.assertEqual(df.loc[3, "SECTOR_ECONOMICO"], "Obras de ingeniería civil")


class TestT2T3T5(unittest.TestCase):
    def setUp(self):
        self.raw = dp.crear_comfatolima_prueba()

    def test_t2_elimina_duplicados_y_outliers(self):
        out = limpieza.t2_deduplicar_y_tratar_outliers(self.raw)
        self.assertEqual(len(out), len(self.raw) - 1)
        self.assertTrue(out["CODIGO_VACANTE"].is_unique)
        self.assertTrue(pd.isna(out.loc[0, "MESES_EXPERIENCIA_CARGO"]))   # 999 -> nulo
        self.assertTrue(pd.isna(out.loc[1, "MESES_EXPERIENCIA_CARGO"]))   # 150 -> nulo
        self.assertEqual(out["MESES_EXPERIENCIA_CARGO"].max(), 36)

    def test_t2_no_modifica_el_original(self):
        copia = self.raw.copy()
        limpieza.t2_deduplicar_y_tratar_outliers(self.raw)
        pd.testing.assert_frame_equal(self.raw, copia)

    def test_t3_salario_numerico(self):
        out = limpieza.t3_estandarizar_salario(self.raw)
        self.assertEqual(out.loc[0, "SALARIO_ESTIMADO_NUM"], 1250000)
        self.assertTrue(np.isnan(out.loc[5, "SALARIO_ESTIMADO_NUM"]))     # 'A Convenir'
        self.assertEqual(str(out["SALARIO_ESTIMADO_NUM"].dtype), "float64")

    def test_t5_solo_tolima(self):
        out = limpieza.t5_segmentar_tolima(limpieza.limpiar_comfatolima(self.raw))
        self.assertEqual(len(out), dp.N_TOLIMA)
        self.assertTrue((out["DEPARTAMENTO"] == "TOLIMA").all())


class TestT4Dane(unittest.TestCase):
    def test_formato_tidy(self):
        raw = dp.crear_dane_prueba()
        tidy = limpieza.t4_normalizar_dane(raw)
        self.assertEqual(list(tidy.columns), ["CONCEPTO", "ANIO", "VALOR", "TIPO_UNIDAD"])
        self.assertEqual(tidy["CONCEPTO"].nunique(), 13)
        self.assertEqual(tidy["ANIO"].nunique(), 19)
        self.assertEqual(len(tidy), 13 * 19)
        self.assertNotIn("Concepto", tidy["CONCEPTO"].tolist())
        self.assertFalse(tidy["VALOR"].isna().any())
        unidad = tidy.drop_duplicates("CONCEPTO").set_index("CONCEPTO")["TIPO_UNIDAD"]
        self.assertEqual(unidad["Tasa de Desocupación (TD)"], "Porcentaje (%)")
        self.assertEqual(unidad["Población total"], "Miles de personas")

    def test_falla_con_mensaje_claro_si_cambia_el_formato(self):
        with self.assertRaises(ValueError):
            limpieza.t4_normalizar_dane(pd.DataFrame({"Tolima": ["a", "b"], "x": [1, 2]}))


class TestIntegracion(unittest.TestCase):
    def setUp(self):
        comfa = limpieza.limpiar_comfatolima(dp.crear_comfatolima_prueba())
        self.vacantes = limpieza.t5_segmentar_tolima(comfa)
        self.dane = limpieza.t4_normalizar_dane(dp.crear_dane_prueba())

    def test_nombres_de_columnas_dane(self):
        self.assertEqual(integracion.nombre_columna_dane("Tasa de Desocupación (TD)"), "DANE_TD")
        self.assertEqual(integracion.nombre_columna_dane("% población en edad de trabajar"),
                         "DANE_PCT_POBLACION_EN_EDAD_DE_TRABAJAR")
        self.assertEqual(integracion.nombre_columna_dane("Fuerza de trabajo "), "DANE_FUERZA_DE_TRABAJO")

    def test_integracion_conserva_filas_y_usa_ultimo_anio(self):
        integrado, anual = integracion.integrar(self.vacantes, self.dane)
        self.assertEqual(len(integrado), len(self.vacantes))
        self.assertTrue(integrado["CODIGO_VACANTE"].is_unique)
        # vacantes de 2026, DANE llega a 2025 -> se usa 2025
        self.assertEqual(set(integrado["ANIO_REFERENCIA_DANE"]), {2025})
        esperado = anual.loc[anual["ANIO"] == 2025, "DANE_TD"].iloc[0]
        self.assertTrue((integrado["DANE_TD"] == esperado).all())

    def test_todas_las_validaciones_pasan(self):
        integrado, anual = integracion.integrar(self.vacantes, self.dane)
        res = validacion.validar_todo(self.vacantes, self.dane, integrado, anual)
        fallidas = [r.nombre for r in res if not r.ok]
        self.assertEqual(fallidas, [])


class TestValidacionesDetectanErrores(unittest.TestCase):
    """Prueba negativa: las validaciones deben FALLAR cuando los datos están mal."""

    def setUp(self):
        comfa = limpieza.limpiar_comfatolima(dp.crear_comfatolima_prueba())
        self.vacantes = limpieza.t5_segmentar_tolima(comfa)
        self.dane = limpieza.t4_normalizar_dane(dp.crear_dane_prueba())
        self.integrado, self.anual = integracion.integrar(self.vacantes, self.dane)

    def _fallos(self, vacantes=None, dane=None, integrado=None):
        res = validacion.validar_todo(
            self.vacantes if vacantes is None else vacantes,
            self.dane if dane is None else dane,
            self.integrado if integrado is None else integrado,
            self.anual,
        )
        return {r.nombre for r in res if not r.ok and r.critica}

    def test_detecta_codigo_duplicado(self):
        malo = pd.concat([self.vacantes, self.vacantes.iloc[[0]]], ignore_index=True)
        self.assertIn("CODIGO_VACANTE único y sin nulos (clave primaria)", self._fallos(vacantes=malo))

    def test_detecta_municipio_fuera_del_tolima(self):
        malo = self.vacantes.copy()
        malo.loc[0, "MUNICIPIO"] = "MEDELLÍN"
        self.assertIn("Todos los municipios pertenecen al Tolima (47 municipios)", self._fallos(vacantes=malo))

    def test_detecta_tasa_imposible(self):
        malo = self.dane.copy()
        malo.loc[malo["TIPO_UNIDAD"] == "Porcentaje (%)", "VALOR"] = 150
        self.assertIn("Tasas y porcentajes dentro del rango 0-100", self._fallos(dane=malo))

    def test_detecta_integracion_que_duplica_filas(self):
        malo = pd.concat([self.integrado, self.integrado.iloc[[0]]], ignore_index=True)
        self.assertIn("La integración no pierde ni duplica vacantes", self._fallos(integrado=malo))

    def test_exigir_criticas_lanza_error(self):
        malo = pd.concat([self.vacantes, self.vacantes.iloc[[0]]], ignore_index=True)
        res = validacion.validar_vacantes(malo)
        with self.assertRaises(validacion.ValidacionError):
            validacion.exigir_criticas(res)


class TestPipelineExtremoAExtremo(unittest.TestCase):
    def test_python_main_con_archivos_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            dp.guardar_excel_prueba(tmp / "raw")
            res = ejecutar_pipeline(tmp / "raw", tmp / "processed", tmp / "outputs")

            for ruta in [tmp / "processed" / config.SALIDA_VACANTES,
                         tmp / "processed" / config.SALIDA_DANE,
                         tmp / "outputs" / config.SALIDA_INTEGRADO,
                         tmp / "outputs" / config.SALIDA_REPORTE]:
                self.assertTrue(ruta.exists(), f"No se generó {ruta.name}")

            leido = pd.read_csv(tmp / "outputs" / config.SALIDA_INTEGRADO)
            self.assertEqual(len(leido), dp.N_TOLIMA)
            self.assertIn("DANE_TD", leido.columns)
            self.assertFalse(leido["DANE_TD"].isna().any())
            self.assertTrue(all(r.ok for r in res["resultados"]))
            reporte = (tmp / "outputs" / config.SALIDA_REPORTE).read_text(encoding="utf-8")
            self.assertIn("Validaciones", reporte)

    def test_mensaje_claro_si_faltan_los_archivos(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError) as ctx:
                ejecutar_pipeline(Path(tmp) / "vacia", Path(tmp) / "p", Path(tmp) / "o")
            self.assertIn("data/raw", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
