from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import enum

# El motor y la Base se definen en database.py para centralizar.
# Aquí solo importamos Base.
from .database import Base

# Enum para la intensidad de la helada (ejemplo, se puede ajustar)
class IntensidadHelada(str, enum.Enum):
    leve = "Leve (-0.1°C a -2°C)"
    moderada = "Moderada (-2.1°C a -5°C)"
    fuerte = "Fuerte (< -5°C)"
    no_helada = "No se espera helada"

class ResultadoPrediccion(str, enum.Enum):
    probable = "Probable"
    poco_probable = "Poco Probable"
    no_determinada = "No Determinada"

# Modelo para la tabla de predicciones
class Prediccion(Base):
    __tablename__ = "predicciones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    fecha_prediccion_para = Column(DateTime, nullable=False, index=True) # Para qué día es la predicción
    ubicacion = Column(String, index=True, nullable=True, default="No especificada")
    estacion_meteorologica = Column(String, index=True, nullable=True, default="No especificada")

    # Campos que podrían venir del modelo de ML o ser calculados
    temperatura_minima_prevista = Column(Float, nullable=True)
    probabilidad_helada = Column(Float, nullable=True) # Ej: 0.85 (85%)

    # Resultado de la predicción (interpretado)
    resultado = Column(Enum(ResultadoPrediccion), default=ResultadoPrediccion.no_determinada)
    intensidad = Column(Enum(IntensidadHelada), default=IntensidadHelada.no_helada)
    duracion_estimada_horas = Column(Float, nullable=True) # En horas, ej: 2.5

    # Otros datos que podrían ser útiles
    parametros_entrada = Column(String, nullable=True) # JSON string de los parámetros usados para la predicción
    fuente_datos_entrada = Column(String, nullable=True) # De dónde se obtuvieron los datos para predecir

    def __repr__(self):
        return f"<Prediccion(id={self.id}, fecha_prediccion_para='{self.fecha_prediccion_para}', resultado='{self.resultado}')>"

# La creación de tablas, SessionLocal y get_db se manejan en database.py.
# El bloque if __name__ == "__main__": en database.py se encarga de la inicialización
# si se ejecuta ese script directamente.

# Si se necesita crear tablas desde aquí por alguna razón específica (poco común ahora):
# from .database import engine, Base
# def crear_tablas_desde_models():
#     Base.metadata.create_all(bind=engine)

# Si se necesita una sesión desde aquí (poco común, debería ser a través de get_db):
# from .database import SessionLocal
# def obtener_sesion_local():
#     return SessionLocal()
