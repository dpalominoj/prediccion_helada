# coding: utf-8
import pandas as pd
import joblib
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import os

# --- Configuración de Rutas ---
RUTA_BASE = "../"  # Ajustar si es necesario para que las rutas relativas funcionen desde src/
RUTA_DATOS_PROCESADOS = os.path.join(RUTA_BASE, "datos/procesados/")
RUTA_MODELOS_ENTRENADOS = os.path.join(RUTA_BASE, "modelos_entrenados/")
RUTA_RESULTADOS_EVALUACION = os.path.join(RUTA_BASE, "resultados_evaluacion/")
RUTA_GRAFICAS = os.path.join(RUTA_RESULTADOS_EVALUACION, "graficas/")

# Crear directorios si no existen
os.makedirs(RUTA_MODELOS_ENTRENADOS, exist_ok=True)
os.makedirs(RUTA_RESULTADOS_EVALUACION, exist_ok=True)
os.makedirs(RUTA_GRAFICAS, exist_ok=True)

# --- Constantes del Modelo ---
NOMBRE_ARCHIVO_DATOS = "datos_completos.csv"
NOMBRE_MODELO_PKL = "modelo_arbol_decision.pkl"
NOMBRE_METRICAS_CSV = "metricas_entrenamiento.csv"
NOMBRE_GRAFICA_ARBOL = "arbol_decision.png"

COLUMNAS_FEATURES = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']
COLUMNA_TARGET = 'HeladaSuelo'
TEST_SIZE = 0.2
RANDOM_STATE = 42

def entrenar_y_evaluar_modelo(visualizar_arbol=True):
    """
    Carga los datos, entrena un modelo de árbol de decisión, lo evalúa,
    guarda el modelo y las métricas, y opcionalmente visualiza el árbol.
    """
    print("--- Iniciando Proceso de Entrenamiento y Evaluación del Modelo ---")

    # 1. Cargar datos
    ruta_csv_datos = os.path.join(RUTA_DATOS_PROCESADOS, NOMBRE_ARCHIVO_DATOS)
    try:
        df = pd.read_csv(ruta_csv_datos)
        print(f"Datos cargados exitosamente desde: {ruta_csv_datos}")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de datos en {ruta_csv_datos}")
        return

    # 2. Definir características (X) y variable objetivo (y)
    X = df[COLUMNAS_FEATURES]
    y = df[COLUMNA_TARGET]
    print(f"Características seleccionadas: {COLUMNAS_FEATURES}")
    print(f"Variable objetivo: {COLUMNA_TARGET}")

    # 3. Dividir en conjuntos de entrenamiento y prueba
    X_entrenamiento, X_prueba, y_entrenamiento, y_prueba = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Datos divididos: {100*(1-TEST_SIZE):.0f}% entrenamiento, {100*TEST_SIZE:.0f}% prueba.")

    # 4. Crear y entrenar el modelo de árbol de decisión
    # Se puede ajustar hiperparámetros como max_depth o min_samples_split según necesidades
    modelo = DecisionTreeClassifier(random_state=RANDOM_STATE, max_depth=None)
    print("Entrenando el modelo de árbol de decisión...")
    modelo.fit(X_entrenamiento, y_entrenamiento)
    print("Modelo entrenado.")

    # 5. Guardar el modelo entrenado
    ruta_modelo_pkl = os.path.join(RUTA_MODELOS_ENTRENADOS, NOMBRE_MODELO_PKL)
    joblib.dump(modelo, ruta_modelo_pkl)
    print(f"Modelo guardado en: {ruta_modelo_pkl}")

    # 6. Visualizar el árbol de decisión (opcional)
    if visualizar_arbol:
        print("Generando visualización del árbol de decisión...")
        plt.figure(figsize=(25, 15))
        plot_tree(
            modelo,
            feature_names=X.columns,
            class_names=[str(c) for c in modelo.classes_], # 'No Helada', 'Helada' si son 0 y 1
            filled=True,
            rounded=True,
            fontsize=10
        )
        plt.title(f"Árbol de Decisión - Predicción de {COLUMNA_TARGET}", fontsize=16)
        ruta_guardado_arbol = os.path.join(RUTA_GRAFICAS, NOMBRE_GRAFICA_ARBOL)
        try:
            plt.savefig(ruta_guardado_arbol)
            print(f"Visualización del árbol guardada en: {ruta_guardado_arbol}")
        except Exception as e:
            print(f"Error al guardar la visualización del árbol: {e}")
        plt.close() # Cerrar la figura para liberar memoria

    # 7. Realizar predicciones sobre el conjunto de prueba
    y_prediccion = modelo.predict(X_prueba)

    # 8. Evaluar el rendimiento del modelo
    exactitud = accuracy_score(y_prueba, y_prediccion)
    precision = precision_score(y_prueba, y_prediccion, zero_division=0)
    sensibilidad = recall_score(y_prueba, y_prediccion, zero_division=0) # Recall
    f1 = f1_score(y_prueba, y_prediccion, zero_division=0)

    metricas = {
        'Metrica': ['Exactitud', 'Precision', 'Sensibilidad (Recall)', 'F1-score'],
        'Valor': [exactitud, precision, sensibilidad, f1]
    }
    df_metricas = pd.DataFrame(metricas)

    # 9. Imprimir y guardar métricas
    print("\n--- Resultados de Evaluación del Modelo (sobre conjunto de prueba) ---")
    print(df_metricas.to_string(index=False, float_format='{:,.3f}'.format))

    ruta_metricas_csv = os.path.join(RUTA_RESULTADOS_EVALUACION, NOMBRE_METRICAS_CSV)
    df_metricas.to_csv(ruta_metricas_csv, index=False)
    print(f"Métricas de entrenamiento exportadas a: {ruta_metricas_csv}")
    print("--- Proceso de Entrenamiento y Evaluación Finalizado ---")

if __name__ == '__main__':
    # Ejecutar el entrenamiento y la evaluación, con visualización del árbol.
    # Cambiar a False si no se desea la visualización.
    entrenar_y_evaluar_modelo(visualizar_arbol=True)
