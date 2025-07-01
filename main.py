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
from database.database import init_db, get_db
from database.models import Prediccion, IntensidadHelada, ResultadoPrediccion
from src.data_fetcher import obtener_datos_meteorologicos_openmeteo # FETCHED_COLUMNAS_MODELO será COLUMNAS_FEATURES_PREDICCION

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

    # Determinar la fecha y hora para la predicción de "noche o madrugada" del día siguiente.
    # Por ejemplo, 3:00 AM del día siguiente.
    # El 'time' en datos_meteo_df es un datetime object (potencialmente UTC o localizado por data_fetcher).
    # Asumimos que 'time' está en una zona horaria consistente (ej. UTC) o ya localizado.
    # data_fetcher usa timezone='auto', que podría ser UTC o la hora local del servidor.
    # Para robustez, sería ideal que data_fetcher siempre devuelva UTC y aquí se maneje.
    # Por ahora, confiamos en la consistencia de 'time'.

    ahora = datetime.datetime.now(datos_meteo_df['time'].iloc[0].tzinfo if datos_meteo_df['time'].iloc[0].tzinfo else None)
    dia_siguiente = ahora.date() + pd.Timedelta(days=1)
    hora_prediccion_target = datetime.datetime.combine(dia_siguiente, datetime.datetime.min.time().replace(hour=3))

    # Si los tiempos en df son naive y 'ahora' es aware (o viceversa), la comparación puede fallar o ser incorrecta.
    # Forzamos hora_prediccion_target a tener el mismo estado de timezone que df['time']
    if datos_meteo_df['time'].iloc[0].tzinfo is not None and hora_prediccion_target.tzinfo is None:
        hora_prediccion_target = hora_prediccion_target.replace(tzinfo=datos_meteo_df['time'].iloc[0].tzinfo)
    elif datos_meteo_df['time'].iloc[0].tzinfo is None and hora_prediccion_target.tzinfo is not None:
        hora_prediccion_target = hora_prediccion_target.replace(tzinfo=None)

    logger.info(f"Buscando datos para la predicción alrededor de: {hora_prediccion_target}")

    # Encontrar la fila más cercana a esta hora.
    # Podríamos interpolar, pero por simplicidad, tomaremos la hora más cercana disponible.
    # Open-Meteo devuelve datos horarios, así que deberíamos encontrar la hora exacta.
    fila_prediccion = datos_meteo_df[datos_meteo_df['time'] == hora_prediccion_target]

    if fila_prediccion.empty:
        # Si no hay datos para la hora exacta, podríamos tomar la más cercana o la primera de la madrugada.
        # Por ejemplo, datos entre las 00:00 y 06:00 del día siguiente.
        logger.warning(f"No se encontraron datos para la hora exacta {hora_prediccion_target}. Buscando en rango de madrugada...")
        madrugada_siguiente_inicio = datetime.datetime.combine(dia_siguiente, datetime.datetime.min.time())
        madrugada_siguiente_fin = datetime.datetime.combine(dia_siguiente, datetime.datetime.min.time().replace(hour=6))

        if datos_meteo_df['time'].iloc[0].tzinfo is not None: # Ajustar tz si es necesario
            madrugada_siguiente_inicio = madrugada_siguiente_inicio.replace(tzinfo=datos_meteo_df['time'].iloc[0].tzinfo)
            madrugada_siguiente_fin = madrugada_siguiente_fin.replace(tzinfo=datos_meteo_df['time'].iloc[0].tzinfo)

        filas_madrugada = datos_meteo_df[
            (datos_meteo_df['time'] >= madrugada_siguiente_inicio) &
            (datos_meteo_df['time'] <= madrugada_siguiente_fin)
        ]
        if not filas_madrugada.empty:
            fila_prediccion = filas_madrugada.iloc[[0]] # Tomar la primera hora de la madrugada (e.g., 00:00 o 01:00)
            logger.info(f"Usando la primera hora disponible de la madrugada: {fila_prediccion['time'].iloc[0]}")
        else:
            logger.error(f"No se encontraron datos meteorológicos para la madrugada del {dia_siguiente}.")
            return jsonify({"error": f"No se encontraron datos para la madrugada del {dia_siguiente}."}), 404

    # Extraer la única fila de datos para la predicción
    datos_para_modelo_serie = fila_prediccion.iloc[0]
    fecha_pred_dt = datos_para_modelo_serie['time']

    # COLUMNAS_FEATURES_PREDICCION ya está definido globalmente en main.py
    datos_hora_dict = datos_para_modelo_serie[COLUMNAS_FEATURES_PREDICCION].to_dict()

    if not all(col in datos_hora_dict and pd.notna(datos_hora_dict[col]) for col in COLUMNAS_FEATURES_PREDICCION):
        msg = f"Faltan datos o hay valores NaN para la predicción en {fecha_pred_dt}. Datos disponibles: {datos_hora_dict}"
        logger.error(msg)
        return jsonify({"error": msg}), 400

    df_pred_hora = pd.DataFrame([datos_hora_dict], columns=COLUMNAS_FEATURES_PREDICCION)
    logger.info(f"DataFrame para predicción única: \n{df_pred_hora.to_string()}")

    try:
        pred_array = prediction_model.predict(df_pred_hora)
        prob_array = prediction_model.predict_proba(df_pred_hora)
        pred_valor = int(pred_array[0])
        prob_helada = float(prob_array[0][1])
        temp_pronosticada = datos_hora_dict['Temperatura']

        resultado, intensidad, duracion = determinar_estado_helada(pred_valor, prob_helada, temp_pronosticada)

        db_session: Session = next(get_db())
        try:
            nueva_pred = Prediccion(
                fecha_prediccion_para=fecha_pred_dt.to_pydatetime(), # Convertir Timestamp de pandas a datetime de Python
                ubicacion="Patala, Pucará (Open-Meteo)",
                estacion_meteorologica="Open-Meteo Forecast",
                temperatura_minima_prevista=temp_pronosticada,
                probabilidad_helada=prob_helada, resultado=resultado,
                intensidad=intensidad, duracion_estimada_horas=duracion,
                parametros_entrada=json.dumps(datos_hora_dict),
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
                # datetime.datetime.combine needs a date object and a time object.
                # datetime.time.min and datetime.time.max are correct.
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
