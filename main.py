# coding: utf-8
from flask import Flask, render_template, jsonify, request, redirect, url_for
from sqlalchemy.orm import Session
import datetime
import json
import os
import joblib
import pandas as pd
import logging

# --- Importaciones de módulos del proyecto (desde src) ---
from src.database.database import init_db, get_db
from src.database.models import Prediccion, IntensidadHelada, ResultadoPrediccion
from src.data_fetcher import obtener_datos_meteorologicos_openmeteo, COLUMNAS_MODELO as FETCHED_COLUMNAS_MODELO

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Logger para este archivo main.py
app_logger = logging.getLogger('werkzeug') # Logger de Flask/Werkzeug
app_logger.setLevel(logging.INFO)

# --- Configuración de la Aplicación Flask ---
app = Flask(__name__,
            template_folder='interfaz_usuario',  # Relativo a la raíz del proyecto
            static_folder='static')             # Relativo a la raíz del proyecto
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///./predicciones.db' # En la raíz
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Carga del Modelo de Predicción y Constantes ---
# main.py está en la raíz.
RUTA_MODELOS_ENTRENADOS = "modelos_entrenados/" # Relativo a la raíz
NOMBRE_MODELO_PREDICCION_PKL = "modelo_arbol_decision.pkl"
COLUMNAS_FEATURES_PREDICCION = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']

prediction_model = None
try:
    ruta_modelo_pkl = os.path.join(RUTA_MODELOS_ENTRENADOS, NOMBRE_MODELO_PREDICCION_PKL)
    if os.path.exists(ruta_modelo_pkl):
        prediction_model = joblib.load(ruta_modelo_pkl)
        logger.info(f"Modelo de predicción cargado exitosamente desde: {ruta_modelo_pkl}")
    else:
        logger.error(f"Error crítico: No se encontró el modelo de predicción en la ruta especificada: {ruta_modelo_pkl}.")
        logger.warning("La funcionalidad de predicción NO estará disponible.")
except Exception as e:
    logger.error(f"Error crítico al cargar el modelo de predicción desde {ruta_modelo_pkl}: {e}", exc_info=True)
    prediction_model = None

# --- Funciones Auxiliares (movidas desde el antiguo app.py) ---
def determinar_estado_helada(prediccion_valor, probabilidad_helada, temperatura_actual_o_prevista):
    resultado_pred = ResultadoPrediccion.poco_probable
    intensidad_pred = IntensidadHelada.no_helada
    duracion_horas = 0.0

    if prediccion_valor == 1: # Helada
        resultado_pred = ResultadoPrediccion.probable
        if probabilidad_helada >= 0.80 and temperatura_actual_o_prevista < -2:
            intensidad_pred = IntensidadHelada.fuerte
            duracion_horas = 4.0
        elif probabilidad_helada >= 0.60 and temperatura_actual_o_prevista < 0:
            intensidad_pred = IntensidadHelada.moderada
            duracion_horas = 2.5
        else:
            intensidad_pred = IntensidadHelada.leve
            duracion_horas = 1.0
    return resultado_pred, intensidad_pred, duracion_horas

# --- Rutas de la Aplicación ---
@app.route('/')
def index():
    return render_template('interfaz_prediccion.html')

