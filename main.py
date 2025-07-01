# coding: utf-8
from flask import Flask, render_template, jsonify, request, redirect, url_for
from sqlalchemy.orm import Session
import datetime
import json
import os
import joblib
import pandas as pd
import logging
import database # Importamos el módulo para acceder a setup_database_engine

# --- Importaciones de módulos del proyecto (desde src) ---
from database.database import init_db, get_db, setup_database_engine # Añadido setup_database_engine
from database.models import Prediccion, IntensidadHelada, ResultadoPrediccion
from src.data_fetcher import obtener_datos_meteorologicos_openmeteo # FETCHED_COLUMNAS_MODELO será COLUMNAS_FEATURES_PREDICCION

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) # Logger para este archivo main.py
app_logger = logging.getLogger('werkzeug') # Logger de Flask/Werkzeug
app_logger.setLevel(logging.INFO)

# --- Configuración de la Aplicación Flask ---
app = Flask(__name__,
            instance_relative_config=True,  # Para que instance_path funcione como se espera
            template_folder='interfaz_usuario',
            static_folder='static')

# Configuración de la base de datos usando instance_path
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key968') # Buena práctica añadir una Secret Key
try:
    os.makedirs(app.instance_path, exist_ok=True) # Crea el directorio instance si no existe
except OSError as e:
    app.logger.error(f"Error creando el directorio de instancia {app.instance_path}: {e}")
    # Considerar si la app debe detenerse aquí o continuar si la creación falla.

default_sqlite_uri = f"sqlite:///{os.path.join(app.instance_path, 'predicciones.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_sqlite_uri)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.logger.info(f"Usando DATABASE_URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

# --- Carga del Modelo de Predicción y Constantes ---
# main.py está en la raíz.
RUTA_MODELOS_ENTRENADOS = "modelos_entrenados/" # Relativo a la raíz
NOMBRE_MODELO_PREDICCION_PKL = "modelo_arbol_decision.pkl"
COLUMNAS_FEATURES_PREDICCION = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']

prediction_model = None
# Solo cargar modelo y configurar DB en el proceso principal de Werkzeug o cuando no se usa el reloader
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
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
def estimar_humedad_suelo_volumetrica(humedad_relativa_percent, precipitacion_mm):
    """
    Estima la humedad volumétrica del suelo (m³/m³) basada en la humedad relativa y la precipitación.
    Esta es una aproximación heurística y los coeficientes/escalas pueden necesitar ajuste.
    """
    if pd.isna(humedad_relativa_percent) or pd.isna(precipitacion_mm):
        logger.warning("Datos de humedad relativa o precipitación faltantes para estimar humedad del suelo. Retornando NA.")
        return pd.NA

    # Fórmula base propuesta por el usuario, con ponderaciones
    raw_score = (humedad_relativa_percent * 0.6) + (precipitacion_mm * 1.2)

    estimated_sm_volumetric = raw_score / 200.0
    capped_sm_volumetric = min(0.55, max(0.05, estimated_sm_volumetric))
    
    logger.info(f"HumedadSuelo estimada: HR={humedad_relativa_percent}%, Precip={precipitacion_mm}mm -> Raw={raw_score:.2f} -> Scaled={estimated_sm_volumetric:.3f} -> Capped={capped_sm_volumetric:.3f} m³/m³")
    return capped_sm_volumetric

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

