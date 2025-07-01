# coding: utf-8
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import os

# --- Configuración de Rutas ---
RUTA_BASE = "../" # Ajustar si es necesario para que las rutas relativas funcionen desde src/
RUTA_DATOS_PROCESADOS = os.path.join(RUTA_BASE, "datos/procesados/")
RUTA_MODELOS_ENTRENADOS = os.path.join(RUTA_BASE, "modelos_entrenados/")
RUTA_RESULTADOS_EVALUACION = os.path.join(RUTA_BASE, "resultados_evaluacion/")
RUTA_GRAFICAS = os.path.join(RUTA_RESULTADOS_EVALUACION, "graficas/")

# Crear directorios si no existen
os.makedirs(RUTA_GRAFICAS, exist_ok=True) # Directorio para guardar la gráfica

# --- Constantes ---
# Usar el modelo generado por entrenamiento_modelo.py
NOMBRE_MODELO_PKL = "modelo_arbol_decision.pkl"
# Usar los datos de prueba originales donde se midió la importancia, o datos completos si es más apropiado
# El archivo 'datos_prueba_importancia.csv' fue el 'test.csv' original.
NOMBRE_DATOS_PARA_ANALISIS = "datos_prueba_importancia.csv"
# Estas deben ser las mismas columnas usadas para entrenar el modelo cargado.
COLUMNAS_FEATURES = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']
NOMBRE_GRAFICA_IMPORTANCIA = "importancia_variables.png"

def analizar_importancia_de_variables():
    """
    Carga un modelo de árbol de decisión entrenado,
    calcula y grafica la importancia de las variables.
    Guarda la gráfica en la carpeta de resultados.
    """
    print("--- Iniciando Análisis de Importancia de Variables ---")

    # 1. Cargar el modelo guardado
    ruta_modelo_pkl = os.path.join(RUTA_MODELOS_ENTRENADOS, NOMBRE_MODELO_PKL)
    try:
        modelo = joblib.load(ruta_modelo_pkl)
        print(f"Modelo cargado desde: {ruta_modelo_pkl}")
    except FileNotFoundError:
        print(f"Error: No se encontró el modelo en {ruta_modelo_pkl}. Asegúrate de haber ejecutado el script de entrenamiento primero.")
        return
    except Exception as e:
        print(f"Error al cargar el modelo: {e}")
        return

    # 2. Cargar el CSV con los datos (solo para obtener los nombres de las features si es necesario, el modelo ya está entrenado)
    # ruta_csv_datos = os.path.join(RUTA_DATOS_PROCESADOS, NOMBRE_DATOS_PARA_ANALISIS)
    # try:
    #     df_datos = pd.read_csv(ruta_csv_datos)
    #     print(f"Datos para nombres de features (si es necesario) cargados desde: {ruta_csv_datos}")
    # except FileNotFoundError:
    #     print(f"Error: No se encontró el archivo de datos en {ruta_csv_datos}")
    #     return
    # except Exception as e:
    #     print(f"Error al cargar los datos para nombres de features: {e}")
    #     return

    # if not all(columna in df_datos.columns for columna in COLUMNAS_FEATURES):
    #     print(f"Advertencia: No todas las columnas {COLUMNAS_FEATURES} se encuentran en {ruta_csv_datos}.")

    # 3. Obtener importancias de las variables desde el modelo
    try:
        importancias = modelo.feature_importances_

        # Usar los nombres de las features con las que el modelo fue entrenado, si están disponibles.
        # De lo contrario, usar la lista COLUMNAS_FEATURES.
        if hasattr(modelo, 'feature_names_in_'):
            nombres_variables = list(modelo.feature_names_in_)
            if list(nombres_variables) != COLUMNAS_FEATURES:
                print("Advertencia: Las 'feature_names_in_' del modelo no coinciden exactamente con COLUMNAS_FEATURES definidas en el script.")
                print(f"   Nombres del modelo: {nombres_variables}")
                print(f"   Nombres en script: {COLUMNAS_FEATURES}")
                print("   Se usarán los nombres del modelo.")
        else:
            nombres_variables = COLUMNAS_FEATURES
            print("Advertencia: El modelo no tiene 'feature_names_in_'. Usando COLUMNAS_FEATURES definidas en el script. Asegúrate que el orden sea el correcto.")


        if len(importancias) != len(nombres_variables):
            print(f"Error: Discrepancia en el número de importancias ({len(importancias)}) y variables ({len(nombres_variables)}).")
            print(f"   Importancias: {importancias}")
            print(f"   Nombres de variables: {nombres_variables}")
            print("   Esto puede ocurrir si COLUMNAS_FEATURES no coincide con cómo se entrenó el modelo y el modelo no tiene 'feature_names_in_'.")
            return

    except AttributeError:
        print("Error: El modelo cargado no tiene el atributo 'feature_importances_'. ¿Es un modelo de árbol de decisión o similar?")
        return
    except Exception as e:
        print(f"Error al obtener importancias: {e}")
        return

    # 4. Crear DataFrame ordenado con las importancias
    df_importancias = pd.DataFrame({
        'Variable': nombres_variables,
        'Importancia': importancias
    }).sort_values(by='Importancia', ascending=False)

    print("\n--- Importancia de Variables ---")
    print(df_importancias.to_string(index=False, float_format='{:,.4f}'.format))

    # 5. Graficar y guardar la importancia de variables
    plt.figure(figsize=(12, 8))
    plt.barh(df_importancias['Variable'], df_importancias['Importancia'], color='lightcoral')
    plt.xlabel('Importancia Relativa')
    plt.ylabel('Variable Meteorológica')
    plt.title('Importancia de las Variables en la Predicción de Heladas (Árbol de Decisión)')
    plt.gca().invert_yaxis()
    plt.grid(True, axis='x', linestyle=':', alpha=0.7)
    plt.tight_layout()

    ruta_guardado_grafica = os.path.join(RUTA_GRAFICAS, NOMBRE_GRAFICA_IMPORTANCIA)
    try:
        plt.savefig(ruta_guardado_grafica)
        print(f"Gráfica de importancia de variables guardada en: {ruta_guardado_grafica}")
    except Exception as e:
        print(f"Error al guardar la gráfica: {e}")

    # plt.show() # Descomentar si se desea mostrar interactivamente al ejecutar el script
    plt.close() # Cerrar la figura para liberar memoria

    print("--- Análisis de Importancia de Variables Finalizado ---")

if __name__ == '__main__':
    analizar_importancia_de_variables()