# @app.route('/predecir', methods=['POST'])
# def predecir():
#     # --- Esta ruta para predicción manual ha sido comentada ---
#     # --- La funcionalidad principal ahora es /pronostico_automatico ---
#     logger.info("Ruta /predecir (manual) ha sido invocada, pero está deshabilitada.")
#     return jsonify({"error": "La predicción manual ha sido deshabilitada. Utilice el pronóstico automático."}), 403
#
#     # if prediction_model is None:
#     #     logger.error("Intento de predicción manual pero el modelo no está cargado.")
#     #     return jsonify({"error": "Modelo de predicción no disponible."}), 500
#     #
#     # input_data_json = request.json
#     # if not input_data_json:
#     #     logger.warning("No se recibieron datos JSON en /predecir.")
#     #     return jsonify({"error": "No se recibieron datos en formato JSON."}), 400
#     #
#     # datos_para_modelo_list = []
#     # for col in COLUMNAS_FEATURES_PREDICCION:
#     #     if col not in input_data_json:
#     #         logger.error(f"Falta la columna '{col}' en los datos de entrada para predicción manual. Datos: {input_data_json}")
#     #         return jsonify({"error": f"Dato de entrada incompleto. Falta '{col}'."}), 400
#     #     try:
#     #         datos_para_modelo_list.append(float(input_data_json[col]))
#     #     except ValueError:
#     #         logger.error(f"Valor no numérico para '{col}': {input_data_json[col]}")
#     #         return jsonify({"error": f"Valor para '{col}' debe ser numérico."}), 400
#     #
#     # datos_para_modelo_dict = dict(zip(COLUMNAS_FEATURES_PREDICCION, datos_para_modelo_list))
#     # ubicacion_manual = input_data_json.get("ubicacion", "Pucará (Manual)")
#     # estacion_manual = input_data_json.get("estacion", "Estación Manual")
#     #
#     # try:
#     #     df_para_predecir = pd.DataFrame([datos_para_modelo_dict], columns=COLUMNAS_FEATURES_PREDICCION)
#     #     logger.info(f"DataFrame para predicción manual: \n{df_para_predecir.to_string()}")
#     #
#     #     pred_array = prediction_model.predict(df_para_predecir)
#     #     prob_array = prediction_model.predict_proba(df_para_predecir)
#     #     pred_valor = int(pred_array[0])
#     #     prob_helada = float(prob_array[0][1])
#     #
#     #     resultado, intensidad, duracion = determinar_estado_helada(
#     #         pred_valor, prob_helada, datos_para_modelo_dict['Temperatura']
#     #     )
#     #     pred_final = {
#     #         "temperatura_minima_prevista": datos_para_modelo_dict['Temperatura'],
#     #         "probabilidad_helada": prob_helada, "resultado": resultado,
#     #         "intensidad": intensidad, "duracion_estimada_horas": duracion,
#     #         "mensaje": f"Resultado (Manual): {'HELADA' if pred_valor == 1 else 'NO HELADA'} (Prob: {prob_helada:.2%})"
#     #     }
#     #     logger.info(f"Predicción manual realizada: {pred_final}")
#     #
#     # except Exception as e:
#     #     logger.error(f"Error en predicción manual: {e}", exc_info=True)
#     #     return jsonify({"error": f"Error interno en predicción manual: {str(e)}"}), 500
#     #
#     # db_session: Session = next(get_db())
#     # try:
#     #     nueva_pred = Prediccion(
#     #         fecha_prediccion_para=datetime.datetime.utcnow() + datetime.timedelta(hours=1), # Placeholder
#     #         ubicacion=ubicacion_manual, estacion_meteorologica=estacion_manual,
#     #         temperatura_minima_prevista=pred_final["temperatura_minima_prevista"],
#     #         probabilidad_helada=pred_final["probabilidad_helada"],
#     #         resultado=pred_final["resultado"], intensidad=pred_final["intensidad"],
#     #         duracion_estimada_horas=pred_final["duracion_estimada_horas"],
#     #         parametros_entrada=json.dumps(datos_para_modelo_dict),
#     #         fuente_datos_entrada="Entrada Manual API Flask (modelo_arbol_decision.pkl)"
#     #     )
#     #     db_session.add(nueva_pred)
#     #     db_session.commit()
#     #     db_session.refresh(nueva_pred)
#     #     logger.info(f"Predicción manual guardada en BD con ID: {nueva_pred.id}")
#     #
#     #     respuesta = {
#     #         "id": nueva_pred.id, "fecha_registro": nueva_pred.fecha_registro.isoformat(),
#     #         "fecha_prediccion_para": nueva_pred.fecha_prediccion_para.isoformat(),
#     #         "ubicacion": nueva_pred.ubicacion, "estacion_meteorologica": nueva_pred.estacion_meteorologica,
#     #         "temperatura_minima_prevista": nueva_pred.temperatura_minima_prevista,
#     #         "probabilidad_helada": nueva_pred.probabilidad_helada,
#     #         "resultado": nueva_pred.resultado.value if nueva_pred.resultado else None,
#     #         "intensidad": nueva_pred.intensidad.value if nueva_pred.intensidad else None,
#     #         "duracion_estimada_horas": nueva_pred.duracion_estimada_horas,
#     #         "mensaje_adicional": pred_final.get("mensaje")
#     #     }
#     #     return jsonify(respuesta), 200
#     # except Exception as e:
#     #     db_session.rollback()
#     #     logger.error(f"Error al guardar predicción manual en BD: {e}", exc_info=True)
#     #     return jsonify({"error": f"Error interno al guardar predicción manual: {str(e)}"}), 500
#     # finally:
#     #     db_session.close()

