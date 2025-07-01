# coding: utf-8
import requests
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Estas son las columnas que el modelo espera, según main.py (COLUMNAS_FEATURES_PREDICCION)
# Asegurémonos de que el DataFrame devuelto por obtener_datos_meteorologicos_openmeteo
# tenga estas columnas con los nombres correctos.
COLUMNAS_MODELO = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']

# Mapeo de nuestras columnas a las variables de Open-Meteo
OPENMETEO_VARIABLES = {
    'Temperatura': 'temperature_2m',
    'HumedadRelativa': 'relativehumidity_2m',
    'PresionAtmosferica': 'surface_pressure', # en Pa, el modelo debe estar entrenado con esto o se necesita conversión
    'HumedadSuelo': 'soil_moisture_0_to_7cm' # m³/m³
}

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
        "timezone": "auto" # Opcional: America/Lima si es específico para Perú
    }

    try:
        logger.info(f"Solicitando datos a Open-Meteo API: {base_url} con params: {params}")
        response = requests.get(base_url, params=params, timeout=10) # 10 segundos de timeout
        response.raise_for_status()  # Lanza HTTPError para respuestas 4XX/5XX
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

        # Asegurar que todas las COLUMNAS_MODELO están presentes
        # Las columnas que no estén en la respuesta de Open-Meteo (si alguna) quedarán como NaN
        # o se podría optar por eliminarlas o rellenarlas si es necesario.
        # Por ahora, solo seleccionamos las que sí están en COLUMNAS_MODELO y fueron solicitadas.
        columnas_finales = ['time'] + [col for col in COLUMNAS_MODELO if col in df.columns]
        df = df[columnas_finales]

        # Verificar si faltan columnas esperadas
        for col in COLUMNAS_MODELO:
            if col not in df.columns:
                logger.warning(f"La columna '{col}' esperada por el modelo no fue encontrada en los datos de Open-Meteo.")
                # Opcional: df[col] = pd.NA o algún valor por defecto si el modelo lo requiere siempre

        logger.info(f"DataFrame procesado de Open-Meteo con {len(df)} filas y columnas: {df.columns.tolist()}")
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

    # Obtener datos para hoy y mañana (2 días para tener el día siguiente completo)
    datos_df = obtener_datos_meteorologicos_openmeteo(lat_pucara, lon_pucara, dias_prediccion=2)

    if datos_df is not None:
        print("\nDatos meteorológicos obtenidos:")
        print(datos_df.head())
        print(f"\nForma del DataFrame: {datos_df.shape}")
        print(f"\nColumnas: {datos_df.columns.tolist()}")
        print(f"\nTipos de datos:\n{datos_df.dtypes}")

        # Ejemplo de cómo filtrar para la "noche o madrugada" del día siguiente
        # Asumimos que "hoy" es el día actual cuando se ejecuta la función
        # "Mañana" es el día siguiente. "Noche o madrugada" podría ser de 00:00 a 06:00 del día siguiente.

        # Si dias_prediccion=1, solo obtenemos datos para las próximas 24h desde la hora actual.
        # Si queremos la noche/madrugada del "siguiente día calendario", necesitamos pedir al menos forecast_days=2
        # si hoy es día D y son las 10 AM, forecast_days=1 nos da hasta D+1 10 AM.
        # forecast_days=2 nos da hasta D+2 10 AM, cubriendo toda la noche de D+1 a D+2.

        # Filtrar para el día siguiente al actual, horas 00:00 a 06:00
        # Esto asume que el 'time' está en la zona horaria local correcta gracias a timezone='auto'

        # Obtener el inicio del día de mañana
        manana_inicio = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # Obtener el fin de la madrugada de mañana (ej. 6 AM)
        manana_madrugada_fin = manana_inicio.replace(hour=6)

        print(f"\nFiltrando para mañana entre {manana_inicio} y {manana_madrugada_fin}")

        # Asegurarse que 'time' es timezone-aware si manana_inicio lo es, o viceversa.
        # pd.to_datetime(df['time']) por defecto crea timezone-naive datetimes.
        # Open-Meteo con timezone='auto' devuelve tiempos en UTC si no se especifica un TZ explícito en la solicitud,
        # o en el TZ local del servidor si se detecta. La columna 'time' es una cadena ISO 8601.
        # Es importante que la comparación sea consistente.
        # Si df['time'] es UTC (común en APIs):
        # import pytz
        # manana_inicio_utc = manana_inicio.astimezone(pytz.utc)
        # manana_madrugada_fin_utc = manana_madrugada_fin.astimezone(pytz.utc)
        # datos_madrugada_manana = datos_df[
        #     (datos_df['time'] >= manana_inicio_utc) & (datos_df['time'] <= manana_madrugada_fin_utc)
        # ]
        # Por simplicidad aquí, asumimos que la conversión a pd.to_datetime y la comparación directa funcionan
        # si los tiempos de Open-Meteo están en la hora local del servidor donde corre el script.
        # Si no, se necesita manejo de timezone explícito.
        # El log de Open-Meteo dice: "Timezone: Auto (GMT +00:00)" si no puede determinar, o un TZ específico.
        # Si es GMT+0, entonces son UTC.

        # Re-evaluando: la API devuelve tiempos UTC. Pandas los convierte a datetime64[ns].
        # Para comparaciones robustas, es mejor localizar los tiempos o convertir los límites de comparación a UTC.
        # Ejemplo simple sin manejo explícito de TZ aquí para brevedad, pero es un punto CRÍTICO en producción.

        datos_madrugada_manana = datos_df[
             (datos_df['time'].dt.date == manana_inicio.date()) & \
             (datos_df['time'].dt.hour >= 0) & \
             (datos_df['time'].dt.hour <= 6)
        ]

        if not datos_madrugada_manana.empty:
            print("\nDatos para la madrugada de mañana (00:00 - 06:00):")
            print(datos_madrugada_manana)
            # Aquí se podría seleccionar la primera hora, la media, o la que tenga la temp. mínima.
            # Por ejemplo, la primera hora disponible en ese rango:
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