@app.route('/pronostico_automatico', methods=['GET'])
def pronostico_automatico():
    if prediction_model is None:
        logger.error("Intento de pronóstico automático pero el modelo no está cargado.")
        return jsonify({"error": "Modelo de predicción no disponible."}), 500

    logger.info("Iniciando pronóstico automático con datos de Open-Meteo...")

    # Coordenadas para Patala, Pucará
    lat_pucara = -12.20892
    lon_pucara = -75.07791

    # Pedimos datos para los próximos 2 días para asegurar que cubrimos la madrugada siguiente.
    datos_meteo_df = obtener_datos_meteorologicos_openmeteo(lat_pucara, lon_pucara, dias_prediccion=2)

    if datos_meteo_df is None or datos_meteo_df.empty:
        logger.error("No se pudieron obtener datos de Open-Meteo.")
        return jsonify({"error": "No se pudieron obtener datos meteorológicos externos."}), 503
    tz_datos = datos_meteo_df['time'].iloc[0].tzinfo if not datos_meteo_df.empty and datos_meteo_df['time'].iloc[0].tzinfo else None
    ahora = datetime.datetime.now(tz_datos)
    dia_siguiente = ahora.date() + pd.Timedelta(days=1)

    hora_inicio_madrugada = 1
    hora_fin_madrugada = 5

    madrugada_inicio = datetime.datetime.combine(dia_siguiente, datetime.time(hora_inicio_madrugada), tzinfo=tz_datos)
    madrugada_fin = datetime.datetime.combine(dia_siguiente, datetime.time(hora_fin_madrugada), tzinfo=tz_datos)

    logger.info(f"Buscando datos completos para predicción en la madrugada del {dia_siguiente.strftime('%Y-%m-%d')} entre {madrugada_inicio.strftime('%H:%M')} y {madrugada_fin.strftime('%H:%M')}.")

    # Filtrar el DataFrame para el rango de la madrugada del día siguiente
    datos_madrugada_df = datos_meteo_df[
        (datos_meteo_df['time'] >= madrugada_inicio) &
        (datos_meteo_df['time'] <= madrugada_fin)
    ].copy()

    datos_para_modelo_serie = None
    fecha_pred_dt = None
    datos_hora_dict_seleccionados = None

    if datos_madrugada_df.empty:
        logger.warning(f"No hay ningún dato horario disponible en Open-Meteo para el rango de {madrugada_inicio} a {madrugada_fin}.")
    else:
        # Iterar sobre las horas disponibles en la madrugada para encontrar la primera con datos completos
        for index, fila_horaria_completa in datos_madrugada_df.iterrows():
            datos_hora_actual_dict = fila_horaria_completa.to_dict()

            # Estimación de HumedadSuelo si es necesario
            if 'HumedadSuelo' not in datos_hora_actual_dict or pd.isna(datos_hora_actual_dict['HumedadSuelo']):
                logger.warning(f"HumedadSuelo es NaN para {fila_horaria_completa['time']}. Intentando estimación.")
                if 'HumedadRelativa' in datos_hora_actual_dict and 'PrecipitacionMM' in datos_hora_actual_dict:
                    hr_val = datos_hora_actual_dict['HumedadRelativa']
                    precip_val = datos_hora_actual_dict['PrecipitacionMM']
                    # Actualizamos el diccionario directamente. La serie original no se modifica aquí.
                    datos_hora_actual_dict['HumedadSuelo'] = estimar_humedad_suelo_volumetrica(hr_val, precip_val)
                    if pd.isna(datos_hora_actual_dict['HumedadSuelo']):
                        logger.error(f"Estimación de HumedadSuelo falló (resulto en NaN) para {fila_horaria_completa['time']}. No se puede proceder con esta hora.")
                        # Continuar al siguiente registro horario si la estimación falla críticamente
                        continue 
                else:
                    logger.error(f"No se puede estimar HumedadSuelo para {fila_horaria_completa['time']} por falta de HumedadRelativa o PrecipitacionMM.")

                    continue
            
            completo_y_valido = True
            # Usamos una copia del dict para no enviar 'PrecipitacionMM' al modelo si no es una feature directa.
            datos_para_modelo_dict = {}
            for col_feature in COLUMNAS_FEATURES_PREDICCION:
                if col_feature not in datos_hora_actual_dict or pd.isna(datos_hora_actual_dict[col_feature]):
                    completo_y_valido = False
                    logger.debug(f"Dato faltante o NaN para la feature del modelo '{col_feature}' en {fila_horaria_completa['time']}: {datos_hora_actual_dict.get(col_feature)}")
                    break # No es necesario seguir verificando esta fila para el modelo
                datos_para_modelo_dict[col_feature] = datos_hora_actual_dict[col_feature]

            if completo_y_valido:
                datos_para_modelo_serie = fila_horaria_completa # Esta serie puede tener más columnas que las del modelo (ej. PrecipitacionMM)
                fecha_pred_dt = fila_horaria_completa['time']
                datos_hora_dict_seleccionados_para_log_y_bd = datos_hora_actual_dict.copy() # Contiene HumedadSuelo estimada y otras
                
                logger.info(f"Datos listos para la predicción a las {fecha_pred_dt.strftime('%Y-%m-%d %H:%M:%S')}. Features: {datos_para_modelo_dict}")
                break # Salir del bucle, ya encontramos la primera hora válida y procesada
            else:
                logger.info(f"Datos incompletos para el modelo en {fila_horaria_completa['time']} incluso después de intentar estimar. Valores: {datos_hora_actual_dict}. Buscando siguiente hora...")

    if datos_para_modelo_serie is None or fecha_pred_dt is None or datos_para_modelo_dict is None:
        msg = f"No se encontraron datos horarios completos (o no se pudieron estimar satisfactoriamente) para las variables {COLUMNAS_FEATURES_PREDICCION} en el rango de la madrugada del {dia_siguiente.strftime('%Y-%m-%d')} ({hora_inicio_madrugada:02d}:00-{hora_fin_madrugada:02d}:00)."
        logger.error(msg)
        return jsonify({"error": msg}), 400

    # Si llegamos aquí, tenemos datos_para_modelo_dict válidos y completos para el modelo
    df_pred_hora = pd.DataFrame([datos_para_modelo_dict], columns=COLUMNAS_FEATURES_PREDICCION)
    logger.info(f"DataFrame para predicción única (solo features del modelo): \n{df_pred_hora.to_string()}")

    try:
        pred_array = prediction_model.predict(df_pred_hora)
        prob_array = prediction_model.predict_proba(df_pred_hora)
        pred_valor = int(pred_array[0])
        prob_helada = float(prob_array[0][1])
        # temp_pronosticada se toma del diccionario que tiene todos los datos de esa hora
        temp_pronosticada = datos_hora_dict_seleccionados_para_log_y_bd['Temperatura'] 

        resultado, intensidad, duracion = determinar_estado_helada(pred_valor, prob_helada, temp_pronosticada)

        db_session: Session = next(get_db())
        try:
            # Usamos datos_hora_dict_seleccionados_para_log_y_bd para parametros_entrada
            # porque este contiene la HumedadSuelo (potencialmente estimada) y otras variables como PrecipitacionMM.
            parametros_entrada_json = json.dumps({k: v for k, v in datos_hora_dict_seleccionados_para_log_y_bd.items() if not pd.isna(v) and k != 'time'})

            nueva_pred = Prediccion(
                fecha_prediccion_para=fecha_pred_dt.to_pydatetime(),
                ubicacion="Patala, Pucará (Open-Meteo)",
                estacion_meteorologica="Open-Meteo Forecast",
                temperatura_minima_prevista=temp_pronosticada,
                probabilidad_helada=prob_helada, resultado=resultado,
                intensidad=intensidad, duracion_estimada_horas=duracion,
                parametros_entrada=parametros_entrada_json,
                fuente_datos_entrada="Open-Meteo API via src.data_fetcher (Pred. Madrugada)"
            )
            db_session.add(nueva_pred)
            db_session.commit()
            db_session.refresh(nueva_pred)

            mensaje_final = f"Pronóstico para la madrugada del {dia_siguiente} (aprox. {fecha_pred_dt.strftime('%H:%M')}) guardado."
            logger.info(f"{mensaje_final} (ID: {nueva_pred.id})")

            respuesta_api = {
                "id": nueva_pred.id,
                "fecha_prediccion_para": nueva_pred.fecha_prediccion_para.isoformat(),
                "ubicacion": nueva_pred.ubicacion,
                "estacion_meteorologica": nueva_pred.estacion_meteorologica,
                "temperatura_pronosticada": nueva_pred.temperatura_minima_prevista, # Renombrado para claridad
                "probabilidad_helada": nueva_pred.probabilidad_helada,
                "resultado": nueva_pred.resultado.value if nueva_pred.resultado else None,
                "intensidad": nueva_pred.intensidad.value if nueva_pred.intensidad else None,
                "duracion_estimada_horas": nueva_pred.duracion_estimada_horas,
                "mensaje": mensaje_final
            }
            return jsonify(respuesta_api), 200

        except Exception as db_exc:
            db_session.rollback()
            msg = f"Error guardando predicción para {fecha_pred_dt} en BD: {db_exc}"
            logger.error(msg, exc_info=True)
            return jsonify({"error": msg}), 500
        finally:
            db_session.close()

    except Exception as model_exc:
        msg = f"Error en predicción del modelo para {fecha_pred_dt}: {model_exc}"
        logger.error(msg, exc_info=True)
        return jsonify({"error": msg}), 500

