# coding: utf-8
import os
import datetime
import pandas as pd
import joblib # Para cargar el modelo en la función de predicción

# Importar funciones de los otros módulos del proyecto
try:
    from .entrenamiento_modelo import entrenar_y_evaluar_modelo
    from .analisis_importancia_variables import analizar_importancia_de_variables
    from .evaluacion_modelo_H02 import evaluar_modelo_H02
except ImportError: # Necesario si se ejecuta main.py directamente desde src/ y no como parte de un paquete
    from entrenamiento_modelo import entrenar_y_evaluar_modelo
    from analisis_importancia_variables import analizar_importancia_de_variables
    from evaluacion_modelo_H02 import evaluar_modelo_H02


# --- Configuración de Rutas (similar a otros scripts, para la función de predicción) ---
# Asumiendo que main.py está en src/
RUTA_BASE_MAIN = "../"
RUTA_MODELOS_ENTRENADOS_MAIN = os.path.join(RUTA_BASE_MAIN, "modelos_entrenados/")
RUTA_DATOS_NUEVOS_MAIN = os.path.join(RUTA_BASE_MAIN, "datos/procesados/") # Directorio para datos de nuevas predicciones

# --- Constantes para la predicción ---
NOMBRE_MODELO_PREDICCION_PKL = "modelo_arbol_decision.pkl" # Modelo a usar para predicciones
COLUMNAS_FEATURES_PREDICCION = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']


def realizar_prediccion_para_fecha(datos_entrada):
    """
    Realiza una predicción de helada para un conjunto de datos de entrada.

    Args:
        datos_entrada (pd.DataFrame): DataFrame con una o más filas,
                                      conteniendo las COLUMNAS_FEATURES_PREDICCION.

    Returns:
        np.array: Array con las predicciones (0 o 1).
                  None si hay error.
    """
    print("\n--- Iniciando Predicción de Helada ---")
    ruta_modelo_pkl = os.path.join(RUTA_MODELOS_ENTRENADOS_MAIN, NOMBRE_MODELO_PREDICCION_PKL)

    try:
        modelo = joblib.load(ruta_modelo_pkl)
        print(f"Modelo de predicción cargado desde: {ruta_modelo_pkl}")
    except FileNotFoundError:
        print(f"Error: No se encontró el modelo de predicción en {ruta_modelo_pkl}.")
        print("Asegúrate de haber entrenado y guardado el modelo primero ejecutando la opción correspondiente.")
        return None
    except Exception as e:
        print(f"Error al cargar el modelo de predicción: {e}")
        return None

    # Validar que datos_entrada es un DataFrame y tiene las columnas necesarias
    if not isinstance(datos_entrada, pd.DataFrame):
        print("Error: Los datos de entrada deben ser un DataFrame de Pandas.")
        return None
    if not all(col in datos_entrada.columns for col in COLUMNAS_FEATURES_PREDICCION):
        print(f"Error: Faltan columnas en los datos de entrada. Se esperan: {COLUMNAS_FEATURES_PREDICCION}")
        return None

    try:
        # Seleccionar solo las columnas de features en el orden correcto
        datos_para_predecir = datos_entrada[COLUMNAS_FEATURES_PREDICCION]
        predicciones = modelo.predict(datos_para_predecir)
        probabilidades = modelo.predict_proba(datos_para_predecir) # Obtener probabilidades

        print("Predicciones realizadas:")
        for i, pred in enumerate(predicciones):
            prob_helada = probabilidades[i][1] # Probabilidad de la clase 1 (Helada)
            print(f"  Registro {i+1}: {'Helada' if pred == 1 else 'No Helada'} (Probabilidad de helada: {prob_helada:.2%})")

        # Devolver solo la predicción (0 o 1) por ahora, la probabilidad se imprime
        return predicciones, probabilidades
    except Exception as e:
        print(f"Error durante la predicción: {e}")
        return None


def obtener_datos_simulados_para_prediccion(fecha_str):
    """
    Simula la obtención de datos para una fecha específica.
    En un caso real, esto vendría de una API, sensores, o entrada manual.
    Retorna un DataFrame.
    """
    print(f"Simulando obtención de datos para la fecha: {fecha_str}")
    # Ejemplo de datos simulados (reemplazar con datos reales o entrada de usuario)
    datos = {
        'Temperatura': [5.0],       # Grados Celsius
        'HumedadRelativa': [85.0],  # Porcentaje
        'PresionAtmosferica': [1012.0], # hPa
        'HumedadSuelo': [60.0]      # Porcentaje
    }
    df_simulado = pd.DataFrame(datos)
    # Aquí se podrían añadir más datos para predicciones múltiples, por ejemplo, para diferentes horas.
    return df_simulado


