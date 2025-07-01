# coding: utf-8
import pandas as pd
import joblib
from sklearn.metrics import precision_score, recall_score, f1_score
import os

# --- Configuración de Rutas ---
RUTA_BASE = "../" # Ajustar si es necesario para que las rutas relativas funcionen desde src/
RUTA_DATOS_PROCESADOS = os.path.join(RUTA_BASE, "datos/procesados/")
# El modelo a usar podría ser el general o uno específico de hipótesis si existiera.
# Por ahora, usaremos el modelo general entrenado.
RUTA_MODELOS_ENTRENADOS = os.path.join(RUTA_BASE, "modelos_entrenados/")
RUTA_RESULTADOS_EVALUACION = os.path.join(RUTA_BASE, "resultados_evaluacion/")

# Crear directorios si no existen
os.makedirs(RUTA_RESULTADOS_EVALUACION, exist_ok=True)

# --- Constantes ---
# El modelo 'modelo_arbol_decision_hipotesis.pkl' (originalmente 'sin_radiacion_temsuelo.pkl' en Hipoetesis)
# podría ser diferente del modelo general entrenado por 'entrenamiento_modelo.py'.
# Si H02 requiere un modelo específico, cambiar NOMBRE_MODELO_PKL aquí y asegurarse que ese modelo exista.
# Por defecto, se usa el modelo 'modelo_arbol_decision_hipotesis.pkl' que fue el renombrado de la carpeta hipotesis.
# Si se quiere usar el modelo general entrenado por `entrenamiento_modelo.py`, cambiar a "modelo_arbol_decision.pkl".
NOMBRE_MODELO_PKL = "modelo_arbol_decision_hipotesis.pkl"
# El archivo original era 'test2.csv', ahora renombrado a 'datos_prueba_evaluacion.csv'
NOMBRE_DATOS_PRUEBA = "datos_prueba_evaluacion.csv"
COLUMNAS_FEATURES = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']
COLUMNA_TARGET = 'HeladaSuelo'
# Nombre descriptivo para el archivo de salida de métricas de esta evaluación específica
NOMBRE_METRICAS_H02_CSV = "metricas_evaluacion_H02.csv"

def evaluar_modelo_H02():
    """
    Evalúa el desempeño (precisión, recall, F1) de un modelo de árbol de decisión ya entrenado,
    específicamente para la hipótesis H₀₂. Carga un modelo y datos de prueba específicos.
    Guarda las métricas en un archivo CSV en la carpeta de resultados.
    """
    print("--- Iniciando Evaluación del Modelo para Hipótesis H₀₂ ---")

    # 1. Cargar modelo entrenado
    ruta_modelo_pkl = os.path.join(RUTA_MODELOS_ENTRENADOS, NOMBRE_MODELO_PKL)
    try:
        modelo = joblib.load(ruta_modelo_pkl)
        print(f"Modelo para H02 cargado desde: {ruta_modelo_pkl}")
    except FileNotFoundError:
        print(f"Error: No se encontró el modelo en {ruta_modelo_pkl}.")
        print(f"Asegúrate de que el modelo '{NOMBRE_MODELO_PKL}' exista en '{RUTA_MODELOS_ENTRENADOS}'.")
        print("Este script espera un modelo específico para H02 o el modelo general si así se configura.")
        return
    except Exception as e:
        print(f"Error al cargar el modelo: {e}")
        return

    # 2. Cargar datos de prueba
    ruta_csv_datos_prueba = os.path.join(RUTA_DATOS_PROCESADOS, NOMBRE_DATOS_PRUEBA)
    try:
        df_prueba = pd.read_csv(ruta_csv_datos_prueba)
        print(f"Datos de prueba para H02 cargados desde: {ruta_csv_datos_prueba}")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de datos de prueba en {ruta_csv_datos_prueba}")
        return
    except Exception as e:
        print(f"Error al cargar los datos de prueba: {e}")
        return

    # 3. Definir X_prueba y y_prueba (conjunto de prueba)
    try:
        X_prueba = df_prueba[COLUMNAS_FEATURES]
        y_prueba = df_prueba[COLUMNA_TARGET]
    except KeyError as e:
        print(f"Error: Una o más columnas (features o target) no se encontraron en el archivo de datos: {e}")
        print(f"   Columnas esperadas para features: {COLUMNAS_FEATURES}")
        print(f"   Columna esperada para target: {COLUMNA_TARGET}")
        return

    print(f"Características para prueba H02: {COLUMNAS_FEATURES}")
    print(f"Variable objetivo para prueba H02: {COLUMNA_TARGET}")

    # 4. Realizar predicciones sobre el conjunto de prueba
    y_prediccion = modelo.predict(X_prueba)

    # 5. Calcular métricas de desempeño (Precision, Recall, F1-score)
    # 'zero_division=0' evita warnings si no hay predicciones para una clase (poco probable aquí).
    precision = precision_score(y_prueba, y_prediccion, zero_division=0)
    sensibilidad = recall_score(y_prueba, y_prediccion, zero_division=0) # Recall es también conocido como sensibilidad
    f1 = f1_score(y_prueba, y_prediccion, zero_division=0)

    # 6. Mostrar resultados de la evaluación
    print("\n--- Evaluación según H₀₂: Desempeño del Modelo (Precisión, Recall, F1) ---")
    print(f"Precisión: {precision:.3f}")
    print(f"Recall (Sensibilidad): {sensibilidad:.3f}")
    print(f"F1-score: {f1:.3f}")

    # 7. Exportar métricas a un archivo CSV
    df_metricas_H02 = pd.DataFrame({
        'Metrica': ['Precision', 'Recall (Sensibilidad)', 'F1-score'],
        'Valor': [precision, sensibilidad, f1]
    })

    ruta_metricas_H02_csv = os.path.join(RUTA_RESULTADOS_EVALUACION, NOMBRE_METRICAS_H02_CSV)
    try:
        df_metricas_H02.to_csv(ruta_metricas_H02_csv, index=False, float_format='%.3f')
        print(f"Métricas de la evaluación H₀₂ exportadas a: {ruta_metricas_H02_csv}")
    except Exception as e:
        print(f"Error al exportar las métricas H02 a CSV: {e}")

    print("--- Evaluación H₀₂ Finalizada ---")

if __name__ == '__main__':
    evaluar_modelo_H02()
