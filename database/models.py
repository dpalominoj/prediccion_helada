from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import enum

# Define el motor de la base de datos (SQLite en este caso)
DATABASE_URL = "sqlite:///./predicciones.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # check_same_thread es para SQLite

# Base para los modelos declarativos
Base = declarative_base()

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

# Crear las tablas en la base de datos (si no existen)
def crear_tablas():
    Base.metadata.create_all(bind=engine)

# Configuración de la sesión de la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Función para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    # Esto creará la base de datos y la tabla si ejecutas models.py directamente
    print("Creando tablas en la base de datos (si no existen)...")
    crear_tablas()
    print("Tablas creadas (o ya existían).")

    # Ejemplo de cómo añadir un registro (opcional, para prueba)
    # from sqlalchemy.orm import Session
    # db_session = SessionLocal()
    # nueva_prediccion = Prediccion(
    #     fecha_prediccion_para=datetime.datetime.utcnow() + datetime.timedelta(days=1),
    #     ubicacion="Pucará - Ejemplo",
    #     estacion_meteorologica="Estacion Test",
    #     temperatura_minima_prevista=-1.5,
    #     probabilidad_helada=0.75,
    #     resultado=ResultadoPrediccion.probable,
    #     intensidad=IntensidadHelada.leve,
    #     duracion_estimada_horas=2.0,
    #     parametros_entrada='{"temp_rocio": 2.0, "temp_min_aire_6h": 0.5}',
    #     fuente_datos_entrada="Sensor XYZ"
    # )
    # db_session.add(nueva_prediccion)
    # db_session.commit()
    # db_session.refresh(nueva_prediccion)
    # print(f"Predicción de ejemplo añadida con ID: {nueva_prediccion.id}")
    # db_session.close()