@app.route('/registros', methods=['GET'])
def ver_registros():
    db_session: Session = next(get_db())
    try:
        query = db_session.query(Prediccion)
        fecha_filtro = request.args.get('fecha')
        estacion_filtro = request.args.get('estacion')

        if fecha_filtro:
            try:
                # strptime returns a datetime object, so calling .date() is correct here.
                fecha_dt = datetime.datetime.strptime(fecha_filtro, "%Y-%m-%d").date()
                query = query.filter( Prediccion.fecha_prediccion_para >= datetime.datetime.combine(fecha_dt, datetime.datetime.min.time()),
                                      Prediccion.fecha_prediccion_para <= datetime.datetime.combine(fecha_dt, datetime.datetime.max.time()))
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
        current_year = datetime.datetime.now().year
        return render_template('interfaz_registros.html', registros=registros, current_year=current_year)
    except Exception as e:
        logger.error(f"Error en la ruta /registros_ui: {e}", exc_info=True)
        return render_template('error.html', error_message=str(e)), 500
    finally:
        db_session.close()

@app.route('/obtener_prediccion_actual', methods=['GET'])
def obtener_prediccion_actual():
    db_session: Session = next(get_db())
    try:
        hoy_inicio = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())

        prediccion_actual = db_session.query(Prediccion)\
            .filter(Prediccion.fecha_prediccion_para >= hoy_inicio)\
            .order_by(Prediccion.fecha_prediccion_para.asc())\
            .first()

        if prediccion_actual:
            return jsonify({
                "id": prediccion_actual.id,
                "fecha_prediccion_para": prediccion_actual.fecha_prediccion_para.isoformat(),
                "ubicacion": prediccion_actual.ubicacion,
                "estacion_meteorologica": prediccion_actual.estacion_meteorologica,
                "temperatura_pronosticada": prediccion_actual.temperatura_minima_prevista,
                "probabilidad_helada": prediccion_actual.probabilidad_helada,
                "resultado": prediccion_actual.resultado.value if prediccion_actual.resultado else None,
                "intensidad": prediccion_actual.intensidad.value if prediccion_actual.intensidad else None,
                "duracion_estimada_horas": prediccion_actual.duracion_estimada_horas,
                "mensaje": "Predicción actual recuperada."
            }), 200
        else:
            return jsonify({"mensaje": "No hay predicción actual disponible."}), 404
    except Exception as e:
        logger.error(f"Error al obtener la predicción actual de la BD: {e}", exc_info=True)
        return jsonify({"error": f"Error al obtener predicción actual: {str(e)}"}), 500
    finally:
        db_session.close()


