from flask import Flask, render_template, jsonify, request, redirect, url_for
from database.database import init_db, get_db
from database.models import Prediccion, IntensidadHelada, ResultadoPrediccion
from sqlalchemy.orm import Session
import datetime
import json
import os
import joblib
import pandas as pd
import logging

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)
# Crear un logger específico para la aplicación si se desea más control
app_logger = logging.getLogger('werkzeug') # o __name__ para el logger de la app
app_logger.setLevel(logging.INFO)


# --- Configuración de la Aplicación Flask ---
app = Flask(__name__, template_folder='interfaz_usuario')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///./predicciones.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Carga del Modelo de Predicción y Constantes ---
# Asume que app.py está en el directorio raíz del proyecto ahora.
# Si app.py estuviera en 'src/', la ruta base necesitaría ajustarse (ej. '../')
RUTA_BASE_APP = os.path.dirname(os.path.abspath(__file__))
RUTA_MODELOS_ENTRENADOS_APP = os.path.join(RUTA_BASE_APP, "modelos_entrenados/")
NOMBRE_MODELO_PREDICCION_PKL = "modelo_arbol_decision.pkl"
# Estas columnas deben coincidir con las usadas durante el entrenamiento del modelo
COLUMNAS_FEATURES_PREDICCION = ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']

prediction_model = None
try:
    ruta_modelo_pkl = os.path.join(RUTA_MODELOS_ENTRENADOS_APP, NOMBRE_MODELO_PREDICCION_PKL)
    if os.path.exists(ruta_modelo_pkl):
        prediction_model = joblib.load(ruta_modelo_pkl)
        app.logger.info(f"Modelo de predicción cargado exitosamente desde: {ruta_modelo_pkl}")
    else:
        app.logger.error(f"Error crítico: No se encontró el modelo de predicción en la ruta especificada: {ruta_modelo_pkl}.")
        app.logger.warning("La funcionalidad de predicción NO estará disponible. Verifique la ruta y el archivo del modelo.")
except Exception as e:
    app.logger.error(f"Error crítico al cargar el modelo de predicción desde {ruta_modelo_pkl}: {e}", exc_info=True)
    prediction_model = None # Asegurar que es None si falla la carga


# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    """Ruta principal que sirve el interfaz_prediccion.html."""
    return render_template('interfaz_prediccion.html')

