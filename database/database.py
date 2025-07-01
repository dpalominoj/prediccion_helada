from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Variables globales para el motor y la sesión, inicializadas como None.
# Serán configuradas por setup_database_engine().
engine = None
SessionLocal = None

# Crea una clase Base. Las clases de modelos de SQLAlchemy heredarán de esta clase.
# Esto puede definirse globalmente ya que no depende de la configuración del motor.
Base = declarative_base()

def setup_database_engine(db_uri: str):
    """
    Inicializa el motor de SQLAlchemy y SessionLocal con la URI de base de datos proporcionada.
    """
    global engine, SessionLocal
    if not db_uri:
        raise ValueError("La URI de la base de datos no puede estar vacía para configurar el motor.")

    current_engine = create_engine(
        db_uri, connect_args={"check_same_thread": False} # connect_args para SQLite
    )
    engine = current_engine # Asigna a la variable global
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    print(f"Motor de base de datos configurado para: {db_uri}")

def init_db():
    """
    Crea todas las tablas definidas por los modelos que heredan de Base.
    Esta función debe llamarse después de que setup_database_engine haya sido ejecutada.
    """
    if not engine:
        raise RuntimeError("El motor de la base de datos no ha sido inicializado. Llama a setup_database_engine() primero.")

    # Importa aquí todos los modelos para que sean registrados en Base.metadata
    # antes de que create_all sea llamado.
    from . import models # models.py debe existir y definir los modelos que heredan de Base.
    Base.metadata.create_all(bind=engine)
    print("Tablas de base de datos verificadas/creadas.")

def get_db() -> Session:
    """
    Generador para obtener una sesión de base de datos.
    Asegura que la sesión de la base de datos se cierre correctamente después de su uso.
    Esta función debe llamarse después de que setup_database_engine haya sido ejecutada.
    """
    if not SessionLocal:
        raise RuntimeError("SessionLocal no ha sido inicializado. Llama a setup_database_engine() primero.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Si ejecutas este archivo directamente, puedes inicializar la base de datos.
# Esto es útil para la configuración inicial o pruebas, pero necesitará una URI.
if __name__ == "__main__":
    print("Ejecutando database.py directamente...")
    # Para ejecutar esto directamente, necesitarías proporcionar una URI de base de datos.
    # Por ejemplo, podrías leerla de una variable de entorno o un archivo de configuración.
    # Como demostración, usaremos una URI en memoria para pruebas si no se proporciona otra.

    # Intenta obtener una DATABASE_URL de entorno, o usa una temporal en memoria.
    import os
    DEFAULT_TEST_DB_URL = "sqlite:///:memory:" # O "sqlite:///./test_direct_run.db"
    db_url_for_direct_run = os.environ.get("DIRECT_DB_URL", DEFAULT_TEST_DB_URL)

    print(f"Usando URL de BD para ejecución directa: {db_url_for_direct_run}")

    try:
        setup_database_engine(db_url_for_direct_run)
        print("Inicializando la base de datos y creando tablas (si no existen)...")
        init_db() # init_db ahora usa el 'engine' global configurado por setup_database_engine
        print("Base de datos inicializada y tablas creadas/verificadas.")

        # Ejemplo de cómo obtener una sesión y usarla (opcional)
        print("Probando obtener una sesión...")
        db_session = next(get_db())
        print(f"Sesión obtenida: {type(db_session)}")
        # Aquí podrías hacer una consulta simple si tienes modelos definidos y quieres probar
        # from .models import TuModelo
        # print(db_session.query(TuModelo).first())
        db_session.close()
        print("Sesión de prueba cerrada.")

    except Exception as e:
        print(f"Error durante la ejecución directa de database.py: {e}")
        print("Asegúrate de que los modelos estén definidos y que la URI de la BD sea válida.")