# --- Lógica de inicialización y ejecución (del antiguo src/main.py) ---
def inicializar_aplicacion(flask_app):
    logger.info("Configurando el motor de la base de datos...")
    # Pasa la URI de la base de datos desde la configuración de Flask a database.py
    setup_database_engine(flask_app.config['SQLALCHEMY_DATABASE_URI'])
    logger.info("Motor de base de datos configurado.")

    logger.info("Inicializando la base de datos (creando tablas si es necesario)...")
    init_db() # Esta función ahora usa el motor configurado por setup_database_engine
    logger.info("Base de datos lista y tablas verificadas/creadas.")
    # Aquí se podrían añadir otras inicializaciones si fueran necesarias

if __name__ == '__main__':
    # Solo inicializar la app en el proceso principal de Werkzeug o cuando no se usa el reloader
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        logger.info("Iniciando aplicación de predicción de heladas...")
        inicializar_aplicacion(app) # Pasar la instancia de la app Flask
    # El logger para el servidor Flask se mostrará igualmente, lo cual es útil.
    logger.info(f"Iniciando servidor Flask. Accede a la interfaz en http://{os.environ.get('FLASK_HOST', '0.0.0.0')}:{os.environ.get('FLASK_PORT', 5000)}")
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", 5000)),
        debug=(os.environ.get("FLASK_DEBUG", "True").lower() == "true")
    )