@app.route('/predecir', methods=['POST'])
def predecir():
    """
    Ruta para realizar una predicción de helada utilizando el modelo cargado.
    Guarda la predicción en la base de datos.
    El frontend debe enviar un JSON con las claves correspondientes a COLUMNAS_FEATURES_PREDICCION.
    """
    if prediction_model is None:
        app.logger.error("Intento de predicción pero el modelo no está cargado.")
        return jsonify({"error": "Modelo de predicción no disponible en el servidor. Contacte al administrador."}), 500

    input_data_json = request.json
    if not input_data_json:
        app.logger.warning("No se recibieron datos JSON en /predecir.")
        return jsonify({"error": "No se recibieron datos en formato JSON."}), 400

    # Validar y extraer las features requeridas por el modelo desde input_data_json
    datos_para_modelo_list = []
    for col in COLUMNAS_FEATURES_PREDICCION:
        if col not in input_data_json:
            app.logger.error(f"Falta la columna '{col}' en los datos de entrada para la predicción. Datos recibidos: {input_data_json}")
            return jsonify({"error": f"Dato de entrada incompleto. Falta '{col}'. Se requieren: {COLUMNAS_FEATURES_PREDICCION}"}), 400
        try:
            # Intentar convertir a float, ya que el modelo espera números
            datos_para_modelo_list.append(float(input_data_json[col]))
        except ValueError:
            app.logger.error(f"Valor no numérico para la columna '{col}': {input_data_json[col]}")
            return jsonify({"error": f"Valor para '{col}' debe ser numérico."}), 400

    datos_para_modelo_dict = dict(zip(COLUMNAS_FEATURES_PREDICCION, datos_para_modelo_list))

    try:
        df_para_predecir = pd.DataFrame([datos_para_modelo_dict], columns=COLUMNAS_FEATURES_PREDICCION)

        app.logger.info(f"DataFrame para predicción: \n{df_para_predecir.to_string()}")

        prediccion_array = prediction_model.predict(df_para_predecir)
        probabilidades_array = prediction_model.predict_proba(df_para_predecir)

        prediccion_valor = int(prediccion_array[0]) # 0 para No Helada, 1 para Helada
        probabilidad_helada = float(probabilidades_array[0][1]) # Probabilidad de la clase 1 (Helada)

        resultado_pred = ResultadoPrediccion.poco_probable
        intensidad_pred = IntensidadHelada.no_helada
        duracion_horas = 0
        # Usamos la Temperatura de entrada como una estimación inicial.
        # Idealmente, el modelo predeciría la temperatura mínima o tendríamos otra fuente.
        temp_min_prevista_estimada = datos_para_modelo_dict['Temperatura']

        if prediccion_valor == 1: # Helada
            resultado_pred = ResultadoPrediccion.probable
            # Lógica de ejemplo para determinar intensidad/duración basada en probabilidad
            if probabilidad_helada >= 0.80:
                intensidad_pred = IntensidadHelada.fuerte
                duracion_horas = 4.0
            elif probabilidad_helada >= 0.60:
                intensidad_pred = IntensidadHelada.moderada
                duracion_horas = 2.5
            else:
                intensidad_pred = IntensidadHelada.leve
                duracion_horas = 1.0

        prediccion_final_modelo = {
            "temperatura_minima_prevista": temp_min_prevista_estimada,
            "probabilidad_helada": probabilidad_helada,
            "resultado": resultado_pred,
            "intensidad": intensidad_pred,
            "duracion_estimada_horas": duracion_horas,
            "mensaje": f"Resultado del Modelo: {'HELADA' if prediccion_valor == 1 else 'NO HELADA'} (Probabilidad de helada: {probabilidad_helada:.2%})"
        }
        app.logger.info(f"Predicción realizada: {prediccion_final_modelo}")

    except Exception as e:
        app.logger.error(f"Error durante la ejecución de la predicción con el modelo: {e}", exc_info=True)
        return jsonify({"error": f"Error interno al procesar la predicción: {str(e)}"}), 500

    # Guardar en la base de datos
    db_session: Session = next(get_db())
    try:
        nueva_prediccion = Prediccion(
            fecha_prediccion_para=datetime.datetime.utcnow() + datetime.timedelta(days=1), # Asume predicción para el día siguiente UTC
            ubicacion=input_data_json.get("ubicacion", "Ubicación no provista por el cliente"),
            estacion_meteorologica=input_data_json.get("estacion", "Estación no provista por el cliente"),
            temperatura_minima_prevista=prediccion_final_modelo["temperatura_minima_prevista"],
            probabilidad_helada=prediccion_final_modelo["probabilidad_helada"],
            resultado=prediccion_final_modelo["resultado"],
            intensidad=prediccion_final_modelo["intensidad"],
            duracion_estimada_horas=prediccion_final_modelo["duracion_estimada_horas"],
            parametros_entrada=json.dumps(datos_para_modelo_dict), # Guardar los datos que realmente usó el modelo
            fuente_datos_entrada="API Flask con Modelo ML (modelo_arbol_decision.pkl)"
        )
        db_session.add(nueva_prediccion)
        db_session.commit()
        db_session.refresh(nueva_prediccion)
        app.logger.info(f"Predicción guardada en BD con ID: {nueva_prediccion.id}")

        prediccion_dict_respuesta = {
            "id": nueva_prediccion.id,
            "fecha_registro": nueva_prediccion.fecha_registro.isoformat(),
            "fecha_prediccion_para": nueva_prediccion.fecha_prediccion_para.isoformat(),
            "ubicacion": nueva_prediccion.ubicacion,
            "estacion_meteorologica": nueva_prediccion.estacion_meteorologica,
            "temperatura_minima_prevista": nueva_prediccion.temperatura_minima_prevista,
            "probabilidad_helada": nueva_prediccion.probabilidad_helada,
            "resultado": nueva_prediccion.resultado.value if nueva_prediccion.resultado else None,
            "intensidad": nueva_prediccion.intensidad.value if nueva_prediccion.intensidad else None,
            "duracion_estimada_horas": nueva_prediccion.duracion_estimada_horas,
            "mensaje_adicional": prediccion_final_modelo.get("mensaje")
        }
        return jsonify(prediccion_dict_respuesta), 200

    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error al guardar la predicción en la base de datos: {e}", exc_info=True)
        return jsonify({"error": f"Error interno al guardar la predicción en la BD: {str(e)}"}), 500
    finally:
        db_session.close()

