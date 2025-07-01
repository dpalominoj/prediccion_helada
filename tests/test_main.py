# coding: utf-8
import unittest
from unittest.mock import patch, MagicMock, ANY
import pandas as pd
from datetime import datetime, date, time, timezone
import json
import sys
import os

# Add project root to sys.path to allow importing main and src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Before importing main, set FLASK_DEBUG to prevent server from running if tests are run directly
os.environ['FLASK_DEBUG'] = 'False'
# Also, use a temporary, in-memory SQLite DB for tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import main # Import the Flask app
from database.database import init_db, get_db, Base
from database.models import Prediccion, ResultadoPrediccion, IntensidadHelada
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


# Global test engine and session
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:" # In-memory SQLite for tests
test_engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine) # Not strictly needed if app uses its own session management based on config

# def override_get_db(): # Not needed for Flask in this way
#     """Dependency override for FastAPI to use the test database."""
#     try:
#         db = TestSessionLocal()
#         yield db
#     finally:
#         db.close()

class TestMainApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create all tables in the in-memory database
        # This test_engine is separate from the one the app uses but points to the same in-memory DB
        # if os.environ['DATABASE_URL'] is set correctly before main import.
        # The app's own init_db() should handle table creation if main.py is structured for it.
        # Call main.init_db() to ensure tables are created using the app's engine configured for tests.
        main.init_db()
        # Base.metadata.create_all(bind=test_engine) # Optional: if test_engine is different from app's engine

        # Mock the prediction model as it's loaded globally in main.py
        cls.mock_model = MagicMock()
        cls.mock_model.predict.return_value = [0] # No helada
        cls.mock_model.predict_proba.return_value = [[0.9, 0.1]] # 10% prob de helada

        cls.model_patcher = patch('main.prediction_model', cls.mock_model)
        cls.model_patcher.start()
        main.prediction_model = cls.mock_model # Ensure the app instance uses the mock


    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        cls.model_patcher.stop()
        # main.app.dependency_overrides.clear() # Not needed


    def setUp(self):
        """Executed before each test."""
        self.app = main.app.test_client()
        # Clear all data from tables before each test
        # Use the main.get_db() which should now be configured for the test DB
        # The main.py's init_db() should have created tables on the in-memory DB
        # because DATABASE_URL was set prior to its import.
        db: Session = next(main.get_db())
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        db.close()
        # Reset mocks if they are per-test
        self.mock_model.reset_mock()
        self.mock_model.predict.return_value = [0]
        self.mock_model.predict_proba.return_value = [[0.9, 0.1]]


    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("GUI prediccion de helada", response.data.decode('utf-8'))

    @patch('main.obtener_datos_meteorologicos_openmeteo')
    def test_pronostico_automatico_success(self, mock_fetch_data):
        # Mock data_fetcher to return sample data
        sample_time_str = (datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)).isoformat()

        mock_df = pd.DataFrame({
            'time': pd.to_datetime([sample_time_str]),
            'Temperatura': [1.0],
            'HumedadRelativa': [80.0],
            'PresionAtmosferica': [101000.0],
            'HumedadSuelo': [0.25]
        })
        mock_fetch_data.return_value = mock_df

        # Setup model prediction for "helada leve"
        self.mock_model.predict.return_value = [1] # Helada
        self.mock_model.predict_proba.return_value = [[0.4, 0.6]] # 60% prob de helada

        response = self.app.get('/pronostico_automatico')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn("id", data)
        self.assertEqual(data["resultado"], ResultadoPrediccion.probable.value) # probable
        self.assertEqual(data["intensidad"], IntensidadHelada.leve.value) # leve
        self.assertEqual(data["temperatura_pronosticada"], 1.0)
        mock_fetch_data.assert_called_once_with(-12.20892, -75.07791, dias_prediccion=2)
        self.mock_model.predict.assert_called_once()
        self.mock_model.predict_proba.assert_called_once()

        # Verify data saved in DB
        db_session = next(main.get_db())
        pred_record = db_session.query(Prediccion).first()
        self.assertIsNotNone(pred_record)
        self.assertEqual(pred_record.temperatura_minima_prevista, 1.0)
        self.assertEqual(pred_record.resultado, ResultadoPrediccion.probable)
        self.assertEqual(pred_record.intensidad, IntensidadHelada.leve)
        db_session.close()

    @patch('main.obtener_datos_meteorologicos_openmeteo')
    def test_pronostico_automatico_no_data_from_fetcher(self, mock_fetch_data):
        mock_fetch_data.return_value = None # Simulate fetcher returning None
        response = self.app.get('/pronostico_automatico')
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn("No se pudieron obtener datos meteorológicos externos", data["error"])

    @patch('main.obtener_datos_meteorologicos_openmeteo')
    def test_pronostico_automatico_empty_df_from_fetcher(self, mock_fetch_data):
        mock_fetch_data.return_value = pd.DataFrame() # Simulate fetcher returning empty DataFrame
        response = self.app.get('/pronostico_automatico')
        self.assertEqual(response.status_code, 503) # Or whatever error for empty df
        data = json.loads(response.data)
        self.assertIn("No se pudieron obtener datos meteorológicos externos", data["error"])


    @patch('main.obtener_datos_meteorologicos_openmeteo')
    def test_pronostico_automatico_no_target_hour_data(self, mock_fetch_data):
        # Simulate fetcher returns data, but not for the target hour/range
        # Example: data only for today, not for tomorrow's madrugada
        today_3am_iso = datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0).isoformat()
        mock_df = pd.DataFrame({
            'time': pd.to_datetime([today_3am_iso]), # Only today's data
            'Temperatura': [1.0], 'HumedadRelativa': [80.0],
            'PresionAtmosferica': [101000.0], 'HumedadSuelo': [0.25]
        })
        mock_fetch_data.return_value = mock_df
        response = self.app.get('/pronostico_automatico')
        self.assertEqual(response.status_code, 404) # Not Found, as specific data for future not available
        data = json.loads(response.data)
        self.assertIn("No se encontraron datos para la madrugada", data["error"])


    def test_ver_registros_api_no_data(self):
        response = self.app.get('/registros')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)

    def test_ver_registros_api_with_data(self):
        # Add some data to the test DB
        db_session = next(main.get_db())
        pred1 = Prediccion(
            fecha_prediccion_para=datetime.now(timezone.utc),
            ubicacion="Test Loc 1", estacion_meteorologica="Test Station 1",
            temperatura_minima_prevista=0.5, probabilidad_helada=0.7,
            resultado=ResultadoPrediccion.probable, intensidad=IntensidadHelada.moderada,
            duracion_estimada_horas=2.0, parametros_entrada='{}', fuente_datos_entrada='test'
        )
        db_session.add(pred1)
        db_session.commit()
        db_session.close()

        response = self.app.get('/registros')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["ubicacion"], "Test Loc 1")
        self.assertEqual(data[0]["intensidad"], IntensidadHelada.moderada.value)


    def test_ver_registros_ui(self):
        # Add some data to the test DB
        db_session = next(main.get_db())
        pred1 = Prediccion(
            fecha_prediccion_para=datetime.now(timezone.utc),
            ubicacion="Test Loc UI", estacion_meteorologica="Test Station UI",
            temperatura_minima_prevista=-1.0, probabilidad_helada=0.8,
            resultado=ResultadoPrediccion.probable, intensidad=IntensidadHelada.fuerte,
            duracion_estimada_horas=3.0, parametros_entrada='{}', fuente_datos_entrada='test_ui'
        )
        db_session.add(pred1)
        db_session.commit()
        db_session.close()

        response = self.app.get('/registros_ui')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Loc UI", response.data)
        self.assertIn(b"Fuerte", response.data) # Assuming 'Fuerte' is the value for IntensidadHelada.fuerte

    def test_model_not_loaded_pronostico(self):
        with patch('main.prediction_model', None): # Simulate model not loaded
             main.prediction_model = None # Critical to re-assign after patch context if it's module global
             response = self.app.get('/pronostico_automatico')
             self.assertEqual(response.status_code, 500)
             data = json.loads(response.data)
             self.assertIn("Modelo de predicción no disponible", data["error"])
        main.prediction_model = self.mock_model # Restore for other tests


if __name__ == '__main__':
    # Important: If running this test file directly, ensure main.py does not app.run() when imported.
    # The FLASK_DEBUG=False or some other mechanism should prevent that.
    # Typically, tests are run via a test runner like `python -m unittest discover tests`
    unittest.main()
