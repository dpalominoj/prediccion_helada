# coding: utf-8
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import requests # Import requests
from datetime import datetime
import sys
import os

# Add project root to sys.path to allow importing src.data_fetcher
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.data_fetcher import obtener_datos_meteorologicos_openmeteo, COLUMNAS_MODELO, OPENMETEO_VARIABLES

class TestDataFetcher(unittest.TestCase):

    @patch('src.data_fetcher.requests.get')
    def test_obtener_datos_meteorologicos_openmeteo_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "latitude": -12.20892,
            "longitude": -75.07791,
            "hourly": {
                "time": ["2023-01-01T00:00", "2023-01-01T01:00"],
                OPENMETEO_VARIABLES['Temperatura']: [10.0, 10.5],
                OPENMETEO_VARIABLES['HumedadRelativa']: [50.0, 52.0],
                OPENMETEO_VARIABLES['PresionAtmosferica']: [101200.0, 101250.0], # Pa
                OPENMETEO_VARIABLES['HumedadSuelo']: [0.3, 0.31] # m³/m³
            }
        }
        mock_get.return_value = mock_response

        lat = -12.20892
        lon = -75.07791
        df = obtener_datos_meteorologicos_openmeteo(lat, lon, dias_prediccion=1)

        self.assertIsNotNone(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertListEqual(list(df.columns), ['time'] + COLUMNAS_MODELO)

        # Check dtypes
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['time']))
        for col in COLUMNAS_MODELO:
            self.assertTrue(pd.api.types.is_numeric_dtype(df[col]))

        # Check values
        self.assertEqual(df['Temperatura'].iloc[0], 10.0)
        self.assertEqual(df['HumedadSuelo'].iloc[1], 0.31)
        mock_get.assert_called_once()

    @patch('src.data_fetcher.requests.get')
    def test_obtener_datos_meteorologicos_openmeteo_api_error(self, mock_get):
        # Mock API error (e.g., 404 Not Found)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        mock_get.return_value = mock_response

        df = obtener_datos_meteorologicos_openmeteo(-12.20892, -75.07791, 1)
        self.assertIsNone(df)
        mock_get.assert_called_once()

    @patch('src.data_fetcher.requests.get')
    def test_obtener_datos_meteorologicos_openmeteo_missing_data(self, mock_get):
        # Mock successful API response but with some expected variables missing
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "latitude": -12.20892,
            "longitude": -75.07791,
            "hourly": {
                "time": ["2023-01-01T00:00"],
                OPENMETEO_VARIABLES['Temperatura']: [10.0],
                # HumedadRelativa is missing
                OPENMETEO_VARIABLES['PresionAtmosferica']: [101200.0],
                OPENMETEO_VARIABLES['HumedadSuelo']: [0.3]
            }
        }
        mock_get.return_value = mock_response

        df = obtener_datos_meteorologicos_openmeteo(-12.20892, -75.07791, 1)

        self.assertIsNotNone(df)
        self.assertIn('Temperatura', df.columns)
        self.assertIn('PresionAtmosferica', df.columns)
        self.assertIn('HumedadSuelo', df.columns)
        # 'HumedadRelativa' was not in the response, so it shouldn't be a column
        # unless we explicitly add it with NaNs. The current implementation filters.
        # The plan was: "Las columnas que no estén en la respuesta de Open-Meteo (si alguna) quedarán como NaN
        # o se podría optar por eliminarlas o rellenarlas si es necesario.
        # Por ahora, solo seleccionamos las que sí están en COLUMNAS_MODELO y fueron solicitadas."
        # And then: "Verificar si faltan columnas esperadas" - this logs a warning.
        # The returned df will only have columns that were present in the API response and mapped.
        self.assertNotIn('HumedadRelativa', df.columns)

        # Test that the function logs a warning for missing columns (optional, advanced test)
        # with self.assertLogs(logger='src.data_fetcher', level='WARNING') as cm:
        #     df = obtener_datos_meteorologicos_openmeteo(-12.20892, -75.07791, 1)
        # self.assertTrue(any("La columna 'HumedadRelativa' esperada" in message for message in cm.output))


    @patch('src.data_fetcher.requests.get')
    def test_obtener_datos_meteorologicos_openmeteo_connection_error(self, mock_get):
        # Mock requests.get to raise a ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        df = obtener_datos_meteorologicos_openmeteo(-12.20892, -75.07791, 1)
        self.assertIsNone(df)
        mock_get.assert_called_once()

if __name__ == '__main__':
    unittest.main()