@app.route('/registros', methods=['GET'])
def ver_registros():
    """
    Ruta para ver los registros de predicciones como JSON.
    Permite filtrar por fecha (formato YYYY-MM-DD) y estación meteorológica.
    """
    db_session: Session = next(get_db())
    try:
        query = db_session.query(Prediccion)

        fecha_filtro = request.args.get('fecha')
        estacion_filtro = request.args.get('estacion')

        if fecha_filtro:
            try:
                fecha_dt = datetime.datetime.strptime(fecha_filtro, "%Y-%m-%d").date()
                query = query.filter(
                    Prediccion.fecha_prediccion_para >= datetime.datetime.combine(fecha_dt, datetime.time.min),
                    Prediccion.fecha_prediccion_para <= datetime.datetime.combine(fecha_dt, datetime.time.max)
                )
            except ValueError:
                app.logger.warning(f"Formato de fecha inválido recibido: {fecha_filtro}")
                return jsonify({"error": "Formato de fecha inválido. Usar YYYY-MM-DD."}), 400

        if estacion_filtro:
            query = query.filter(Prediccion.estacion_meteorologica.ilike(f"%{estacion_filtro}%"))

        registros = query.order_by(Prediccion.fecha_prediccion_para.desc()).all()

        registros_list = []
        for reg in registros:
            registros_list.append({
                "id": reg.id,
                "fecha_registro": reg.fecha_registro.isoformat(),
                "fecha_prediccion_para": reg.fecha_prediccion_para.isoformat(),
                "ubicacion": reg.ubicacion,
                "estacion_meteorologica": reg.estacion_meteorologica,
                "resultado": reg.resultado.value if reg.resultado else None,
                "intensidad": reg.intensidad.value if reg.intensidad else None,
                "duracion_estimada_horas": reg.duracion_estimada_horas,
                "temperatura_minima_prevista": reg.temperatura_minima_prevista,
                "probabilidad_helada": reg.probabilidad_helada
            })

        return jsonify(registros_list), 200

    except Exception as e:
        app.logger.error(f"Error al obtener registros de la BD: {e}", exc_info=True)
        return jsonify({"error": f"Error al obtener registros: {str(e)}"}), 500
    finally:
        db_session.close()

@app.route('/registros_ui', methods=['GET'])
def ver_registros_ui():
    """
    Ruta para ver los registros de predicciones en una interfaz HTML.
    """
    db_session: Session = next(get_db())
    try:
        query = db_session.query(Prediccion)
        # TODO: Añadir filtros desde request.args si se implementan en el template 'interfaz_registros.html'
        # Ejemplo:
        # fecha_filtro = request.args.get('fecha_filtro_form')
        # if fecha_filtro:
        #     # aplicar filtro a query
        registros = query.order_by(Prediccion.fecha_prediccion_para.desc()).all()
        return render_template('interfaz_registros.html', registros=registros)
    except Exception as e:
        app.logger.error(f"Error en la ruta /registros_ui: {e}", exc_info=True)
        # Considerar renderizar una página de error HTML en lugar de JSON para una UI
        return render_template('error.html', error_message=str(e)), 500
    finally:
        db_session.close()

# La plantilla error.html ya fue movida a interfaz_usuario/error.html


# --- Inicialización y ejecución ---
if __name__ == '__main__':
    # Asegurar que la base de datos y las tablas estén creadas antes de iniciar la app.
    # Esta función init_db() debería llamar a Base.metadata.create_all(engine)
    from database.database import init_db as init_db_function

    app.logger.info("Inicializando la base de datos (si es necesario)...")
    init_db_function() # Llama a la función que crea las tablas

    app.logger.info("Iniciando el servidor Flask en modo debug...")
    # app.run(debug=True, host='0.0.0.0', port=5000)
    # Para producción, se usaría un servidor WSGI como Gunicorn o Waitress.
    # Ejemplo: waitress-serve --host 0.0.0.0 --port 5000 app:app
    # Para desarrollo, debug=True está bien.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