@app.route('/pronostico_automatico', methods=['GET'])
def pronostico_automatico():
    if prediction_model is None:
        logger.error("Intento de pronóstico automático pero el modelo no está cargado.")
        return jsonify({"error": "Modelo de predicción no disponible."}), 500

    logger.info("Iniciando pronóstico automático con datos de Open-Meteo...")
    datos_meteo_df = obtener_datos_meteorologicos_openmeteo(dias_prediccion=2)

    if datos_meteo_df is None or datos_meteo_df.empty:
        logger.error("No se pudieron obtener datos de Open-Meteo.")
        return jsonify({"error": "No se pudieron obtener datos meteorológicos externos."}), 503

    predicciones_guardadas = []
    errores_prediccion = []

    for _, fila_hora in datos_meteo_df.iterrows():
        fecha_pred = fila_hora['time']
        datos_hora_dict = fila_hora[FETCHED_COLUMNAS_MODELO].to_dict()

        if not all(col in datos_hora_dict for col in COLUMNAS_FEATURES_PREDICCION):
            msg = f"Faltan datos para predicción en {fecha_pred}. Datos: {datos_hora_dict.keys()}"
            logger.error(msg)
            errores_prediccion.append({"timestamp": fecha_pred.isoformat(), "error": msg})
            continue

        df_pred_hora = pd.DataFrame([datos_hora_dict], columns=COLUMNAS_FEATURES_PREDICCION)

        try:
            pred_array = prediction_model.predict(df_pred_hora)
            prob_array = prediction_model.predict_proba(df_pred_hora)
            pred_valor = int(pred_array[0])
            prob_helada = float(prob_array[0][1])
            temp_actual = datos_hora_dict['Temperatura']
            resultado, intensidad, duracion = determinar_estado_helada(pred_valor, prob_helada, temp_actual)

            db_session: Session = next(get_db())
            try:
                nueva_pred = Prediccion(
                    fecha_prediccion_para=fecha_pred,
                    ubicacion="Patala, Pucará (Open-Meteo)",
                    estacion_meteorologica="Open-Meteo Forecast",
                    temperatura_minima_prevista=temp_actual,
                    probabilidad_helada=prob_helada, resultado=resultado,
                    intensidad=intensidad, duracion_estimada_horas=duracion,
                    parametros_entrada=json.dumps(datos_hora_dict),
                    fuente_datos_entrada="Open-Meteo API via src.data_fetcher"
                )
                db_session.add(nueva_pred)
                db_session.commit()
                db_session.refresh(nueva_pred)
                predicciones_guardadas.append({
                    "id": nueva_pred.id, "fecha_prediccion_para": nueva_pred.fecha_prediccion_para.isoformat(),
                    "resultado": nueva_pred.resultado.value if nueva_pred.resultado else None,
                    "intensidad": nueva_pred.intensidad.value if nueva_pred.intensidad else None
                })
                logger.info(f"Predicción horaria para {fecha_pred} guardada (ID: {nueva_pred.id}).")
            except Exception as db_exc:
                db_session.rollback()
                msg = f"Error guardando predicción para {fecha_pred} en BD: {db_exc}"
                logger.error(msg, exc_info=True)
                errores_prediccion.append({"timestamp": fecha_pred.isoformat(), "error": msg})
            finally:
                db_session.close()
        except Exception as model_exc:
            msg = f"Error en predicción del modelo para {fecha_pred}: {model_exc}"
            logger.error(msg, exc_info=True)
            errores_prediccion.append({"timestamp": fecha_pred.isoformat(), "error": msg})

    num_exitos = len(predicciones_guardadas)
    num_fallos = len(errores_prediccion)
    mensaje_final = f"Pronóstico automático completado. {num_exitos} predicciones horarias guardadas. {num_fallos} errores."
    logger.info(mensaje_final)

    return jsonify({
        "mensaje": mensaje_final,
        "predicciones_exitosas": predicciones_guardadas,
        "errores": errores_prediccion
    }), 200 if num_fallos == 0 else 207

