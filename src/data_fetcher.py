import requests
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

COLUMNAS_MODELO = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']

OPENMETEO_VARIABLES = {
    'Temperatura': 'temperature_2m',
    'HumedadRelativa': 'relativehumidity_2m',
    'PresionAtmosferica': 'surface_pressure', # en Pa, el modelo debe estar entrenado con esto o se necesita conversión
    'HumedadSuelo': 'soil_moisture_0_to_7cm', # m³/m³
    'PrecipitacionMM': 'precipitation_sum' # mm
}

COLUMNAS_A_SOLICITAR_API = list(OPENMETEO_VARIABLES.keys())


def obtener_datos_meteorologicos_openmeteo(latitud: float, longitud: float, dias_prediccion: int = 1):
    """
    Obtiene datos meteorológicos horarios de la API de Open-Meteo para una ubicación y número de días dados.

    Args:
        latitud (float): Latitud de la ubicación.
        longitud (float): Longitud de la ubicación.
        dias_prediccion (int): Número de días de pronóstico a obtener (1 a 16).

    Returns:
        pandas.DataFrame: Un DataFrame con los datos meteorológicos horarios,
                          con columnas 'time', 'Temperatura', 'HumedadRelativa',
                          'PresionAtmosferica', 'HumedadSuelo'.
                          Retorna None si ocurre un error.
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitud,
        "longitude": longitud,
        "hourly": ",".join(OPENMETEO_VARIABLES.values()),
        "forecast_days": dias_prediccion,
        "timezone": "auto"
    }

    try:
        logger.info(f"Solicitando datos a Open-Meteo API: {base_url} con params: {params}")
        response = requests.get(base_url, params=params, timeout=10) 
        response.raise_for_status() 
        data = response.json()
        logger.info(f"Datos recibidos de Open-Meteo para {latitud},{longitud}.")

        if 'hourly' not in data or 'time' not in data['hourly']:
            logger.error("Respuesta de Open-Meteo no contiene datos horarios 'hourly' o 'time'.")
            return None

        hourly_data = data['hourly']
        df = pd.DataFrame(hourly_data)

        # Convertir 'time' a datetime objects
        df['time'] = pd.to_datetime(df['time'])

        # Renombrar columnas según nuestro mapeo
        rename_map = {v: k for k, v in OPENMETEO_VARIABLES.items()}
        df.rename(columns=rename_map, inplace=True)

        columnas_presentes_en_df = [col for col in COLUMNAS_A_SOLICITAR_API if col in df.columns]
        columnas_finales_df = ['time'] + columnas_presentes_en_df
        df = df[columnas_finales_df]

        for col_modelo in COLUMNAS_MODELO:
            if col_modelo not in df.columns:
                # Si HumedadSuelo no está, es esperado. Para otras, es un problema.
                if col_modelo == 'HumedadSuelo':
                    logger.info(f"La columna '{col_modelo}' no fue encontrada en los datos de Open-Meteo y será estimada.")
                    df[col_modelo] = pd.NA 
                else:
                    logger.warning(f"La columna '{col_modelo}' esperada por el modelo no fue encontrada en los datos de Open-Meteo.")
        
        # Verificar si PrecipitacionMM está presente, ya que es necesaria para la estimación
        if 'PrecipitacionMM' not in df.columns:
            logger.warning("La columna 'PrecipitacionMM' necesaria para estimar HumedadSuelo no fue encontrada en los datos de Open-Meteo.")
            # Podríamos añadirla con pd.NA o 0 si queremos que la estimación proceda con un default para precipitación
            df['PrecipitacionMM'] = 0.0 # O pd.NA, si la función de estimación lo maneja
            logger.info("Se añadió 'PrecipitacionMM' con valores por defecto (0.0) debido a su ausencia en la API.")


        logger.info(f"DataFrame procesado de Open-Meteo con {len(df)} filas y columnas: {df.columns.tolist()}")
        # Ejemplo de inspección de datos:
        # logger.info(f"Primeras filas del DataFrame devuelto por data_fetcher:\n{df.head().to_string()}")
        return df

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Error HTTP al contactar Open-Meteo: {http_err} - Response: {response.text if response else 'No response'}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Error de conexión al contactar Open-Meteo: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout al contactar Open-Meteo: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error inesperado de requests al contactar Open-Meteo: {req_err}")
    except ValueError as json_err: # Incluye JSONDecodeError
        logger.error(f"Error al decodificar JSON de Open-Meteo: {json_err}")
    except KeyError as key_err:
        logger.error(f"Error de clave al procesar respuesta de Open-Meteo (faltan datos esperados): {key_err}")
    except Exception as e:
        logger.error(f"Error inesperado en obtener_datos_meteorologicos_openmeteo: {e}", exc_info=True)

    return None

if __name__ == '__main__':
    # Ejemplo de uso (para pruebas directas del script)
    logging.basicConfig(level=logging.INFO)
    logger.info("Probando data_fetcher directamente...")
    # Coordenadas para Patala, Pucará, Huancayo, Junín, Perú
    lat_pucara = -12.20892
    lon_pucara = -75.07791
    
    datos_df = obtener_datos_meteorologicos_openmeteo(lat_pucara, lon_pucara, dias_prediccion=2)

    if datos_df is not None:
        print("\nDatos meteorológicos obtenidos:")
        print(datos_df.head())
        print(f"\nForma del DataFrame: {datos_df.shape}")
        print(f"\nColumnas: {datos_df.columns.tolist()}")
        print(f"\nTipos de datos:\n{datos_df.dtypes}")

        manana_inicio = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        manana_madrugada_fin = manana_inicio.replace(hour=6)

        print(f"\nFiltrando para mañana entre {manana_inicio} y {manana_madrugada_fin}")

        datos_madrugada_manana = datos_df[
             (datos_df['time'].dt.date == manana_inicio.date()) & \
             (datos_df['time'].dt.hour >= 0) & \
             (datos_df['time'].dt.hour <= 6)
        ]

        if not datos_madrugada_manana.empty:
            print("\nDatos para la madrugada de mañana (00:00 - 06:00):")
            print(datos_madrugada_manana)
            prediccion_target_data = datos_madrugada_manana.iloc[0]
            print("\nFila de datos para la predicción (primera hora de la madrugada):")
            print(prediccion_target_data[COLUMNAS_MODELO])
        else:
            print("\nNo se encontraron datos para la madrugada de mañana en el rango especificado.")
            print(f"Rango buscado: {manana_inicio.date()} de 00:00 a 06:00.")
            print(f"Primeras fechas en datos_df: {datos_df['time'].head(5)}")
            print(f"Últimas fechas en datos_df: {datos_df['time'].tail(5)}")

    else:
        print("No se pudieron obtener datos meteorológicos.")