def mostrar_menu_principal():
    """Muestra el menú principal y maneja la selección del usuario."""
    while True:
        print("\n========== Menú Principal de la Tesis: Predicción de Heladas ==========")
        print("1. Entrenar y Evaluar Modelo Principal (guarda modelo y métricas)")
        print("2. Analizar Importancia de Variables (usa modelo entrenado)")
        print("3. Realizar Evaluación Específica H₀₂ (usa modelo y datos de prueba H02)")
        print("4. Realizar Predicción para Hoy y Mañana (simulado)")
        print("5. Abrir Interfaz de Usuario (placeholder)")
        print("0. Salir")
        print("======================================================================")

        opcion = input("Selecciona una opción: ")

        if opcion == '1':
            print("\n*** Opción 1: Entrenar y Evaluar Modelo Principal ***")
            # El True/False es para visualizar_arbol en la función
            entrenar_y_evaluar_modelo(visualizar_arbol=True)
        elif opcion == '2':
            print("\n*** Opción 2: Analizar Importancia de Variables ***")
            analizar_importancia_de_variables()
        elif opcion == '3':
            print("\n*** Opción 3: Realizar Evaluación Específica H₀₂ ***")
            evaluar_modelo_H02()
        elif opcion == '4':
            print("\n*** Opción 4: Realizar Predicción para Hoy y Mañana (Simulado) ***")
            hoy = datetime.date.today()
            manana = hoy + datetime.timedelta(days=1)

            print(f"\n--- Predicción para HOY ({hoy.strftime('%Y-%m-%d')}) ---")
            datos_hoy = obtener_datos_simulados_para_prediccion(hoy.strftime('%Y-%m-%d'))
            # Modificar ligeramente los datos simulados para que sean diferentes para hoy
            datos_hoy['Temperatura'] = datos_hoy['Temperatura'] -1 # Un poco más frío para hoy
            predicciones_hoy, _ = realizar_prediccion_para_fecha(datos_hoy)
            # Aquí se podría hacer algo más con las predicciones_hoy

            print(f"\n--- Predicción para MAÑANA ({manana.strftime('%Y-%m-%d')}) ---")
            datos_manana = obtener_datos_simulados_para_prediccion(manana.strftime('%Y-%m-%d'))
             # Modificar ligeramente los datos simulados para que sean diferentes para mañana
            datos_manana['HumedadRelativa'] = datos_manana['HumedadRelativa'] + 5
            predicciones_manana, _ = realizar_prediccion_para_fecha(datos_manana)
            # Aquí se podría hacer algo más con las predicciones_manana

        elif opcion == '5':
            print("\n*** Opción 5: Abrir Interfaz de Usuario (Placeholder) ***")
            ruta_interfaz = os.path.join(RUTA_BASE_MAIN, "interfaz_usuario/interfaz_prediccion.html")
            print(f"Se intentaría abrir: {os.path.abspath(ruta_interfaz)}")
            print("Esta funcionalidad es un placeholder. En un entorno real, se podría usar webbrowser.open()")
            print("O la interfaz podría ser una aplicación web Flask/Django que este main.py no lanzaría directamente.")
            # import webbrowser
            # try:
            #     webbrowser.open(f"file://{os.path.abspath(ruta_interfaz)}")
            # except Exception as e:
            #     print(f"No se pudo abrir la interfaz automáticamente: {e}")

        elif opcion == '0':
            print("Saliendo del programa. ¡Hasta luego!")
            break
        else:
            print("Opción no válida. Por favor, intenta de nuevo.")

if __name__ == '__main__':
    # Pequeña verificación de la ruta base si se ejecuta directamente desde src/
    # Esto es para asegurar que las rutas relativas a los datos y modelos funcionen bien.
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    expected_src_path_ending = os.path.join("tesis_prediccion_heladas", "src")

    if not current_script_path.endswith(expected_src_path_ending):
        print(f"Advertencia: El script main.py se está ejecutando desde: {current_script_path}")
        print(f"Se esperaba que terminara en '{expected_src_path_ending}'.")
        print("Las rutas relativas a datos y modelos podrían no funcionar correctamente.")
        print(f"RUTA_BASE_MAIN actual es: {os.path.abspath(RUTA_BASE_MAIN)}")
    else:
        print(f"Script main.py ejecutándose desde: {current_script_path}")
        print(f"RUTA_BASE_MAIN (directorio del proyecto) resuelta a: {os.path.abspath(RUTA_BASE_MAIN)}")

    mostrar_menu_principal()