@app.route('/registros', methods=['GET'])
def ver_registros():
    db_session: Session = next(get_db())
    try:
        query = db_session.query(Prediccion)
        fecha_filtro = request.args.get('fecha')
        estacion_filtro = request.args.get('estacion')

        if fecha_filtro:
            try:
                fecha_dt = datetime.datetime.strptime(fecha_filtro, "%Y-%m-%d").date()
                query = query.filter( Prediccion.fecha_prediccion_para >= datetime.datetime.combine(fecha_dt, datetime.time.min),
                                      Prediccion.fecha_prediccion_para <= datetime.datetime.combine(fecha_dt, datetime.time.max))
            except ValueError:
                logger.warning(f"Formato de fecha inválido: {fecha_filtro}")
                return jsonify({"error": "Formato de fecha inválido. Usar YYYY-MM-DD."}), 400
        if estacion_filtro:
            query = query.filter(Prediccion.estacion_meteorologica.ilike(f"%{estacion_filtro}%"))

        registros = query.order_by(Prediccion.fecha_prediccion_para.desc()).all()
        registros_list = [{
                "id": reg.id, "fecha_registro": reg.fecha_registro.isoformat(),
                "fecha_prediccion_para": reg.fecha_prediccion_para.isoformat(),
                "ubicacion": reg.ubicacion, "estacion_meteorologica": reg.estacion_meteorologica,
                "resultado": reg.resultado.value if reg.resultado else None,
                "intensidad": reg.intensidad.value if reg.intensidad else None,
                "duracion_estimada_horas": reg.duracion_estimada_horas,
                "temperatura_minima_prevista": reg.temperatura_minima_prevista,
                "probabilidad_helada": reg.probabilidad_helada
            } for reg in registros]
        return jsonify(registros_list), 200
    except Exception as e:
        logger.error(f"Error al obtener registros de la BD: {e}", exc_info=True)
        return jsonify({"error": f"Error al obtener registros: {str(e)}"}), 500
    finally:
        db_session.close()

@app.route('/registros_ui', methods=['GET'])
def ver_registros_ui():
    db_session: Session = next(get_db())
    try:
        registros = db_session.query(Prediccion).order_by(Prediccion.fecha_prediccion_para.desc()).all()
        return render_template('interfaz_registros.html', registros=registros)
    except Exception as e:
        logger.error(f"Error en la ruta /registros_ui: {e}", exc_info=True)
        return render_template('error.html', error_message=str(e)), 500
    finally:
        db_session.close()

# --- Lógica de inicialización y ejecución (del antiguo src/main.py) ---
def inicializar_aplicacion():
    logger.info("Inicializando la base de datos (si es necesario)...")
    init_db() # Esta función está en src.database.database
    logger.info("Base de datos lista.")
    # Aquí se podrían añadir otras inicializaciones si fueran necesarias

if __name__ == '__main__':
    logger.info("Iniciando aplicación de predicción de heladas...")
    inicializar_aplicacion()

    logger.info(f"Iniciando servidor Flask. Accede a la interfaz en http://{os.environ.get('FLASK_HOST', '0.0.0.0')}:{os.environ.get('FLASK_PORT', 5000)}")
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", 5000)),
        debug=(os.environ.get("FLASK_DEBUG", "True").lower() == "true")
    )

# --- Comentarios sobre otros scripts en src/ ---
# Los scripts como src/entrenamiento_modelo.py, src/analisis_importancia_variables.py,
# y src/evaluacion_modelo_H02.py pueden seguir siendo ejecutados individualmente
# (ej. `python src/entrenamiento_modelo.py`) si se desea realizar esas tareas
# específicas. Sus rutas internas (RUTA_BASE = "../") deberían seguir funcionando
# correctamente cuando se ejecutan desde la carpeta src/.
# Si se quisiera integrarlos como comandos o funciones accesibles desde este
# main.py, se podrían importar y llamar aquí, posiblemente usando argumentos de línea de comandos.
# Por ahora, se mantienen como scripts independientes.
